"""HTML-страницы subscription-сервиса.

Вынесено из subscription_api.py, чтобы не держать большой шаблон внутри логики
роутинга. Шаблон — обычный f-string; CSS-скобки экранированы как {{ }}.
"""

import html


def render_silent_incy_import_page() -> str:
    """Blank HTTPS bridge that immediately opens an encrypted INCY link."""
    return """<!doctype html>
<html lang="ru"><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="color-scheme" content="dark"><title></title>
  <style>html,body{width:100%;height:100%;margin:0;background:#02060c;overflow:hidden}</style>
</head><body aria-label="Открытие INCY"><script>
  function target() {
    const payload = decodeURIComponent(location.hash.slice(1));
    return /^[A-Za-z0-9_-]+$/.test(payload) ? `incy://crypt1/${payload}` : '';
  }
  let opening = false;
  function openIncy() {
    if (opening || !target()) return;
    opening = true;
    window.location.replace(target());
  }
  document.addEventListener('click', openIncy);
  setTimeout(openIncy, 40);
</script></body></html>"""


def render_silent_import_page(
    js_subscription_url: str,
    js_device_registration_url: str,
    js_server_device_token: str = "null",
) -> str:
    """Blank HTTPS bridge that registers the browser and immediately opens Happ."""
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="color-scheme" content="dark">
  <title></title>
  <style>html,body{{width:100%;height:100%;margin:0;background:#02060c;overflow:hidden}}</style>
</head>
<body aria-label="Открытие Happ">
<script>
  const subscriptionUrl = {js_subscription_url};
  const registrationUrl = {js_device_registration_url};
  const serverDeviceToken = {js_server_device_token};
  function deviceToken() {{
    if (serverDeviceToken) {{
      localStorage.setItem('arcvpn_device_token', serverDeviceToken);
      return serverDeviceToken;
    }}
    let token = localStorage.getItem('arcvpn_device_token');
    if (!token) {{
      const bytes = new Uint8Array(24);
      crypto.getRandomValues(bytes);
      token = btoa(String.fromCharCode(...bytes)).replace(/[^A-Za-z0-9_-]/g, '').slice(0, 48);
      localStorage.setItem('arcvpn_device_token', token);
    }}
    return token;
  }}
  async function register() {{
    let model = '';
    let platform = navigator.userAgentData?.platform || navigator.platform || '';
    let browser = navigator.userAgentData?.brands?.map(item => item.brand).join(', ') || '';
    const payload = {{
      device_token: deviceToken(), platform, model, browser,
      screen_size: `${{screen.width}}x${{screen.height}}`,
    }};
    const response = await fetch(registrationUrl, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
      credentials: 'omit',
      cache: 'no-store',
    }});
    if (!response.ok) throw new Error(`registration failed: ${{response.status}}`);
    return response.json();
  }}
  function fallbackDeeplink() {{
    const target = new URL(subscriptionUrl);
    target.searchParams.set('device', deviceToken());
    return `happ://add/${{target.toString()}}`;
  }}
  let opening = false;
  const openHapp = async () => {{
    if (opening) return;
    opening = true;
    let target = fallbackDeeplink();
    try {{
      const result = await register();
      if (result?.import_url?.startsWith('happ://add/')) target = result.import_url;
    }} catch (_) {{}}
    window.location.replace(target);
  }};
  document.addEventListener('click', openHapp);
  setTimeout(openHapp, 40);
</script>
</body>
</html>"""


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
        const subscriptionUrl = {js_subscription_url};

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

        function happDeepLink() {{
            const separator = subscriptionUrl.includes('?') ? '&' : '?';
            const deviceUrl = `${{subscriptionUrl}}${{separator}}device=${{encodeURIComponent(getDeviceToken())}}`;
            return `happ://add/${{deviceUrl}}`;
        }}

        function openHapp(event) {{
            event.preventDefault();
            const href = happDeepLink();
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

        // Telegram допускает в inline-кнопках только HTTPS. Мост сразу пытается
        // открыть Happ; кнопка остаётся fallback для браузеров, запрещающих
        // custom scheme без дополнительного касания.
        const primaryButton = document.querySelector('.btn-primary');
        if (primaryButton) primaryButton.href = happDeepLink();
        setTimeout(() => {{
            window.location.href = happDeepLink();
        }}, 120);

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
    def public_legal_value(value: str) -> str:
        clean = str(value or "").strip()
        return "" if clean.startswith("[УКАЖИТЕ ") else html.escape(clean)

    legal = {
        "name": public_legal_value(operator_name),
        "inn": public_legal_value(operator_inn),
        "registration": public_legal_value(operator_registration),
        "address": public_legal_value(operator_address),
        "email": public_legal_value(contact_email),
    }
    legal_rows = "".join(
        f"<dt>{label}</dt><dd>{value}</dd>"
        for label, value in (
            ("Оператор", legal["name"]),
            ("ИНН", legal["inn"]),
            ("ОГРНИП/ОГРН", legal["registration"]),
            ("Адрес", legal["address"]),
            ("Email", legal["email"]),
        )
        if value
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#03070e"><title>Соглашение и конфиденциальность — {title}</title>
<style>
:root{{color-scheme:dark;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#03070e;color:#f7f9fd;scroll-behavior:smooth}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(60% 24% at 85% 0,#16385c55,transparent 75%),#03070e}}
main{{width:min(100% - 32px,820px);margin:auto;padding:42px 0 88px}}.brand{{color:#f8fbff;font-size:18px;font-weight:800;text-decoration:none}}
.meta{{margin:8px 0 28px;color:#8492a3;font-size:13px}}.hero{{padding:clamp(24px,6vw,48px);border:1px solid #a6dafa18;border-radius:30px;background:#08101ae8}}
h1{{max-width:680px;margin:0;font-size:clamp(32px,7vw,54px);line-height:1.02;letter-spacing:-.05em}}.lede{{max-width:650px;margin:18px 0 0;color:#aebac8;line-height:1.65}}
nav{{display:flex;flex-wrap:wrap;gap:8px;margin-top:28px}}nav a{{padding:10px 14px;border:1px solid #9ad9fa22;border-radius:999px;color:#b9def3;font-size:13px;text-decoration:none}}
article{{margin-top:18px;padding:clamp(22px,5vw,42px);border:1px solid #ffffff0c;border-radius:28px;background:#080f18}}
h2{{margin:0 0 8px;font-size:clamp(25px,5vw,36px);letter-spacing:-.035em}}h3{{margin:30px 0 9px;font-size:18px;line-height:1.3}}
p,li{{color:#b5c0cc;font-size:14px;line-height:1.7}}ul{{padding-left:22px}}li+li{{margin-top:6px}}a{{color:#91d3f8}}.eyebrow{{margin:0 0 12px;color:#74c3ee;font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
.note{{padding:15px 17px;border:1px solid #9edcff16;border-radius:15px;background:#101b29}}.details{{display:grid;grid-template-columns:max-content 1fr;gap:8px 16px;margin-top:18px}}.details dt{{color:#7f8d9d}}.details dd{{margin:0;color:#c7d0da;overflow-wrap:anywhere}}
@media(max-width:520px){{main{{width:min(100% - 20px,820px);padding-top:18px}}.hero,article{{border-radius:22px}}.details{{grid-template-columns:1fr;gap:3px}}.details dd{{margin-bottom:10px}}}}
@media(prefers-reduced-motion:reduce){{:root{{scroll-behavior:auto}}}}
</style></head><body><main><a class="brand" href="/">{title}</a><p class="meta">Редакция от {updated}</p>
<header class="hero"><p class="eyebrow">Правила сервиса</p><h1>Пользовательское соглашение и конфиденциальность</h1>
<p class="lede">Здесь собраны условия использования {title} и правила обработки данных. Прочитайте их до регистрации, активации пробного периода или оплаты.</p>
<nav aria-label="Разделы документа"><a href="#agreement">Соглашение</a><a href="#privacy">Конфиденциальность</a><a href="#contacts">Контакты</a></nav></header>

<article id="agreement"><p class="eyebrow">Часть I</p><h2>Пользовательское соглашение</h2>
<h3>1. Общие положения</h3><p>Настоящее соглашение регулирует использование сайта, личного кабинета, Telegram-бота, ссылок подписки и иных интерфейсов {title}. Оператор предлагает пользователю удалённый доступ к функциональности VPN-сервиса на условиях выбранного тарифа.</p>
<p>Соглашение считается принятым, когда пользователь явно подтверждает согласие в интерфейсе, регистрируется, активирует пробный доступ, оплачивает тариф либо начинает использовать предоставленный доступ. Если пользователь не согласен с условиями, ему следует прекратить использование сервиса.</p>
<h3>2. Аккаунт и доступ</h3><p>Аккаунт может быть создан через Telegram или подтверждённый email. Email может быть привязан к существующему аккаунту. Персональная ссылка подписки и коды доступа предназначены для пользователя и разрешённых им устройств в пределах тарифа; пользователь отвечает за их сохранность и своевременное обращение в поддержку при компрометации.</p>
<h3>3. Тарифы и предоставление услуги</h3><p>Актуальные цена, срок, лимит устройств, объём отдельных видов трафика и иные существенные параметры показываются до оплаты. Доступ активируется автоматически после подтверждения платежа либо на условиях пробной, реферальной или промоакции. Состав серверов, маршрутов и поддерживаемых приложений может меняться для безопасности и работоспособности сервиса без ухудшения уже оплаченного объёма прав.</p>
<h3>4. Оплата и автопродление</h3><p>Платежи обрабатывает платёжный провайдер. Автопродление подключается только по отдельному выбору пользователя при оплате. При его подключении провайдер сохраняет способ оплаты, а {title} — его служебный идентификатор и параметры следующего списания. Отключить автопродление и отвязать способ оплаты можно в настройках; действующий оплаченный период при этом сохраняется.</p>
<h3>5. Отказ и возвраты</h3><p>Пользователь вправе отказаться от услуги и обратиться в поддержку по вопросу возврата. Сумма определяется с учётом фактически предоставленного доступа, понесённых оператором расходов, причины обращения и обязательных требований законодательства. Ошибочное списание, двойная оплата или непредоставление оплаченного доступа рассматриваются отдельно. Ничто в соглашении не ограничивает права потребителя, которые нельзя отменить договором.</p>
<h3>6. Допустимое использование</h3><p>Запрещены противоправные действия, нарушение прав третьих лиц, атаки на системы и сети, распространение вредоносного кода, спам, мошенничество, перепродажа доступа, обход технических лимитов и нагрузка, мешающая другим пользователям. При обоснованных признаках нарушения оператор вправе временно ограничить доступ, запросить пояснения или прекратить обслуживание соразмерно нарушению и требованиям закона.</p>
<h3>7. Доступность и ответственность</h3><p>Оператор поддерживает инфраструктуру, но не гарантирует непрерывную доступность каждого сервера, протокола, оператора связи или стороннего ресурса. Возможны технические работы и сбои внешних сетей. В пределах, допускаемых законом, оператор не отвечает за косвенные последствия, вызванные действиями пользователя или третьих лиц; обязательная ответственность оператора и законные способы защиты пользователя сохраняются.</p>
<h3>8. Пробные периоды и бонусы</h3><p>Правила пробных периодов, промокодов и реферальной программы отображаются в интерфейсе. Они могут быть ограничены одним аккаунтом или пользователем. При мультиаккаунтинге, накрутке или иной недобросовестной активации бонус может быть отменён.</p>
<h3>9. Изменение и прекращение</h3><p>Новая редакция публикуется на этой странице с новой датой. Существенные изменения не применяются задним числом к уже оплаченному периоду, если иное не требуется законом. Пользователь может прекратить использование сервиса и отключить автопродление; удаление аккаунта и данных выполняется по обращению с учётом обязательных сроков хранения.</p>
<h3>10. Разрешение споров</h3><p>Сначала стороны стремятся урегулировать вопрос через поддержку. Если договориться не удалось, спор рассматривается по применимому законодательству и правилам подсудности, включая специальные права потребителя.</p></article>

<article id="privacy"><p class="eyebrow">Часть II</p><h2>Политика конфиденциальности</h2>
<h3>1. Кто обрабатывает данные</h3><p>Оператор {title}, указанный в разделе «Контакты», обрабатывает данные для заключения и исполнения соглашения, работы сервиса, расчётов, поддержки, безопасности и выполнения требований закона.</p>
<h3>2. Какие данные обрабатываются</h3><ul><li>идентификатор Telegram, публичные данные профиля Telegram и подтверждённый email;</li><li>данные аккаунта, согласий, подписки, тарифа, срока, лимитов, бонусов и обращений в поддержку;</li><li>сумма, статус, время и технический идентификатор платежа; реквизиты карты оператор не получает;</li><li>служебный идентификатор сохранённого способа оплаты, если пользователь включил автопродление;</li><li>случайный идентификатор устройства, тип платформы, название или модель — только в объёме, который сообщает приложение, браузер или ОС;</li><li>технические журналы безопасности и работоспособности, включая время запросов, сетевые адреса и сведения об ошибках, когда это необходимо для защиты и диагностики.</li></ul>
<p class="note">{title} не предназначен для анализа поведения пользователя в интернете и не ведёт список посещённых сайтов. Содержимое передаваемого через VPN интернет-трафика намеренно не сохраняется.</p>
<h3>3. Цели и основания</h3><p>Данные используются для создания и защиты аккаунта, предоставления подписки, учёта лимитов и устройств, проведения и сверки платежей, автопродления по выбору пользователя, поддержки, предотвращения злоупотреблений, улучшения стабильности и исполнения обязанностей оператора. Основаниями служат заключение и исполнение соглашения, требования закона, законный интерес в защите сервиса и согласие — когда оно требуется.</p>
<h3>4. Передача и обработчики</h3><p>В необходимом объёме данные могут передаваться поставщикам хостинга и инфраструктуры, Telegram, сервису отправки email, платёжному провайдеру, приложениям для импорта подписки по действию пользователя, а также государственным органам при наличии законного требования. Такие лица получают только данные, необходимые для своей функции, и действуют по собственным правилам либо договору с оператором.</p>
<h3>5. Сроки хранения и удаление</h3><p>Данные хранятся не дольше, чем требуют указанные цели: данные активного аккаунта — пока действует аккаунт и необходим разумный срок после его закрытия; платёжные и учётные документы — в сроки, установленные законом; технические журналы — ограниченный срок, необходимый для безопасности и диагностики. После достижения цели данные удаляются или обезличиваются, если закон не требует дальнейшего хранения.</p>
<h3>6. Защита данных</h3><p>Применяются разграничение доступа, защищённая передача, контроль сессий, журналирование административных действий, резервирование и другие разумные организационные и технические меры. Ни один способ передачи и хранения не исключает риск полностью, поэтому пользователь также должен защищать email, Telegram и персональную ссылку.</p>
<h3>7. Права пользователя</h3><p>Пользователь вправе запросить сведения об обработке, уточнение, блокирование или удаление неточных либо незаконно обрабатываемых данных, отозвать согласие, когда обработка основана на нём, и обжаловать действия оператора. Для защиты аккаунта перед выполнением запроса может потребоваться подтверждение личности.</p>
<h3>8. Обновления политики</h3><p>Актуальная версия всегда доступна по этому адресу. При существенном изменении целей или состава обработки оператор обновляет документ и, когда это требуется, запрашивает новое согласие.</p></article>

<article id="contacts"><p class="eyebrow">Связь с оператором</p><h2>Контакты и реквизиты</h2>
<p class="note">Вопросы по сервису, оплате, возвратам и данным можно направить <a href="{support}">в поддержку {title}</a> или на email, указанный ниже.</p>
<dl class="details">{legal_rows}</dl></article>
</main></body></html>"""
