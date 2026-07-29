"""HTML-страницы subscription-сервиса.

Вынесено из subscription_api.py, чтобы не держать большой шаблон внутри логики
роутинга. Шаблон — обычный f-string; CSS-скобки экранированы как {{ }}.
"""

import html


def render_import_page(
    safe_happ_deeplink: str,
    safe_subscription_url: str,
    js_subscription_url: str,
    js_device_registration_url: str,
    profile_title: str = "ArcVPN",
) -> str:
    """
    Возвращает HTML страницы импорта подписки для обычных браузеров.

    Args:
        safe_happ_deeplink: html-экранированный happ://add/... deeplink
        safe_subscription_url: html-экранированный URL подписки
        js_subscription_url: JSON-сериализованный URL подписки (для вставки в JS)
        js_device_registration_url: JSON-сериализованный endpoint регистрации устройства
        profile_title: Название профиля/бренда
    """
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{profile_title} - Импорт подписки</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(180deg, #3d5a9e 0%, #516db3 50%, #7a8fc4 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}

        /* Анимированные звезды на фоне */
        .stars {{
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}

        .star {{
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: twinkle 3s infinite;
        }}

        @keyframes twinkle {{
            0%, 100% {{ opacity: 0.3; }}
            50% {{ opacity: 1; }}
        }}

        /* Генерируем звезды */
        .star:nth-child(1) {{ top: 10%; left: 20%; animation-delay: 0s; }}
        .star:nth-child(2) {{ top: 20%; left: 80%; animation-delay: 0.5s; }}
        .star:nth-child(3) {{ top: 30%; left: 50%; animation-delay: 1s; }}
        .star:nth-child(4) {{ top: 40%; left: 10%; animation-delay: 1.5s; }}
        .star:nth-child(5) {{ top: 50%; left: 90%; animation-delay: 2s; }}
        .star:nth-child(6) {{ top: 60%; left: 30%; animation-delay: 2.5s; }}
        .star:nth-child(7) {{ top: 70%; left: 70%; animation-delay: 0.3s; }}
        .star:nth-child(8) {{ top: 80%; left: 40%; animation-delay: 0.8s; }}
        .star:nth-child(9) {{ top: 15%; left: 60%; animation-delay: 1.2s; }}
        .star:nth-child(10) {{ top: 85%; left: 15%; animation-delay: 1.8s; }}
        .star:nth-child(11) {{ top: 25%; left: 85%; animation-delay: 0.6s; }}
        .star:nth-child(12) {{ top: 45%; left: 25%; animation-delay: 1.4s; }}
        .star:nth-child(13) {{ top: 65%; left: 75%; animation-delay: 2.2s; }}
        .star:nth-child(14) {{ top: 35%; left: 45%; animation-delay: 0.9s; }}
        .star:nth-child(15) {{ top: 75%; left: 55%; animation-delay: 1.7s; }}

        /* Большие яркие звезды */
        .star.bright {{
            width: 3px;
            height: 3px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}

        .star:nth-child(3), .star:nth-child(7), .star:nth-child(12) {{
            width: 3px;
            height: 3px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}

        .container {{
            position: relative;
            z-index: 1;
            text-align: center;
            max-width: 480px;
            width: 100%;
        }}

        /* Логотип с свечением */
        .logo {{
            width: 360px;
            height: 360px;
            margin: 0 auto 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 0 50px rgba(255, 255, 255, 0.5));
            animation: glow 3s ease-in-out infinite;
        }}

        .logo img {{
            width: 360px;
            height: 360px;
            object-fit: contain;
        }}

        @keyframes glow {{
            0%, 100% {{ filter: drop-shadow(0 0 50px rgba(255, 255, 255, 0.5)); }}
            50% {{ filter: drop-shadow(0 0 70px rgba(255, 255, 255, 0.7)); }}
        }}

        h1 {{
            font-size: 96px;
            font-weight: 400;
            color: white;
            margin-bottom: 70px;
            letter-spacing: 3px;
            font-family: 'Playfair Display', serif;
        }}

        /* Кнопки */
        .btn {{
            display: block;
            width: 100%;
            max-width: 440px;
            margin: 0 auto 20px;
            padding: 20px 40px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            font-family: 'Geist', sans-serif;
        }}

        .btn-primary {{
            background: white;
            color: #516db3;
            box-shadow: 0 4px 20px rgba(255, 255, 255, 0.3);
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(255, 255, 255, 0.4);
        }}

        .btn-secondary {{
            background: transparent;
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.5);
        }}

        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.8);
        }}

        .divider-text {{
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
            margin: 30px 0 20px;
        }}

        /* Уведомление об успешном копировании */
        .toast {{
            position: fixed;
            top: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: rgba(255, 255, 255, 0.95);
            color: #516db3;
            padding: 16px 32px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.4s ease;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }}

        .toast.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}

        @media (max-width: 640px) {{
            .logo {{
                width: 240px;
                height: 240px;
                margin-bottom: 40px;
            }}

            .logo img {{
                width: 240px;
                height: 240px;
            }}

            h1 {{
                font-size: 64px;
                margin-bottom: 50px;
                letter-spacing: 2px;
            }}

            .btn {{
                padding: 18px 32px;
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <!-- Звезды на фоне -->
    <div class="stars">
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
    </div>

    <div class="container">
        <!-- Логотип SVG -->
        <div class="logo">
            <img src="/logo.svg" alt="{profile_title} Logo">
        </div>

        <h1>{profile_title}</h1>

        <!-- Кнопка открытия в Happ -->
        <a href="{safe_happ_deeplink}" onclick="openHapp(event)" class="btn btn-primary" rel="noopener noreferrer">Открыть в Happ</a>

        <p class="divider-text">Или скопируйте ссылку вручную</p>

        <!-- Кнопка копирования -->
        <button onclick="copyUrl()" class="btn btn-secondary">Копировать вручную</button>
        <a href="{safe_subscription_url}" class="btn btn-secondary" rel="noopener noreferrer">Открыть URL подписки</a>
    </div>

    <!-- Уведомление -->
    <div class="toast" id="toast">
        ✓ Ссылка скопирована
    </div>

    <script>
        const registrationUrl = {js_device_registration_url};

        function getDeviceToken() {{
            let token = localStorage.getItem('arcvpn_device_token');
            if (!token) {{
                const bytes = new Uint8Array(24);
                crypto.getRandomValues(bytes);
                token = btoa(String.fromCharCode(...bytes)).replace(/[^A-Za-z0-9_-]/g, '').slice(0, 48);
                localStorage.setItem('arcvpn_device_token', token);
            }}
            return token;
        }}

        async function devicePayload() {{
            let model = '';
            let platform = navigator.userAgentData?.platform || navigator.platform || '';
            let browser = navigator.userAgentData?.brands?.map((item) => item.brand).join(', ') || '';
            try {{
                const hints = await navigator.userAgentData?.getHighEntropyValues?.(['model', 'platformVersion']);
                model = hints?.model || '';
            }} catch (_) {{}}
            return {{
                device_token: getDeviceToken(),
                platform,
                model,
                browser,
                screen_size: `${{screen.width}}x${{screen.height}}`,
            }};
        }}

        async function registerDevice() {{
            try {{
                const payload = await devicePayload();
                await fetch(registrationUrl, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload),
                    credentials: 'omit',
                    keepalive: true,
                }});
                return payload;
            }} catch (_) {{
                return null;
            }}
        }}

        const registration = registerDevice();

        function openHapp(event) {{
            event.preventDefault();
            const href = event.currentTarget.href;
            // Deep-link должен открыться внутри исходного пользовательского клика.
            // Фоновая регистрация уже стартовала при загрузке страницы; beacon
            // лишь дублирует её без задержки перехода в Happ.
            registration.then((payload) => {{
                if (payload && navigator.sendBeacon) {{
                    navigator.sendBeacon(registrationUrl, new Blob([JSON.stringify(payload)], {{type: 'application/json'}}));
                }}
            }});
            window.location.href = href;
        }}

        function copyUrl() {{
            const url = {js_subscription_url};
            const toast = document.getElementById('toast');

            navigator.clipboard.writeText(url).then(() => {{
                showToast();
            }}).catch(() => {{
                // Fallback для старых браузеров
                const textarea = document.createElement('textarea');
                textarea.value = url;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast();
            }});

            function showToast() {{
                toast.classList.add('show');
                setTimeout(() => {{
                    toast.classList.remove('show');
                }}, 2500);
            }}
        }}
    </script>
</body>
</html>"""


def render_user_agreement(
    *, profile_title: str, updated_date: str, support_url: str,
    operator_name: str, operator_inn: str, operator_registration: str,
    operator_address: str, contact_email: str,
) -> str:
    """Публичная читаемая версия соглашения; та же дата показывается в WebApp."""
    title = html.escape(profile_title)
    updated = html.escape(updated_date)
    support = html.escape(support_url, quote=True)
    legal = {
        "name": html.escape(operator_name),
        "inn": html.escape(operator_inn),
        "registration": html.escape(operator_registration),
        "address": html.escape(operator_address),
        "email": html.escape(contact_email),
    }
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Пользовательское соглашение — {title}</title>
<style>
:root{{color-scheme:dark;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#03070e;color:#f7f9fd}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(70% 35% at 95% 5%,#16385c66,transparent 72%),#03070e}}
main{{width:min(100% - 32px,720px);margin:auto;padding:48px 0 80px}} .brand{{font-size:18px;font-weight:800}}
.meta{{margin:8px 0 34px;color:#aab6c5;font-size:13px}} article{{padding:clamp(20px,5vw,38px);border-radius:28px;background:#0a111b}}
h1{{margin:0 0 22px;font-size:clamp(28px,7vw,46px);line-height:1.05;letter-spacing:-.045em}} h2{{margin:28px 0 9px;font-size:18px}}
p,li{{color:#bdc7d2;font-size:14px;line-height:1.65}} a{{color:#91d3f8}} .note{{padding:14px 16px;border-radius:14px;background:#111c2a}}
</style></head><body><main><div class="brand">{title}</div><p class="meta">Обновлено: {updated}</p><article>
<h1>Пользовательское соглашение</h1>
<p>Используя {title}, вы принимаете эти условия. Если вы с ними не согласны, не подключайте и не оплачивайте сервис.</p>
<h2>1. Аккаунт и доступ</h2><p>Аккаунт связан с Telegram. Подтверждённый email может использоваться как дополнительный способ входа в тот же аккаунт и не создаёт новую учётную запись. Пользователь отвечает за сохранность своих ссылок подключения.</p>
<h2>2. Подписка и оплата</h2><p>Срок, цена и состав тарифа показываются до оплаты. Доступ предоставляется на оплаченный период. Вопросы об ошибочном платеже или возврате рассматриваются поддержкой с учётом обязательных требований применимого законодательства.</p>
<h2>3. Допустимое использование</h2><p>Запрещено использовать сервис для нарушения закона и прав третьих лиц, атак, распространения вредоносного кода, спама, мошенничества, перепродажи доступа или действий, создающих чрезмерную нагрузку.</p>
<h2>4. Доступность сервиса</h2><p>Мы поддерживаем инфраструктуру и устраняем неисправности, однако доступность отдельных серверов, протоколов и сторонних сайтов может меняться. Эти условия не ограничивают права потребителя, которые нельзя исключить соглашением.</p>
<h2>5. Данные</h2><p>Для работы сервиса обрабатываются Telegram ID, имя пользователя, подтверждённый email, сведения о подписке и оплате. При импорте подписки сохраняются случайный идентификатор, тип устройства и модель только когда её сообщает браузер или операционная система. Содержимое интернет-трафика не сохраняется.</p>
<h2>6. Изменения условий</h2><p>При изменении документа обновляется дата публикации. Существенные изменения применяются после публикации новой версии.</p>
<h2>7. Поддержка</h2><p class="note">Вопросы по сервису, оплате и данным можно направить <a href="{support}">в поддержку {title}</a>.</p>
<h2>8. Реквизиты оператора</h2><p>Оператор: {legal['name']}<br>ИНН: {legal['inn']}<br>ОГРНИП/ОГРН: {legal['registration']}<br>Адрес: {legal['address']}<br>Email: {legal['email']}</p>
</article></main></body></html>"""
