from typing import List
import base64

import flask
from flask import make_response
import requests
from cachetools import TTLCache, cached

import config as c


app = flask.Flask(__name__)


@app.route('/')
def index():
    ...


# Кеш внешних подписок с TTL (по умолчанию 1 час)
_subs_cache = TTLCache(maxsize=256, ttl=c.SUBSCRIPTION_CACHE_TTL)
@cached(_subs_cache)
def get_subs_from_server(link: str):
    """
    Получает внешнюю подписку.
    Возвращает кортеж: (список нод, Subscription-Userinfo из заголовка или None)
    """
    try:
        sub_response = requests.get(link, timeout=10)
        userinfo = sub_response.headers.get('Subscription-Userinfo') or \
                   sub_response.headers.get('subscription-userinfo')

        decoded = base64.b64decode(sub_response.text).decode('utf-8')
        nodes = [line for line in decoded.split('\n') if line.strip()]

        return nodes, userinfo
    except Exception:
        # При ошибке не кешируем и пробуем заново в следующий раз
        _subs_cache.pop(link, None)
        return [], None

def format_urls(urls: List[str], user: str):
    """
    Возвращает (список всех нод, список найденных Subscription-Userinfo из внешних подписок)
    """
    all_nodes = []
    userinfos = []

    for url in urls:
        url = url.strip().format(user)
        if url.startswith('https://'):
            nodes, userinfo = get_subs_from_server(url)
            all_nodes += nodes
            if userinfo:
                userinfos.append(userinfo)
        else:
            all_nodes.append(url)

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


@app.route(f'{c.URI_PATH}<user>')
def get_subs(user: str):
    nodes, upstream_userinfos = format_urls(
        c.URLS.get(user, []) + c.URLS.get('all', []), user
    )

    urls_text = '\n'.join(nodes)
    encoded = base64.b64encode(bytes(urls_text, 'utf-8'))

    resp = make_response(encoded)
    resp.headers['Content-Type'] = 'text/plain; charset=utf-8'

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



if __name__ == '__main__':
    app.run(c.LISTEN_HOST, c.LISTEN_PORT)