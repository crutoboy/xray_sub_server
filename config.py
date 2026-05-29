import os
import json

from dotenv import load_dotenv


load_dotenv()


LISTEN_HOST = os.getenv('LISTEN_HOST', '0.0.0.0')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '2096'))
URI_PATH = os.getenv('URI_PATH', '/sub/')
URLS = json.loads(os.getenv('URLS', '{}'))

# TTL кеша внешних подписок в секундах (по умолчанию 1 час)
SUBSCRIPTION_CACHE_TTL = int(os.getenv('SUBSCRIPTION_CACHE_TTL', '3600'))
