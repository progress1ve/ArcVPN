# 🔗 Subscription система

## Быстрая установка (3 команды):

```bash
# 1. Установить Flask
pip3 install flask

# 2. Запустить subscription API
cd /root/ArcVPN
nohup python3 subscription_api.py > subscription.log 2>&1 &

# 3. Проверить
curl http://localhost:8080/health
```

Должно вернуть: `OK`

---

## Проверка работы:

```bash
# Найти Telegram ID пользователя
sqlite3 database/vpn_bot.db "SELECT telegram_id FROM users LIMIT 1;"

# Проверить subscription (замените USER_ID)
curl http://localhost:8080/sub/USER_ID
```

---

## Автозапуск (опционально):

```bash
sudo cp subscription.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start subscription
sudo systemctl enable subscription
```

---

## Команды:

```bash
# Статус
sudo systemctl status subscription

# Логи
sudo journalctl -u subscription -f

# Перезапуск
sudo systemctl restart subscription
```

---

## Настройка:

В `config.py` уже настроено:
```python
SUBSCRIPTION_URL = "http://144.31.136.54:8080"
```

Измените IP на ваш если нужно.

---

## Что это даёт:

- Клиенты получают subscription URL вместо прямых ключей
- При добавлении новых серверов клиенты видят их автоматически
- Не нужно рассылать новые ключи при миграции
