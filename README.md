# ArcVPN Bot

Telegram бот для управления VPN подписками.

## Subscription система

Для работы subscription системы нужно запустить `subscription_api.py`:

```bash
# Установить Flask
pip3 install flask

# Запустить API
nohup python3 subscription_api.py > subscription.log 2>&1 &

# Проверить
curl http://localhost:8080/health
```

Пользователи получают subscription URL через кнопку "🔗 Subscription ссылка" в боте.
