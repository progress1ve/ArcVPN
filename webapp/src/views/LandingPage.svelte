<script>
  import { onMount } from 'svelte'
  import ArcIcon from '../components/ArcIcon.svelte'
  import DeviceIcon from '../components/DeviceIcon.svelte'

  const base = import.meta.env.BASE_URL
  const productNames = { economy: 'Эконом', standard: 'Стандарт', family: 'Семейный' }
  const productCopy = {
    economy: 'Для одного-двух личных устройств',
    standard: 'С отдельным запасом обхода для сложных сетей',
    family: 'Больше устройств и увеличенный запас обхода',
  }
  const appCatalog = {
    happ: {
      label: 'Happ',
      art: `${base}assets/arc-flow/connect-happ-phone-v2.png`,
      stores: {
        iphone: 'https://apps.apple.com/app/happ-proxy-utility/id6504287215',
        android: 'https://play.google.com/store/apps/details?id=com.happproxy',
        windows: 'https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe',
        linux: 'https://happ.info/',
      },
    },
    incy: {
      label: 'INCY',
      art: `${base}assets/arc-flow/connect-incy-phone-v1.png`,
      stores: {
        iphone: 'https://apps.apple.com/ru/app/incy/id6756943388',
        android: 'https://play.google.com/store/apps/details?id=llc.itdev.incy',
        windows: 'https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-windows-setup.exe',
        linux: 'https://incy.host/download/linux',
      },
    },
  }
  const devices = [
    { id: 'iphone', label: 'iPhone / iPad', icon: 'apple' },
    { id: 'android', label: 'Android', icon: 'android' },
    { id: 'windows', label: 'Windows', icon: 'windows' },
    { id: 'linux', label: 'Linux', icon: 'linux' },
  ]
  const featureRows = [
    ['Автовыбор', 'Один профиль для обычного использования — без ручного перебора списка.'],
    ['Обычные локации', 'Выбирайте страну, когда хотите управлять подключением сами.'],
    ['Обход глушилок', 'Специальные профили расходуют только отдельный запас, а не основной трафик.'],
    ['Одна ссылка', 'Обычные локации, сервисные профили и обход обновляются вместе с подпиской.'],
  ]
  const faqs = [
    ['Как установить и подключить ArcVPN?', 'Откройте личный кабинет, выберите устройство и установите Happ или INCY. Затем импортируйте ссылку подписки и выберите Автовыбор.'],
    ['Что такое трафик обхода глушилок?', 'Это отдельный запас для специальных профилей, которые помогают в сложных сетях. Основной трафик остаётся безлимитным и учитывается отдельно.'],
    ['На скольких устройствах работает подписка?', 'Количество зависит от тарифа. Доступные слоты видны в тарифе и личном кабинете; дополнительные устройства можно докупить.'],
    ['Что делать, если VPN не подключается?', 'Обновите подписку в приложении, включите Автовыбор и повторите подключение. Если не помогло, напишите в поддержку и приложите модель устройства и скриншот ошибки.'],
  ]
  const fallbackTariffs = import.meta.env.DEV ? [
    ['economy',1,95,2,0],['standard',1,145,3,45],['family',1,329,8,115],
    ['economy',3,259,2,0],['standard',3,399,3,45],['family',3,899,8,115],
    ['economy',6,479,2,0],['standard',6,759,3,45],['family',6,1699,8,115],
    ['economy',12,929,2,0],['standard',12,1469,3,45],['family',12,3389,8,115],
  ].map((p, i) => ({ id:i+1, product_code:p[0], period_months:p[1], price_rub:p[2], monthly_rub:Math.round(p[2]/p[1]), device_limit:p[3], lte_quota_gb:p[4] })) : []

  let scrolled = false
  let activeSection = 'subscription'
  let heroVideoEnabled = false
  let tariffs = []
  let config = {}
  let dataError = false
  let selectedPeriod = 3
  let selectedApp = 'happ'
  let selectedDevice = 'iphone'
  let openFaq = -1
  let customMonths = 3
  let customDevices = 3
  let customLte = 45
  let customQuote = null
  let quoteBusy = true
  let quoteTimer

  $: periodTariffs = tariffs.filter((item) => Number(item.period_months) === selectedPeriod)
  $: selectedStore = appCatalog[selectedApp].stores[selectedDevice]
  $: if (customMonths && customDevices && customLte >= 0) scheduleQuote(customMonths, customDevices, customLte)

  function track(event, details = {}) {
    window.dataLayer?.push({ event, ...details })
  }
  function cabinetUrl(params = {}) {
    const query = new URLSearchParams(params)
    return `/app${query.size ? `?${query}` : ''}`
  }
  function scheduleQuote(months, devicesCount, lte) {
    clearTimeout(quoteTimer)
    quoteTimer = setTimeout(() => loadQuote(months, devicesCount, lte), 180)
  }
  function previewCustomPrice(months, devicesCount, lte) {
    const prices = Object.fromEntries(fallbackTariffs.filter((plan) => plan.period_months === months).map((plan) => [plan.product_code, plan.price_rub]))
    if (!prices.economy || !prices.standard || !prices.family) return 0
    const standardDelta = prices.standard - prices.economy
    const deviceRate = standardDelta / 5
    const firstBypassRate = (standardDelta - deviceRate) / 45
    const upperBypassRate = (prices.family - prices.economy - 6 * deviceRate - 45 * firstBypassRate) / 70
    const basePrice = Math.max(1, Math.round(prices.economy + (devicesCount - 2) * deviceRate + Math.min(lte,45) * firstBypassRate + Math.max(0,lte - 45) * upperBypassRate))
    if (devicesCount === 2 && lte === 0) return prices.economy
    if (devicesCount === 3 && lte === 45) return prices.standard
    if (devicesCount === 8 && lte === 115) return prices.family
    let price = Math.ceil(basePrice * 1.08)
    if (lte > 0) price = Math.max(price, 100 * months)
    if (devicesCount <= 3 && lte <= 45) price = Math.min(price, prices.standard - 1)
    if (devicesCount <= 8 && lte <= 115) price = Math.min(price, prices.family - 1)
    return price
  }
  async function loadQuote(months, devicesCount, lte) {
    quoteBusy = true
    try {
      const qs = new URLSearchParams({ period_months: months, device_limit: devicesCount, lte_quota_gb: lte })
      const response = await fetch(`/api/public/custom-tariff-quote?${qs}`)
      if (!response.ok) throw new Error('quote')
      customQuote = await response.json()
    } catch (_) {
      const previewPrice = import.meta.env.DEV ? previewCustomPrice(months, devicesCount, lte) : 0
      customQuote = previewPrice ? { price_rub: previewPrice, monthly_rub: Math.round(previewPrice / months), preview: true } : null
    } finally {
      quoteBusy = false
    }
  }
  async function loadPublicData() {
    try {
      const [tariffResponse, configResponse] = await Promise.all([
        fetch('/api/public/tariffs'), fetch('/api/public/config'),
      ])
      if (!tariffResponse.ok || !configResponse.ok) throw new Error('public data')
      tariffs = (await tariffResponse.json()).tariffs || []
      config = await configResponse.json()
    } catch (_) {
      tariffs = fallbackTariffs
      dataError = !import.meta.env.DEV
    }
  }
  function selectTariff(plan) {
    track('landing_tariff_select', { product: plan.product_code, months: plan.period_months })
    location.href = cabinetUrl({ screen: 'tariffs', product: plan.product_code, months: plan.period_months })
  }
  onMount(() => {
    document.title = 'ArcVPN — одна подписка для свободного интернета'
    const description = document.querySelector('meta[name="description"]')
    if (description) description.content = 'ArcVPN для iPhone, Android, Windows и Linux: подписка для Happ и INCY, актуальные тарифы и удобное управление.'
    document.documentElement.classList.add('landing-document')
    heroVideoEnabled = !matchMedia('(max-width: 600px)').matches
      && !matchMedia('(prefers-reduced-motion: reduce)').matches
      && !navigator.connection?.saveData
    loadPublicData()
    const handleScroll = () => scrolled = scrollY > 36
    addEventListener('scroll', handleScroll, { passive: true })
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a,b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (visible?.target?.id) activeSection = visible.target.id
    }, { rootMargin: '-25% 0px -60%', threshold: [0,.2,.5] })
    document.querySelectorAll('[data-nav-section]').forEach((section) => observer.observe(section))
    return () => {
      removeEventListener('scroll', handleScroll)
      observer.disconnect()
      clearTimeout(quoteTimer)
      document.documentElement.classList.remove('landing-document')
    }
  })
</script>

<svelte:head>
  <meta name="theme-color" content="#030508" />
  <meta property="og:title" content="ArcVPN — одна подписка для свободного интернета" />
  <meta property="og:description" content="Подключение через Happ и INCY, актуальные тарифы и управление устройствами в личном кабинете." />
</svelte:head>

<div class="landing">
  <a class="skip" href="#main">К содержанию</a>

  <header class:compact={scrolled} class="landing-nav">
    <a class="brand" href="#top" aria-label="ArcVPN — наверх">
      <img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" />
      <b>ArcVPN</b>
    </a>
    <nav class="desktop-nav" aria-label="Основная навигация">
      {#each [['subscription','Попробовать'],['apps','Приложения'],['tariffs','Тарифы'],['cabinet','Кабинет'],['faq','Вопросы']] as item}
        <a class:active={activeSection === item[0]} href={`#${item[0]}`}>{item[1]}</a>
      {/each}
    </nav>
    <a class="nav-cta" href="/app" on:click={() => track('landing_cabinet_click', { place:'nav' })}>Личный кабинет <ArcIcon name="arrow" size={17} /></a>
  </header>

  <main id="main">
    <section class="hero" id="top">
      {#if heroVideoEnabled}
        <video class="hero-current" autoplay muted loop playsinline preload="metadata" poster={`${base}assets/landing/northern-flow.webp`} aria-hidden="true">
          <source src={`${base}assets/landing/northern-flow.webm`} type="video/webm" />
          <source src={`${base}assets/landing/northern-flow.mp4`} type="video/mp4" />
        </video>
      {:else}
        <img class="hero-current" src={`${base}assets/landing/northern-flow.webp`} alt="" aria-hidden="true" width="1280" height="720" />
      {/if}
      <div class="hero-copy">
        <h1>Одна подписка.<br /><span>Свободный интернет.</span></h1>
        <p class="hero-text">Обычные подключения для каждого дня и отдельные профили обхода глушилок — когда привычной сети недостаточно.</p>
        <div class="hero-actions">
          <a class="primary" href="/app" on:click={() => track('landing_cabinet_click', { place:'hero' })}>Открыть личный кабинет <ArcIcon name="arrow" size={18} /></a>
          <a class="quiet-link" href="#subscription">Попробовать ArcVPN</a>
        </div>
      </div>
      <div class="platform-line"><span>iPhone / iPad</span><span>Android</span><span>Windows</span><span>Linux</span></div>
    </section>

    <section class="trial-section" id="subscription" data-nav-section>
      <div class="trial-intro">
        <h2>Много локаций.<br />Проверьте сами.</h2>
        <p>В подписке есть Автовыбор, обычные локации и отдельные профили обхода. Актуальный список обновляется автоматически — проще открыть пробный доступ и выбрать подходящий вариант на своём устройстве.</p>
      </div>
      <div class="trial-panel">
        <article class="trial-free">
          <span>В Telegram</span>
          <strong>Бесплатно</strong>
          <p>Для нового пользователя: 7 дней ArcVPN и 5 ГБ обхода глушилок. Бот активирует пробную подписку автоматически.</p>
          {#if config.bot_url}
            <a href={config.bot_url} target="_blank" rel="noopener" on:click={() => track('landing_trial_click', { channel:'bot' })}>Попробовать в боте <ArcIcon name="arrow" size={18} /></a>
          {/if}
        </article>
        <article class="trial-site">
          <span>На сайте</span>
          <strong>10 ₽</strong>
          <p>Для нового email-аккаунта: 7 дней Standard и 5 ГБ обхода. Автопродление можно отключить в настройках.</p>
          <a href="/app" on:click={() => track('landing_trial_click', { channel:'site' })}>Попробовать на сайте <ArcIcon name="arrow" size={18} /></a>
        </article>
      </div>
    </section>

    <section class="apps-section" id="apps" data-nav-section>
      <div class="apps-proof">
        <div class="phone-well">
          <div class="app-switch" aria-label="Выбор приложения">
            {#each Object.entries(appCatalog) as [id, app]}
              <button class:active={selectedApp === id} on:click={() => selectedApp = id}>{app.label}</button>
            {/each}
          </div>
          <img src={appCatalog[selectedApp].art} alt={`Приложение ${appCatalog[selectedApp].label} на телефоне`} />
        </div>
        <div class="app-copy">
          <h2>Работает на ваших устройствах</h2>
          <p>Выберите приложение и платформу. Ссылка импорта и следующие шаги появятся в личном кабинете.</p>
          <div class="device-tabs" role="group" aria-label="Платформа">
            {#each devices as device}
              <button class:active={selectedDevice === device.id} on:click={() => selectedDevice = device.id}>
                <DeviceIcon name={device.icon} size={20} /><span>{device.label}</span>
              </button>
            {/each}
          </div>
          <div class="app-actions">
            <a class="primary" href={selectedStore} target="_blank" rel="noopener" on:click={() => track('landing_app_install_click', { app:selectedApp, platform:selectedDevice })}>Установить {appCatalog[selectedApp].label} <ArcIcon name="arrow" size={18} /></a>
          </div>
        </div>
      </div>

      <div class="feature-ledger" id="features">
        {#each featureRows as feature}
          <article><h3>{feature[0]}</h3><p>{feature[1]}</p></article>
        {/each}
      </div>
    </section>

    <section class="bypass-section">
      <div>
        <h2>Обход глушилок — отдельный запас</h2>
        <p>Основной трафик ArcVPN остаётся безлимитным. Дополнительные гигабайты расходуются только при выборе специальных профилей обхода — для сетей, где обычное подключение не справляется.</p>
        <p>Если запас закончится, Автовыбор и обычные локации продолжат работать. Объём обхода можно выбрать в тарифе или докупить позже в личном кабинете.</p>
        <small>Доступность зависит от сети, устройства и характера ограничений.</small>
        <a href="#tariffs">Тарифы с обходом <ArcIcon name="arrow" size={18} /></a>
      </div>
      <dl><div><dt>Основной интернет</dt><dd>Безлимитно</dd></div><div><dt>Профили обхода</dt><dd>Отдельные гигабайты</dd></div><div><dt>После исчерпания</dt><dd>Обычные профили работают</dd></div><div><dt>Нужен ещё запас</dt><dd>Можно докупить</dd></div></dl>
    </section>

    <section class="pricing-section" id="tariffs" data-nav-section>
      <div class="intro pricing-intro">
        <h2>Тарифы без мелкого шрифта</h2>
        <p>Во всех тарифах основной трафик безлимитный. Стандарт и Семейный включают отдельный объём для профилей обхода глушилок.</p>
      </div>
      <div class="periods" role="group" aria-label="Срок подписки">
        {#each [1,3,6,12] as month}
          <button class:active={selectedPeriod === month} aria-pressed={selectedPeriod === month} on:click={() => selectedPeriod = month}>{month} {month === 1 ? 'месяц' : 'мес.'}</button>
        {/each}
      </div>
      {#if periodTariffs.length}
        <div class="tariff-grid">
          {#each ['economy','standard','family'] as code}
            {@const plan = periodTariffs.find((item) => item.product_code === code)}
            {#if plan}
              <article class:recommended={code === 'standard'}>
                <header><span>{productNames[code]}</span>{#if code === 'standard'}<em>Оптимальный</em>{/if}</header>
                <p>{productCopy[code]}</p>
                <div class="plan-price"><b>{plan.monthly_rub.toLocaleString('ru-RU')} ₽</b><span>в месяц</span></div>
                <small>{plan.price_rub.toLocaleString('ru-RU')} ₽ за {plan.period_months} {plan.period_months === 1 ? 'месяц' : 'месяца'}</small>
                <ul><li>Основной трафик безлимитный</li><li>{plan.device_limit} {plan.device_limit >= 2 && plan.device_limit <= 4 ? 'устройства' : 'устройств'}</li><li>{plan.lte_quota_gb ? `${plan.lte_quota_gb} ГБ обхода` : 'Без трафика обхода'}</li></ul>
                <button on:click={() => selectTariff(plan)}>Выбрать <ArcIcon name="arrow" size={17} /></button>
              </article>
            {/if}
          {/each}
        </div>
      {:else if dataError}
        <div class="pricing-error"><b>Тарифы временно не загрузились</b><span>Актуальные цены доступны в личном кабинете.</span><a href="/app">Открыть кабинет</a></div>
      {:else}
        <div class="loading"><span></span></div>
      {/if}

      <div class="custom-builder">
        <div class="custom-heading"><h3>Соберите свой тариф</h3><p>Срок, устройства и запас обхода. Цена пересчитывается сервером.</p></div>
        <div class="custom-controls">
          <label><span>Срок</span><div>{#each [1,3,6,12] as month}<button class:active={customMonths === month} on:click={() => customMonths = month}>{month}</button>{/each}</div></label>
          <label><span>Устройства <b>{customDevices}</b></span><input aria-label={`Устройства ${customDevices}`} type="range" min="1" max="15" bind:value={customDevices} /></label>
          <label><span>Обход</span><div>{#each [0,15,30,45,75,115] as gb}<button class:active={customLte === gb} on:click={() => customLte = gb}>{gb || '—'}</button>{/each}</div></label>
        </div>
        <div class="custom-total">
          <small class="custom-label">Ваша цена</small>
          <span>{customMonths} мес. · {customDevices} устр. · {customLte} ГБ обхода</span>
          <b>{quoteBusy ? '…' : customQuote ? `${customQuote.price_rub.toLocaleString('ru-RU')} ₽` : 'Цена недоступна'}</b>
          {#if customQuote?.monthly_rub}<small>{customQuote.monthly_rub.toLocaleString('ru-RU')} ₽ в месяц</small>{/if}
          <a href="/app?screen=custom-tariff" on:click={() => track('landing_custom_tariff_click')}>Создать тариф <ArcIcon name="arrow" size={17} /></a>
        </div>
      </div>
    </section>

    <section class="cabinet-section" id="cabinet" data-nav-section>
      <div class="intro split-intro">
        <h2>Подписка всегда<br />под рукой</h2>
        <p>Один кабинет для срока, трафика, устройств, продления, уведомлений и поддержки. Это реальные интерфейсы ArcVPN на компьютере и телефоне.</p>
      </div>
      <div class="cabinet-proof">
        <figure class="cabinet-desktop-shot">
          <figcaption>Кабинет на компьютере</figcaption>
          <img src={`${base}assets/landing/cabinet-desktop.webp`} alt="Главный экран личного кабинета ArcVPN на компьютере" width="1600" height="924" loading="lazy" decoding="async" />
        </figure>
        <figure class="cabinet-mobile-shot">
          <figcaption>На телефоне</figcaption>
          <img src={`${base}assets/landing/cabinet-mobile.webp`} alt="Главный экран личного кабинета ArcVPN на телефоне" width="568" height="912" loading="lazy" decoding="async" />
        </figure>
      </div>
      <a class="cabinet-link" href="/app" on:click={() => track('landing_cabinet_click', { place:'cabinet' })}>Открыть личный кабинет <ArcIcon name="arrow" size={18} /></a>
    </section>

    <section class="connection-section" id="steps">
      <div class="intro"><h2>Четыре действия до подключения</h2></div>
      <ol><li><span>1</span><b>Выберите тариф</b><p>Готовый вариант или свои параметры.</p></li><li><span>2</span><b>Получите ссылку</b><p>Она появится после активации.</p></li><li><span>3</span><b>Установите приложение</b><p>Подойдут Happ или INCY.</p></li><li><span>4</span><b>Импортируйте подписку</b><p>Выберите Автовыбор и подключитесь.</p></li></ol>
    </section>

    <section class="faq-section" id="faq" data-nav-section>
      <div class="intro"><h2>Вопросы перед подключением</h2></div>
      <div class="faq-list">
        {#each faqs as faq, index}
          <article><h3><button aria-expanded={openFaq === index} aria-controls={`answer-${index}`} on:click={() => { openFaq = openFaq === index ? -1 : index; track('landing_faq_open', { index }) }}><span>{faq[0]}</span><i>{openFaq === index ? '−' : '+'}</i></button></h3>{#if openFaq === index}<div id={`answer-${index}`}><p>{faq[1]}</p></div>{/if}</article>
        {/each}
      </div>
    </section>

    <section class="final-section">
      <img src={`${base}assets/landing/northern-flow.webp`} alt="" aria-hidden="true" />
      <div><h2>ArcVPN готов<br />к подключению</h2><p>Одна подписка. Ваши устройства. Управление через сайт и Telegram.</p><nav><a class="primary" href="/app">Личный кабинет <ArcIcon name="arrow" size={18} /></a><a class="quiet-link" href="#tariffs">Посмотреть тарифы</a></nav></div>
    </section>

    <section class="links-section">
      <h2>Оставайтесь на связи</h2>
      <nav>
        {#if config.bot_url}<a href={config.bot_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click', { channel:'bot' })}><b>Telegram-бот</b><span>Подключение и уведомления</span><ArcIcon name="arrow" size={18} /></a>{/if}
        {#if config.channel_url}<a href={config.channel_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click', { channel:'channel' })}><b>Telegram-канал</b><span>Новости ArcVPN</span><ArcIcon name="arrow" size={18} /></a>{/if}
        {#if config.instagram_url}<a href={config.instagram_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click', { channel:'instagram' })}><b>Instagram</b><span>ArcVPN в Instagram</span><ArcIcon name="arrow" size={18} /></a>{/if}
        {#if config.tiktok_url}<a href={config.tiktok_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click', { channel:'tiktok' })}><b>TikTok</b><span>ArcVPN в TikTok</span><ArcIcon name="arrow" size={18} /></a>{/if}
        <a href="/app"><b>Личный кабинет</b><span>Подписка и устройства</span><ArcIcon name="arrow" size={18} /></a>
      </nav>
    </section>
  </main>

  <footer class="footer">
    <a class="brand" href="#top"><img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" /><b>ArcVPN</b></a>
    <nav>{#if config.support_url}<a href={config.support_url}>Поддержка</a>{/if}<a href="/legal/user-agreement">Соглашение</a>{#if config.status_url}<a href={config.status_url}>Статус</a>{/if}<a href="/app">Кабинет</a></nav>
    <small>© {new Date().getFullYear()} ArcVPN</small>
  </footer>
</div>

<style>
  :global(.landing-document){scroll-padding-top:105px;background:#030508}
  :global(body:has(.landing)){min-width:320px;overflow-x:hidden;color:#f4f7fa;background:#030508;overscroll-behavior-y:auto}
  :global(body:has(.landing) #app){max-width:none;overflow:visible}
  .landing{--ink:#030508;--carbon:#0a0d12;--surface:#0e131a;--line:rgba(219,234,247,.12);--line-strong:rgba(219,234,247,.22);--snow:#f4f7fa;--steel:#8d98a7;--blue:#66bfff;--deep-blue:#06274a;width:100%;overflow:hidden;color:var(--snow);background:var(--ink);font-family:'Manrope',system-ui,sans-serif}
  .landing *{box-sizing:border-box}.landing a{color:inherit;text-decoration:none}.landing button{border:0;color:inherit;font:inherit;cursor:pointer}.landing h1,.landing h2,.landing h3,.landing p{margin-top:0}.landing :is(a,button,input):focus-visible{outline:2px solid #9edcff;outline-offset:4px}
  .skip{position:fixed;z-index:100;top:8px;left:8px;padding:12px 18px;border-radius:999px;color:#030508!important;background:#fff;transform:translateY(-150%)}.skip:focus{transform:none}
  .landing-nav{position:fixed;z-index:50;top:18px;left:50%;width:min(calc(100% - 40px),1120px);height:64px;display:flex;align-items:center;gap:28px;padding:7px 9px 7px 18px;border:1px solid rgba(255,255,255,.1);border-radius:999px;background:rgba(3,5,8,.72);box-shadow:0 20px 70px rgba(0,0,0,.3);transform:translateX(-50%);backdrop-filter:blur(22px);transition:transform .24s ease,background .24s ease}.landing-nav.compact{background:rgba(3,5,8,.92);transform:translateX(-50%) translateY(-8px)}
  .brand{display:flex;align-items:center;gap:9px;flex:none}.brand img{width:25px;height:25px}.brand b{font-size:16px;letter-spacing:-.03em}.desktop-nav{display:flex;justify-content:center;gap:24px;flex:1}.desktop-nav a{position:relative;padding:12px 0;color:#7e8894;font-size:11px;font-weight:700}.desktop-nav a:hover,.desktop-nav a.active{color:#fff}.desktop-nav a.active::after{content:'';position:absolute;right:0;bottom:6px;left:0;height:1px;background:var(--blue)}
  .nav-cta,.primary{min-height:48px;display:inline-flex;align-items:center;justify-content:center;gap:9px;padding:0 20px;border-radius:999px;color:#02070b!important;background:#f5f8fb;font-size:11px;font-weight:800;transition:transform .18s ease,background .18s ease}.nav-cta:hover,.primary:hover{background:#cceeff}.nav-cta:active,.primary:active{transform:scale(.98)}
  .hero{position:relative;min-height:max(760px,100svh);display:grid;place-items:center;isolation:isolate;padding:132px 24px 105px;border-bottom:1px solid var(--line)}.hero::before{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(ellipse 48% 38% at 50% 45%,rgba(3,5,8,.62),rgba(3,5,8,.24) 62%,transparent 100%),linear-gradient(180deg,rgba(3,5,8,.24),transparent 24%,transparent 62%,#030508 98%)}.hero-current{position:absolute;z-index:-2;inset:0;width:100%;height:100%;object-fit:cover;object-position:center;background:#020305}.hero-copy{width:min(100%,930px);text-align:center;transform:translateY(-1.5vh)}.hero h1{margin:0;font-size:clamp(54px,6.25vw,94px);font-weight:700;line-height:.97;letter-spacing:-.066em;text-shadow:0 3px 28px rgba(0,0,0,.68)}.hero h1 span{display:inline-block;color:#e3eaf0}.hero-text{max-width:610px;margin:26px auto 0;color:#a7b1bc;font-size:14px;line-height:1.65;text-wrap:balance}.hero-actions{display:flex;align-items:center;justify-content:center;gap:25px;margin-top:30px}.quiet-link{display:inline-flex;align-items:center;min-height:44px;color:#d1d8df!important;font-size:11px;font-weight:750;border-bottom:1px solid rgba(255,255,255,.28)}.platform-line{position:absolute;right:24px;bottom:27px;left:24px;display:flex;justify-content:center;gap:34px;color:#697480;font-size:9px;font-weight:700}
  .trial-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{width:min(calc(100% - 48px),1180px);margin:0 auto;padding:132px 0}
  .intro h2,.trial-intro h2{margin:0;font-size:clamp(42px,5.4vw,76px);font-weight:650;line-height:.98;letter-spacing:-.065em;text-wrap:balance}.intro>p,.trial-intro>p{max-width:540px;margin:0;color:var(--steel);font-size:14px;line-height:1.75}.split-intro,.trial-intro{display:grid;grid-template-columns:1fr .72fr;align-items:end;gap:80px;margin-bottom:65px}
  .trial-section{padding-top:118px}.trial-panel{position:relative;display:grid;grid-template-columns:1fr 1fr;overflow:hidden;border:1px solid var(--line-strong);border-radius:34px;background:linear-gradient(125deg,#0d1722,#080d14 55%,#07111b);box-shadow:0 55px 130px -80px rgba(91,184,241,.52)}.trial-panel::before{content:'';position:absolute;top:-180px;left:12%;width:440px;height:340px;border-radius:50%;background:rgba(70,171,231,.15);filter:blur(90px);pointer-events:none}.trial-panel article{position:relative;min-height:340px;display:flex;align-items:flex-start;flex-direction:column;padding:42px 44px}.trial-panel article+article{border-left:1px solid var(--line)}.trial-panel span{color:#90a1b0;font-size:10px;font-weight:750}.trial-panel strong{margin-top:18px;font-size:clamp(40px,4.4vw,58px);line-height:1;letter-spacing:-.06em}.trial-panel p{max-width:430px;margin:20px 0 30px;color:#8e9aa6;font-size:12px;line-height:1.65}.trial-panel a{min-height:48px;display:inline-flex;align-items:center;justify-content:center;gap:9px;margin-top:auto;padding:0 20px;border:1px solid var(--line-strong);border-radius:999px;font-size:10px;font-weight:850;transition:transform .18s ease,border-color .18s ease,background .18s ease}.trial-panel a:hover{border-color:#81c9f2;background:rgba(104,194,244,.08)}.trial-panel a:active{transform:scale(.98)}.trial-free a{border-color:#bee9ff;color:#05101a!important;background:#bde8ff}.trial-free a:hover{color:#04101a!important;background:#e1f5ff}
  .loading,.pricing-error{min-height:260px;display:grid;place-content:center;place-items:center;gap:10px;text-align:center}.loading span{width:26px;height:26px;border:2px solid #23313e;border-top-color:#82cef4;border-radius:50%;animation:spin .8s linear infinite}.pricing-error span{color:var(--steel);font-size:11px}.pricing-error a{color:#9ddcff;font-size:11px;font-weight:800}
  .apps-section{padding-top:40px}.apps-proof{min-height:680px;display:grid;grid-template-columns:1.05fr .95fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.phone-well{position:relative;display:grid;place-items:end center;overflow:hidden;background:radial-gradient(circle at 50% 70%,rgba(29,113,172,.22),transparent 55%)}.phone-well>img{width:min(78%,390px);height:585px;object-fit:contain;object-position:bottom}.app-switch{position:absolute;z-index:2;top:28px;display:flex;gap:3px;padding:4px;border:1px solid var(--line);border-radius:999px;background:#070a0e}.app-switch button{min-width:84px;min-height:38px;border-radius:999px;background:transparent;color:#7e8994;font-size:10px;font-weight:800}.app-switch button.active{color:#05090c;background:#eef6fb}.app-copy{display:flex;justify-content:center;flex-direction:column;padding:60px 70px;border-left:1px solid var(--line)}.app-copy h2{margin:0;font-size:clamp(38px,4.2vw,62px);line-height:.98;letter-spacing:-.06em}.app-copy>p{max-width:460px;margin:25px 0 0;color:var(--steel);font-size:13px;line-height:1.7}.device-tabs{display:grid;grid-template-columns:1fr 1fr;margin-top:36px;border-top:1px solid var(--line)}.device-tabs button{min-height:67px;display:flex;align-items:center;gap:11px;padding:0 5px;border-bottom:1px solid var(--line);background:transparent;color:#798490;font-size:10px;text-align:left}.device-tabs button:nth-child(odd){border-right:1px solid var(--line)}.device-tabs button.active{color:#dff4ff}.app-actions{display:flex;align-items:center;gap:24px;margin-top:34px}.feature-ledger{display:grid;grid-template-columns:1fr 1fr;margin-top:100px;border-top:1px solid var(--line)}.feature-ledger article{min-height:185px;padding:35px 38px;border-bottom:1px solid var(--line)}.feature-ledger article:nth-child(odd){border-right:1px solid var(--line)}.feature-ledger h3{margin:0;font-size:19px;letter-spacing:-.03em}.feature-ledger p{max-width:430px;margin:15px 0 0;color:var(--steel);font-size:12px;line-height:1.65}
  .bypass-section{width:min(calc(100% - 48px),1180px);min-height:470px;display:grid;grid-template-columns:1.08fr .72fr;align-items:center;gap:90px;margin:0 auto;padding:72px;border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);background:linear-gradient(105deg,rgba(6,39,74,.62),rgba(5,9,14,.2) 58%,rgba(2,7,12,.44))}.bypass-section h2{margin:0;font-size:clamp(38px,4.45vw,62px);line-height:1;letter-spacing:-.06em}.bypass-section p{max-width:650px;margin:20px 0 0;color:#a4afba;font-size:13px;line-height:1.72}.bypass-section small{display:block;max-width:560px;margin-top:16px;color:#6f7d89;font-size:9px;line-height:1.6}.bypass-section a{display:inline-flex;align-items:center;gap:8px;margin-top:25px;color:#a6e0ff;font-size:11px;font-weight:800}.bypass-section dl{margin:0;border-top:1px solid var(--line)}.bypass-section dl div{display:flex;justify-content:space-between;gap:20px;padding:18px 0;border-bottom:1px solid var(--line)}.bypass-section dt{color:#88939f;font-size:11px}.bypass-section dd{margin:0;color:#dceaf2;font-size:11px;font-weight:800;text-align:right}
  .pricing-section{padding-bottom:105px}.pricing-intro{display:flex;align-items:end;justify-content:space-between;gap:80px}.pricing-intro h2{max-width:750px}.pricing-intro p{max-width:380px}.periods{width:max-content;display:flex;gap:4px;margin:48px auto 45px;padding:5px;border:1px solid var(--line);border-radius:999px;background:#070b10}.periods button{min-width:84px;min-height:40px;border-radius:999px;background:transparent;color:#77818c;font-size:9px;font-weight:800;transition:color .18s ease,background .18s ease}.periods button:hover{color:#dce9f2}.periods button.active{color:#03070b;background:#eef6fb}.tariff-grid{display:grid;grid-template-columns:repeat(3,1fr);align-items:stretch;gap:12px}.tariff-grid article{position:relative;min-height:500px;display:flex;flex-direction:column;padding:34px 32px;border:1px solid var(--line);border-radius:30px;background:linear-gradient(160deg,#0b1017,#06090d 72%);box-shadow:0 30px 90px -70px #000;transition:transform .2s ease,border-color .2s ease}.tariff-grid article:hover{border-color:rgba(160,211,242,.3);transform:translateY(-3px)}.tariff-grid article.recommended{border-color:rgba(113,202,251,.52);background:linear-gradient(155deg,#101d29,#081019 68%);box-shadow:0 38px 100px -58px rgba(72,171,230,.52);transform:translateY(-10px)}.tariff-grid article.recommended:hover{transform:translateY(-13px)}.tariff-grid header{display:flex;align-items:center;justify-content:space-between;gap:20px}.tariff-grid header span{font-size:19px;font-weight:800}.tariff-grid header em{padding:6px 10px;border:1px solid #315d7b;border-radius:999px;color:#9bdcff;font-size:8px;font-style:normal}.tariff-grid article>p{min-height:42px;margin:17px 0 33px;color:#84909c;font-size:11px;line-height:1.55}.plan-price{display:flex;align-items:baseline;gap:9px}.plan-price b{font-size:48px;line-height:1;letter-spacing:-.06em}.plan-price span,.tariff-grid article>small{color:#77838f;font-size:9px}.tariff-grid ul{display:grid;gap:15px;margin:31px 0;padding:27px 0 0;border-top:1px solid var(--line);list-style:none}.tariff-grid li{display:flex;gap:10px;color:#b6c2cc;font-size:11px}.tariff-grid li::before{content:'✓';color:#76c9f5;font-size:10px}.tariff-grid article>button{min-height:50px;display:flex;align-items:center;justify-content:center;gap:8px;margin-top:auto;border:1px solid var(--line-strong);border-radius:999px;background:rgba(255,255,255,.01);font-size:10px;font-weight:850;transition:transform .18s ease,background .18s ease}.tariff-grid article>button:hover{background:rgba(117,199,243,.09)}.tariff-grid article>button:active{transform:scale(.98)}.tariff-grid article.recommended>button{border-color:#dbeef8;color:#03080b;background:#eff7fb}.custom-builder{display:grid;grid-template-columns:.72fr 1.2fr .72fr;gap:38px;margin-top:72px;padding:38px;border:1px solid var(--line-strong);border-radius:34px;background:linear-gradient(140deg,#0b1119,#060a0f 65%);box-shadow:0 40px 100px -80px rgba(82,176,232,.45)}.custom-heading h3{margin:0;font-size:29px;line-height:1.05;letter-spacing:-.045em}.custom-heading p{max-width:260px;margin:14px 0 0;color:#818d99;font-size:10px;line-height:1.65}.custom-controls{display:grid;gap:19px}.custom-controls label{display:grid;grid-template-columns:92px 1fr;align-items:center;gap:17px}.custom-controls label>span{color:#909aa5;font-size:9px}.custom-controls label>span b{float:right;color:#e4edf4}.custom-controls label>div{display:flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:16px;background:#070b10}.custom-controls button{min-width:42px;min-height:36px;border-radius:12px;background:transparent;color:#73808c;font-size:9px}.custom-controls button:hover{color:#d8e8f2}.custom-controls button.active{color:#06101a;background:#a9defa}.custom-controls input{width:100%;accent-color:#75c7f2}.custom-total{min-height:190px;display:flex;align-items:flex-start;flex-direction:column;padding:25px;border:1px solid rgba(114,198,244,.2);border-radius:24px;background:linear-gradient(145deg,rgba(83,174,226,.18),rgba(11,25,38,.55))}.custom-total .custom-label{color:#9fcfe9;font-size:8px;font-weight:850}.custom-total>span{margin-top:10px;color:#91a0ad;font-size:8px;line-height:1.5}.custom-total>b{margin-top:16px;font-size:39px;line-height:1;letter-spacing:-.055em}.custom-total>small:not(.custom-label){margin-top:6px;color:#8b9aa6;font-size:8px}.custom-total>a{min-height:42px;display:flex;align-items:center;gap:7px;margin-top:auto;color:#c5ebff;font-size:10px;font-weight:850}
  .cabinet-section{padding-top:105px}.cabinet-proof{position:relative;min-height:720px;margin-top:8px;padding:38px 90px 78px 0;background:radial-gradient(ellipse 48% 42% at 58% 58%,rgba(32,112,169,.2),transparent 72%)}.cabinet-proof figure{position:relative;margin:0;overflow:hidden;border:1px solid rgba(182,221,246,.18);background:#05090e;box-shadow:0 45px 120px -62px rgba(53,147,208,.48)}.cabinet-proof figcaption{position:absolute;z-index:2;top:17px;left:18px;padding:8px 11px;border:1px solid rgba(255,255,255,.1);border-radius:999px;color:#c9dae5;background:rgba(3,7,12,.72);font-size:8px;font-weight:800;backdrop-filter:blur(12px)}.cabinet-proof img{width:100%;height:auto;display:block}.cabinet-desktop-shot{width:min(100%,1050px);border-radius:30px}.cabinet-mobile-shot{position:absolute!important;right:0;bottom:18px;width:240px;padding:6px;border-radius:38px!important;transform:rotate(1.5deg)}.cabinet-mobile-shot img{border-radius:31px}.cabinet-mobile-shot figcaption{top:14px;left:14px}.cabinet-link{width:max-content;display:flex;align-items:center;gap:8px;margin:4px auto 0;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.28);font-size:11px;font-weight:800}
  .connection-section{padding-bottom:100px}.connection-section .intro{max-width:760px}.connection-section ol{display:grid;grid-template-columns:repeat(4,1fr);margin:58px 0 0;padding:0;border-top:1px solid var(--line);list-style:none}.connection-section li{padding:30px 26px 0 0}.connection-section li+li{padding-left:26px;border-left:1px solid var(--line)}.connection-section li>span{color:#6fc7f5;font-size:10px}.connection-section li>b{display:block;margin-top:22px;font-size:14px}.connection-section li>p{margin:10px 0 0;color:#7e8994;font-size:10px;line-height:1.55}
  .faq-section{display:grid;grid-template-columns:.7fr 1.3fr;gap:90px}.faq-list{border-top:1px solid var(--line)}.faq-list article{border-bottom:1px solid var(--line)}.faq-list h3{margin:0}.faq-list button{width:100%;min-height:82px;display:flex;align-items:center;justify-content:space-between;gap:25px;padding:0;background:transparent;text-align:left}.faq-list button span{font-size:13px}.faq-list button i{color:#79c8f0;font-size:20px;font-style:normal;font-weight:400}.faq-list article>div{padding:0 45px 25px 0}.faq-list p{max-width:650px;margin:0;color:#8a95a0;font-size:11px;line-height:1.75}
  .final-section{position:relative;width:min(calc(100% - 48px),1180px);min-height:560px;display:grid;place-items:center;isolation:isolate;overflow:hidden;margin:20px auto 120px;border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);text-align:center}.final-section::after{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(circle at 50% 45%,rgba(3,5,8,.15),rgba(3,5,8,.88) 73%)}.final-section>img{position:absolute;z-index:-2;inset:0;width:100%;height:100%;object-fit:cover}.final-section>div{padding:60px 24px}.final-section h2{margin:0;font-size:clamp(50px,6.5vw,88px);line-height:.9;letter-spacing:-.07em}.final-section p{margin:28px auto 0;color:#96a2ad;font-size:12px}.final-section nav{display:flex;align-items:center;justify-content:center;gap:26px;margin-top:31px}
  .links-section{display:grid;grid-template-columns:.75fr 1.25fr;gap:90px;padding-top:20px}.links-section h2{margin:0;font-size:clamp(35px,4.5vw,58px);line-height:1;letter-spacing:-.055em}.links-section nav{border-top:1px solid var(--line)}.links-section nav a{min-height:76px;display:grid;grid-template-columns:1fr 1.2fr auto;align-items:center;gap:20px;border-bottom:1px solid var(--line)}.links-section nav b{font-size:12px}.links-section nav span{color:#77838e;font-size:9px}.links-section nav a:hover :global(.arc-icon){transform:translateX(3px)}
  .footer{width:min(calc(100% - 48px),1180px);min-height:120px;display:flex;align-items:center;gap:40px;margin:0 auto;border-top:1px solid var(--line)}.footer nav{display:flex;gap:25px;margin-left:auto}.footer nav a,.footer small{color:#75808a;font-size:9px}.footer small{margin-left:25px}
  @keyframes spin{to{transform:rotate(360deg)}}
  @media(max-width:900px){.landing-nav{top:12px;width:calc(100% - 24px);height:60px}.landing-nav.compact{transform:translateX(-50%) translateY(-4px)}.desktop-nav{display:none}.nav-cta{margin-left:auto}.hero{min-height:850px;padding-top:125px}.hero h1{font-size:clamp(54px,9vw,76px)}.trial-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{width:min(calc(100% - 32px),720px);padding:105px 0}.trial-intro,.split-intro,.faq-section,.links-section{grid-template-columns:1fr;gap:35px}.trial-intro,.split-intro{margin-bottom:50px}.trial-panel article{padding:36px 34px}.apps-proof{grid-template-columns:1fr;min-height:0}.phone-well{min-height:590px}.app-copy{padding:55px 45px;border-top:1px solid var(--line);border-left:0}.feature-ledger{margin-top:70px}.bypass-section{width:min(calc(100% - 32px),720px);grid-template-columns:1fr;gap:45px;padding:60px 44px}.pricing-intro{align-items:flex-start;flex-direction:column;gap:25px}.tariff-grid{grid-template-columns:1fr;gap:14px}.tariff-grid article,.tariff-grid article.recommended,.tariff-grid article.recommended:hover{min-height:430px;transform:none}.custom-builder{grid-template-columns:1fr;gap:32px}.custom-heading p{max-width:440px}.custom-total{min-height:180px}.cabinet-proof{min-height:570px;padding:30px 65px 70px 0}.cabinet-mobile-shot{width:185px}.connection-section ol{grid-template-columns:1fr 1fr;row-gap:35px}.connection-section li:nth-child(3){padding-left:0;border-left:0}.links-section{padding-top:30px}.footer{width:calc(100% - 32px);flex-wrap:wrap;padding:35px 0}.footer nav{order:3;width:100%;margin-left:0}.footer small{margin-left:auto}}
  @media(max-width:560px){.landing-nav{gap:12px;padding:7px 8px 7px 18px}.landing-nav .brand{gap:7px}.landing-nav .brand img{width:23px;height:23px}.landing-nav .brand b{display:block;font-size:13px}.nav-cta{min-height:42px;padding:0 13px;font-size:8.5px}.nav-cta :global(.arc-icon){width:14px;height:14px}.hero{min-height:800px;place-items:center;padding:125px 17px 92px}.hero::before{background:radial-gradient(ellipse 85% 43% at 50% 44%,rgba(3,5,8,.16),rgba(3,5,8,.62) 78%),linear-gradient(180deg,rgba(3,5,8,.3),transparent 26%,rgba(3,5,8,.16) 58%,#030508 96%)}.hero-current{object-position:66% center}.hero-copy{text-align:left;transform:translateY(-2vh)}.hero h1{font-size:clamp(42px,12.2vw,48px);line-height:1;letter-spacing:-.058em}.hero-text{max-width:350px;margin:23px 0 0;font-size:11.5px;line-height:1.62;text-wrap:pretty}.hero-actions{align-items:flex-start;justify-content:flex-start;flex-direction:column;gap:13px;margin-top:27px}.platform-line{right:17px;bottom:19px;left:17px;justify-content:space-between;gap:4px;font-size:6px}.trial-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{padding:78px 0}.intro h2,.trial-intro h2{font-size:42px}.intro>p,.trial-intro>p{font-size:12px}.trial-intro{gap:24px;margin-bottom:38px}.trial-panel{grid-template-columns:1fr;border-radius:26px}.trial-panel article{min-height:0;padding:30px 24px}.trial-panel article+article{border-top:1px solid var(--line);border-left:0}.trial-panel strong{font-size:44px}.trial-panel p{font-size:11.5px}.apps-section{padding-top:20px}.phone-well{min-height:505px}.phone-well>img{height:460px}.app-copy{padding:45px 18px}.app-copy h2{font-size:42px}.device-tabs{grid-template-columns:1fr}.device-tabs button:nth-child(odd){border-right:0}.app-actions{align-items:flex-start;flex-direction:column;gap:14px}.feature-ledger{grid-template-columns:1fr}.feature-ledger article{min-height:145px;padding:28px 5px}.feature-ledger article:nth-child(odd){border-right:0}.bypass-section{min-height:0;padding:48px 24px}.bypass-section h2{font-size:40px}.bypass-section p{font-size:11.5px}.periods{width:100%;overflow-x:auto;scrollbar-width:none}.periods::-webkit-scrollbar{display:none}.periods button{min-width:70px}.tariff-grid article,.tariff-grid article.recommended{min-height:425px;padding:28px 22px;border-radius:25px}.plan-price b{font-size:44px}.custom-builder{gap:28px;padding:24px;border-radius:27px}.custom-controls label{grid-template-columns:1fr;gap:10px}.custom-controls label>div{overflow-x:auto;scrollbar-width:none}.custom-controls label>div::-webkit-scrollbar{display:none}.custom-total{min-height:185px;padding:22px}.custom-total>b{font-size:40px}.cabinet-section .split-intro{margin-bottom:28px}.cabinet-proof{min-height:0;display:grid;gap:0;margin:0;padding:0;background:none}.cabinet-desktop-shot{width:100%;border-radius:19px}.cabinet-proof figcaption{top:11px;left:11px;padding:6px 8px;font-size:7px}.cabinet-mobile-shot{position:relative!important;right:auto;bottom:auto;width:min(72%,260px);justify-self:end;margin-top:-28px;padding:5px;border-radius:31px!important;transform:none}.cabinet-mobile-shot img{border-radius:25px}.cabinet-link{margin-top:28px}.connection-section ol{grid-template-columns:1fr;gap:0}.connection-section li,.connection-section li+li,.connection-section li:nth-child(3){padding:23px 0;border-top:1px solid var(--line);border-left:0}.connection-section li>b{margin-top:10px}.faq-list button{min-height:75px}.faq-list button span{font-size:12px}.final-section{width:calc(100% - 32px);min-height:500px;margin-bottom:80px}.final-section>div{padding:45px 18px}.final-section h2{font-size:52px}.final-section nav{align-items:center;flex-direction:column;gap:13px}.links-section nav a{grid-template-columns:1fr auto}.links-section nav a span{display:none}.footer{gap:20px}.footer nav{gap:18px;flex-wrap:wrap}}
  @media(prefers-reduced-motion:reduce){.landing *{transition:none!important}.loading span{animation:none}}
</style>
