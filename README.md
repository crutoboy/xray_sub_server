# Xray Subscription Server

Лёгкий сервер подписок для Xray/V2Ray экосистемы. Позволяет объединять несколько источников конфигураций (внешние подписки + локальные ссылки) и отдавать их в формате, совместимом с популярными клиентами (v2rayN, Nekobox, Happ, Sing-box и др.).

## Возможности

- Объединение внешних подписок (`https://`) и локальных ссылок
- Поддержка метаданных подписки в стиле **3x-ui**:
  - `Subscription-Userinfo` (динамически подтягивается из внешних подписок)
  - `Support-Url`
  - `Profile-Web-Page-Url`
  - `Announce`
  - `Profile-Update-Interval`
  - `Routing` + `Routing-Enable` (для клиента Happ)
- Умное объединение `Subscription-Userinfo` из нескольких upstream-подписок
- Кеширование внешних подписок (TTL)
- Запуск через Docker + gunicorn
- Поддержка SSL прямо в gunicorn (без reverse proxy)
- Простая конфигурация через `.env`

## Быстрый старт

### Через Docker Compose (рекомендуется)

1. Склонируй репозиторий:
   ```bash
   git clone https://github.com/crutoboy/xray_sub_server.git
   cd xray_sub_server
   ```

2. Создай `.env` на основе примера:
   ```bash
   cp .env.example .env
   ```

3. Отредактируй `.env` — укажи свои ссылки и метаданные.

4. Настрой сертификаты (обязательно для работы по HTTPS).

   Подробности ниже в разделе **SSL / Сертификаты**.

5. Запусти:
   ```bash
   docker compose up -d
   ```

Подписка будет доступна по адресу:
```
https://your-domain:2096/sub/<username>
```

## Конфигурация

Основная конфигурация находится в файле `.env`.

### URLS

Параметр `URLS` — это JSON-объект, где ключ — имя пользователя, а значение — массив ссылок.

Пример:

```json
{
  "all": [
    "https://panel.example.com:2096/sub/{}",
    "vless://...@server.com:443?security=reality#{}"
  ],
  "crutoboy": [
    "hysteria2://...@server.com:444#user-{}"
  ]
}
```

- Ключ `"all"` — ссылки, которые получают **все** пользователи.
- Другие ключи — персональные ссылки для конкретного пользователя.
- На место `{}` подставляется имя пользователя из URL.

Поддерживаемые типы ссылок:
- `https://...` — внешняя подписка (сервер сам её скачает и объединит)
- `vless://`, `hysteria2://`, `trojan://`, `vmess://` и т.д. — прямые конфиги

### Глобальные метаданные подписки

Эти параметры добавляются во все подписки:

| Переменная               | Описание                                      | Пример |
|--------------------------|-----------------------------------------------|--------|
| `SUPPORT_URL`            | Ссылка на поддержку                           | `https://t.me/your_support` |
| `PROFILE_WEB_PAGE_URL`   | Ссылка на панель / профиль                    | `https://panel.example.com` |
| `ANNOUNCE`               | Объявление (показывается в клиентах)          | `Техработы 25.06 с 23:00` |
| `UPDATE_INTERVAL`        | Интервал обновления подписки (в часах)        | `12` |
| `SUBSCRIPTION_USERINFO`  | Fallback для статистики трафика               | `upload=0; download=0; total=0; expire=0` |
| `HAPP_ROUTING_LINK`      | Ссылка на маршрутизацию для клиента Happ      | `happ://routing/add/...` |

> **Важно:** Если среди ваших `https://` ссылок есть подписки от 3x-ui / Hiddify и т.д., то `Subscription-Userinfo` будет автоматически подтягиваться оттуда и объединяться.

## SSL / Сертификаты

Сервер по умолчанию работает по HTTP. Для продакшена рекомендуется использовать HTTPS.

В поставляемом `docker-compose.yml` настроен запуск с SSL напрямую через gunicorn. Для этого в контейнере должны быть доступны файлы сертификатов:
- `fullchain.pem`
- `privkey.pem`

### Получение сертификатов через Certbot (рекомендуется)

Самый правильный способ — не копировать сертификаты, а смонтировать их напрямую из директории Let's Encrypt.

1. Получи сертификат:

```bash
sudo apt update
sudo apt install certbot

sudo certbot certonly --standalone -d your-domain.com
```

2. Отредактируй `docker-compose.yml` и замени путь к сертификатам:

```yaml
volumes:
  # Вместо ./certs монтируем настоящие сертификаты Let's Encrypt
  - /etc/letsencrypt/live/your-domain.com:/certs:ro
```

3. Запусти:

```bash
docker compose up -d
```

При таком подходе после автоматического продления сертификатов (`certbot renew`) ничего дополнительно делать не нужно.

### Альтернатива: Симлинк в папку certs

Если по каким-то причинам хочешь оставить структуру с `./certs`, можно сделать симлинк:

```bash
sudo ln -s /etc/letsencrypt/live/your-domain.com /path/to/project/certs
```

После этого можно не менять `docker-compose.yml`.

### Самоподписной сертификат (только для теста)

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -subj "/CN=your-domain.com"
```

### Через reverse proxy (альтернатива)

Если предпочитаешь вынести SSL на уровень reverse proxy — используй **Caddy**, **Nginx** или **Traefik**. В этом случае можно запускать приложение без SSL (убрав блок `command` в docker-compose).

## Переменные окружения

Полный список переменных окружения описан в файле [`.env.example`](.env.example).

## Разработка

### Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Лицензия

MIT

---

**Проект создан для личного использования и self-hosted решений.** Приветствуются пулл-реквесты и идеи по улучшению.