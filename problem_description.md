# Проблема: Обход белых списков РКН через CDN

## Контекст

Российский VPN-сервис для 13 пользователей. 
Стек: Xray/x-ui панель (3X-UI) на сервере в Германии (2.26.84.210), свою подписку генерируем через Python-приложение (subscription_api.py).
Клиенты используют Happ (iOS/Android).

У нас работают 2 inbounds:
- Основной: VLESS+XHTTP+Reality (порт 12631)
- Запасной: VLESS+TCP+Reality (порт 443)

## Задача

Добавить третий inbound — «Обход белых списков (БС)» — который будет работать когда РКН/ТСПУ включает режим белых списков (доступ только к whitelisted-ресурсам РФ). 

При БС обычный VPN на зарубежный сервер перестаёт работать, т.к. IP сервера не в белом списке. Нужно маскировать трафик под легитимный российский ресурс.

## Решение: Yandex Cloud CDN

Выбрали метод из популярного гайда (видео «ВСЕ про обход БЕЛЫХ СПИСКОВ | ГАЙД?», автор Rast for New / RFN VPN).

Архитектура:

```
Пользователь (Happ) → cdn.arccnet.space:443 (Yandex CDN, IP в БС) → 2.26.84.210:80 (nginx) → Xray (127.0.0.1:10001) → Интернет
```

Yandex CDN IP (AS Yandex LLC, 188.72.x.x) — в белом списке, т.к. обслуживает yandex.ru. CDN терминирует TLS, форвардит HTTP на origin (DE сервер). Для ТСПУ выглядит как HTTPS к Яндексу.

### Что настроено

1. **Домен**: arccnet.space (Reg.ru, 305₽), поддомен cdn.arccnet.space
2. **Yandex Cloud CDN**:
   - Доменное имя: cdn.arccnet.space
   - Origin: 2.26.84.210 (DE сервер)
   - Протокол для источников: HTTP (порт 80)
   - Сертификат: Let's Encrypt (Certificate Manager)
   - Кэширование: отключено, протокол HTTP
3. **DE сервер (2.26.84.210)**:
   - nginx: default_server на порту 80, прокси / на Xray (127.0.0.1:10001)
   - Xray inbound: VLESS+XHTTP, порт 10001, path=/, security=none (TLS на CDN)
   - UFW: 80/tcp открыт
4. **Подписка (subscription_api.py)**:
   - Для порта 10001 подменяем host/port/security: host=cdn.arccnet.space, port=443, security=tls
   - Ссылка: vless://uuid@cdn.arccnet.space:443?type=xhttp&path=/&host=cdn.arccnet.space&mode=auto&security=tls&sni=cdn.arccnet.space#🇷🇺 Белые списки (LTE)

## Текущий статус

### Что работает ✅
- CDN публично доступен: `curl https://cdn.arccnet.space/` возвращает 400 (Xray, path совпал)
- GET/POST через CDN доходят до origin (nginx → Xray)
- SSL сертификат cdn.arccnet.space от Let's Encrypt
- DNS глобально: cdn.arccnet.space CNAME → yccdn.ru → 188.72.103.3
- Локально (DE сервер): nginx → Xray работает (400)

### Что НЕ работает ❌
- Клиенты не могут подключиться через Happ (VLESS+XHTTP через CDN)
- "Не пингуется", сайты не открываются
- Причина не ясна: DNS кэш на устройстве? CDN буферизирует POST? Happ не понимает XHTTP через CDN? Оператор (Билайн) блокирует?

### Детали тестирования

**Тестовый сервис** (vless_test, тестирует inbound из x-ui панели):
- Тестирует 2.26.84.210:10001 напрямую (raw inbound, не через CDN)
- Порт 10001 закрыт в firewall (только локальный доступ через nginx)
- Результат: "TCP заблокирован" — ожидаемо, т.к. порт 10001 не публичный
- Сервис не умеет тестить CDN-фронтинг (cdn.arccnet.space:443)

**Ручная проверка CDN (curl извне)**:
```
GET https://cdn.arccnet.space/ → 400 (0.3s)
POST https://cdn.arccnet.space/ → 405 (0.2s)
```
Оба запроса доходят до origin (nginx → Xray). CDN работает.

**SSL сертификат**:
```
subject=CN = cdn.arccnet.space
issuer=Let's Encrypt (YR1)
```

**CDN заголовки ответа**:
```
server: nginx
x-padding: ... (Xray XHTTP padding)
cache-host: yccdn-m9-17.yccdn.cloud.yandex.net
```

## Гипотезы почему не работает в Happ

1. **CDN буферизирует POST-тело** — XHTTP использует streaming HTTP POST. Если CDN буферизирует запрос перед отправкой на origin, VLESS payload не доходит до Xray вовремя → соединение ломается
2. **CDN не поддерживает streaming** — Возможно, Yandex CDN не может проксировать длинные HTTP-соединения (keep-alive, chunked transfer)
3. **DNS кэш на устройстве** — Старая A-запись (cdn → 2.26.84.210) могла закэшироваться у оператора
4. **Happ неправильно интерпретирует ссылку** — Возможно, Happ ожидает WS, а не XHTTP через CDN
5. **Оператор (Билайн) блокирует Yandex CDN IP** — Маловероятно, но возможно

## Ссылка для теста в Happ

```
vless://323bbc90-0e0e-488c-8e28-dddfb5f8d94b@cdn.arccnet.space:443?type=xhttp&encryption=none&path=/&host=cdn.arccnet.space&mode=auto&security=tls&sni=cdn.arccnet.space&fp=firefox&alpn=http/1.1#🇷🇺 Белые списки (LTE)
```

P.S. Вообще с самого начала были идеи и другие варианты:
- Использовать WebRTC (VK Calls TURN) — но это требует отдельного приложения, Happ не поддерживает
- Использовать RU relay VPS (Timeweb/VDSina) — но нужна аренда дополнительного VPS
- Использовать Yandex Cloud CDN как сейчас
