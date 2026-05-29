from typing import List
import base64

import flask
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
    res = base64.b64encode(bytes(urls_text, 'utf-8'))
    return res


if __name__ == '__main__':
    app.run(c.LISTEN_HOST, c.LISTEN_PORT)