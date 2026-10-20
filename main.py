from typing import List
import base64
import json
import urllib.parse
import asyncio

import flask
from flask import make_response
import aiohttp
from cachetools import TTLCache, cached

import config as c


app = flask.Flask(__name__)


@app.route('/')
def index():
    ...


# Кеш внешних подписок с TTL (по умолчанию 1 час)
_subs_cache = TTLCache(maxsize=256, ttl=c.SUBSCRIPTION_CACHE_TTL)
@cached(_subs_cache)
async def get_subs_from_server(link: str, headers: dict):
    """
    Получает внешнюю подписку.
    Возвращает кортеж: (json ли, список нод, Subscription-Userinfo из заголовка или None)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                link,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as sub_response:

                userinfo = (
                    sub_response.headers.get('Subscription-Userinfo')
                    or sub_response.headers.get('subscription-userinfo')
                )

                text = await sub_response.text()

                try:
                    parsed_json = await sub_response.json()
                    return True, parsed_json, userinfo
                except (aiohttp.ContentTypeError, ValueError):
                    pass

                try:
                    decoded = base64.b64decode(text).decode('utf-8')
                except Exception:
                    decoded = text

                nodes = [line for line in decoded.split('\n') if line.strip()]
                return False, nodes, userinfo

    except Exception:
        # При ошибке не кешируем и пробуем заново в следующий раз
        _subs_cache.pop(link, None)
        return False, [], None

async def format_url(configs: dict, user: str, is_json: bool):
    if not config.get('enable', True):
        return []
    config_json = config.get('json')
    config_link = config.get('link')
    config_sub = config.get('sub')

    config_prefix = config.get('prefix')
    config_name = config.get('name')

    config_select = config.get('select')
    config_headers = config.get('headers', c.GET_SUB_HEADERS)

    if (is_json and config_link is not None) or \
        (not is_json and config_json is not None):
        return []

    if config_json is not None:
        node = json.loads(config_json)
        node = {}
        if config_name is not None:
            node.update({'remarks': config_name})
        elif config_prefix is not None:
            node.update({'remarks': config_prefix + node.get('remarks', '')})
        return [node]
        # all_nodes.append(node)

    elif config_link is not None:
        conf, remark = config_link.split('#')
        remark = urllib.parse.unquote(remark)
        if config_name is not None:
            remark = config_name
        elif config_prefix is not None:
            remark = config_prefix + remark
        remark = urllib.parse.quote(remark)
        return [f'{conf}#{remark}']
        # all_nodes.append(f'{conf}#{remark}')

    elif config_sub is not None:
        is_json_sub, nodes, userinfo = await get_subs_from_server(config_sub, config_headers)
        if is_json != is_json_sub:
            return []
        if config_select is not None:
            res = []
            for i in config_select:
                if -len(nodes) <= i < len(nodes): 
                    res.append(nodes[i])
            nodes = res
        if config_prefix is not None and is_json:
            for i in len(nodes):
                nodes[i].update({'remarks': config_prefix + nodes[i].get('remarks', '')})
        if config_prefix is not None and not is_json:
            res = []
            for node in nodes:
                conf, remark = node.split('#')
                remark = urllib.parse.unquote(remark)
                remark = urllib.parse.quote(config_prefix + remark)
                res.append(f'{conf}#{remark}')
            nodes = res

        # print(nodes)
        # all_nodes += nodes
        return nodes


def format_urls(configs: List[dict], user: str, is_json: bool):
    """
    Возвращает (список всех нод, список найденных Subscription-Userinfo из внешних подписок)
    """
    all_nodes = []
    userinfos = []
    
    results = asyncio.run(           # ← здесь создаётся и запускается event loop
        asyncio.gather(*(format_url(format_url, user, is_json) for config in configs))
    )

    print(results)


    return all_nodes, userinfos

def _parse_userinfo(s: str) -> dict:
    """Парсит строку вида 'upload=123; download=456; total=789; expire=1234567890'"""
    data = {}
    for part in s.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            try:
                data[k.strip().lower()] = int(v.strip())
            except ValueError:
                pass
    return data


def _merge_userinfo(infos: list[str]) -> str | None:
    """Объединяет несколько Subscription-Userinfo (суммирует трафик, берёт минимальные лимиты)."""
    if not infos:
        return None

    total_upload = 0
    total_download = 0
    min_total = None
    min_expire = None

    for info in infos:
        parsed = _parse_userinfo(info)
        total_upload += parsed.get('upload', 0)
        total_download += parsed.get('download', 0)

        t = parsed.get('total')
        if t is not None and t > 0:
            min_total = t if min_total is None else min(min_total, t)

        e = parsed.get('expire')
        if e is not None and e > 0:
            min_expire = e if min_expire is None else min(min_expire, e)

    parts = [
        f"upload={total_upload}",
        f"download={total_download}",
    ]

    if min_total is not None:
        parts.append(f"total={min_total}")
    else:
        parts.append("total=0")

    if min_expire is not None:
        parts.append(f"expire={min_expire}")
    else:
        parts.append("expire=0")

    return '; '.join(parts)

def _add_resp_headers(resp, upstream_userinfos):
    # === Динамический Userinfo из внешних подписок ===
    dynamic_userinfo = _merge_userinfo(upstream_userinfos)
    if dynamic_userinfo:
        resp.headers['Subscription-Userinfo'] = dynamic_userinfo
    elif c.SUBSCRIPTION_USERINFO:  # fallback на статическое значение, если есть
        resp.headers['Subscription-Userinfo'] = c.SUBSCRIPTION_USERINFO

    if c.UPDATE_INTERVAL:
        resp.headers['Profile-Update-Interval'] = str(c.UPDATE_INTERVAL)

    if c.SUPPORT_URL:
        resp.headers['Support-Url'] = c.SUPPORT_URL

    if c.PROFILE_WEB_PAGE_URL:
        resp.headers['Profile-Web-Page-Url'] = c.PROFILE_WEB_PAGE_URL

    if c.ANNOUNCE:
        announce_bytes = base64.b64encode(bytes(c.ANNOUNCE, "utf-8"))
        announce_encode = announce_bytes.decode('ascii')
        resp.headers['Announce'] = f'base64:{announce_encode}'

    if c.HAPP_ROUTING_LINK:
        resp.headers['Routing'] = c.HAPP_ROUTING_LINK
        resp.headers['Routing-Enable'] = 'true'

    return resp

@app.route(f'{c.URI_PATH_SUB}<user>')
def get_subs(user: str):
    nodes, upstream_userinfos = format_urls(
        c.SUB_CONFIG.get('all', []) + c.SUB_CONFIG.get(user, []), user, False
    )

    urls_text = '\n'.join(nodes)
    encoded = base64.b64encode(bytes(urls_text, 'utf-8'))

    resp = make_response(encoded)
    resp.headers['Content-Type'] = 'text/plain; charset=utf-8'

    resp = _add_resp_headers(resp, upstream_userinfos)

    return resp

@app.route(f'{c.URI_PATH_JSON}<user>')
def get_jsons(user: str):
    nodes, upstream_userinfos = format_urls(
        c.SUB_CONFIG.get('all', []) + c.SUB_CONFIG.get(user, []), user, True
    )

    encoded = json.dumps(nodes)

    resp = make_response(encoded)
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'

    resp = _add_resp_headers(resp, upstream_userinfos)

    return resp


if __name__ == '__main__':
    app.run(c.LISTEN_HOST, c.LISTEN_PORT)