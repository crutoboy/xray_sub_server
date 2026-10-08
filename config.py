import os
import json

from dotenv import load_dotenv
import yaml


load_dotenv()


LISTEN_HOST = os.getenv('LISTEN_HOST', '0.0.0.0')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '2096'))
URI_PATH = os.getenv('URI_PATH', '/sub/')

# TTL кеша внешних подписок в секундах (по умолчанию 1 час)
SUBSCRIPTION_CACHE_TTL = int(os.getenv('SUBSCRIPTION_CACHE_TTL', '3600'))
USER_AGENT = os.getenv('USER_AGENT', '')

# метаданные подписки
SUPPORT_URL = os.getenv('SUPPORT_URL', '')
PROFILE_WEB_PAGE_URL = os.getenv('PROFILE_WEB_PAGE_URL', '')
ANNOUNCE = os.getenv('ANNOUNCE', '')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '12'))          # в часах
HAPP_ROUTING_LINK = os.getenv('HAPP_ROUTING_LINK', '')             # полный happ://routing/add/...

# Fallback значение Subscription-Userinfo, если ни одна внешняя подписка не вернула свои данные
SUBSCRIPTION_USERINFO = os.getenv('SUBSCRIPTION_USERINFO', '')

# Файл конфигурации подписки
SUB_CONFIG_FILE = os.getenv('SUB_CONFIG', './config.yaml')

def import_sub_config():
    with open(SUB_CONFIG_FILE) as file:
        sub_config = yaml.safe_load(file)

    for user in sub_config:
        for config in sub_config[user]:
            if not config.get('enable', True):
                continue
            config_json = config.get('json')
            config_link = config.get('link')
            config_sub = config.get('sub')
            count_main_conf = sum(map(bool, (config_json, config_link, config_sub)))

            config_prefix = config.get('prefix')
            config_name = config.get('name')
            count_rename_conf = sum(map(bool, (config_prefix, config_name)))

            config_select = config.get('select')

            if count_main_conf == 0:
                raise Exception('use "json", "link" or "sub" in config is required')
            if count_main_conf > 1:
                raise Exception('use only *one* "json", "link" or "sub" in config')
            if count_rename_conf > 1:
                raise Exception('use only *one* "prefix" or "name" in config')
            if config_select is not None and config_sub is None:
                raise Exception('use "select" only with "sub" in config')

    return sub_config

SUB_CONFIG = import_sub_config()