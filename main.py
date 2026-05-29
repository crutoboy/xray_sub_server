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
def get_subs_from_server(link: str) -> List[str]:
    """
    Получает и декодирует внешнюю подписку по HTTPS ссылке.
    Результат кешируется на SUBSCRIPTION_CACHE_TTL секунд.
    """
    try:
        sub_response = requests.get(link, timeout=10)
        decoded = base64.b64decode(sub_response.text).decode('utf-8')
        res = decoded.split('\n')
        res = list(filter(None, res))
        return res
    except Exception:
        # В случае ошибки не кешируем результат (попробуем снова при следующем запросе)
        # Для этого очищаем кеш для данного ключа
        _subs_cache.pop(link, None)
        return []

def format_urls(urls: List[str], user: str) -> List[str]:
    res = []
    for url in urls:
        url = url.strip().format(user)
        if url.startswith('https://'):
            subs = get_subs_from_server(url)
            res += subs
        else: 
            res.append(url)
    return res 

@app.route(f'{c.URI_PATH}<user>')
def get_subs(user: str):
    urls = format_urls(c.URLS.get(user, []) + c.URLS.get('all', []), user)
    urls_text = '\n'.join(urls)

    encoded = base64.b64encode(bytes(urls_text, 'utf-8'))

    # Создаём ответ и добавляем заголовки
    resp = make_response(encoded)
    resp.headers['Content-Type'] = 'text/plain; charset=utf-8'

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