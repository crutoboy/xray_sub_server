from typing import List
import base64

import flask
import requests

import config as c


app = flask.Flask(__name__)


@app.route('/')
def index():
    ...


def get_subs_from_server(link: str) -> List[str]:
    try:
        sub_response = requests.get(link)
        decoded = base64.b64decode(sub_response.text).decode('utf-8')
        res = decoded.split('\n')
        res = list(filter(None, res))
        return res
    except:
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