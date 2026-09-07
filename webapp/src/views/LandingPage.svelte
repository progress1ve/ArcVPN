<script>
  import { onMount, tick } from 'svelte'
  import ArcIcon from '../components/ArcIcon.svelte'
  import DeviceIcon from '../components/DeviceIcon.svelte'

  const base = import.meta.env.BASE_URL
  const productNames = { economy: 'Эконом', standard: 'Стандарт', family: 'Семейный' }
  const productCopy = {
    economy: 'Для одного-двух личных устройств',
    standard: 'Оптимальный запас для повседневных сетей',
    family: 'Для семьи и большого числа устройств',
  }
  const profileCopy = {
    auto: 'Подбирает подходящее подключение автоматически',
    location: 'Обычная локация для повседневного интернета',
    service: 'Отдельный профиль для конкретного сервиса',
    bypass: 'Использует запас трафика для сложных сетей',
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
    ['Профили для сервисов', 'Отдельные варианты для задач, которым нужен свой маршрут.'],
    ['Одна ссылка', 'Каталог обновляется после обычного обновления подписки в приложении.'],
  ]
  const faqs = [
    ['Как установить и подключить ArcVPN?', 'Откройте личный кабинет, выберите устройство и установите Happ или INCY. Затем импортируйте ссылку подписки и выберите Автовыбор.'],
    ['Что такое трафик обхода глушилок?', 'Это отдельный запас для специальных профилей, которые помогают в сложных сетях. Основной трафик остаётся безлимитным и учитывается отдельно.'],
    ['На скольких устройствах работает подписка?', 'Количество зависит от тарифа. Доступные слоты видны в тарифе и личном кабинете; дополнительные устройства можно докупить.'],
    ['Что делать, если VPN не подключается?', 'Обновите подписку в приложении, включите Автовыбор и повторите подключение. Если не помогло, напишите в поддержку и приложите модель устройства и скриншот ошибки.'],
  ]
  const fallbackProfiles = import.meta.env.DEV ? [
    { display_name: 'Автовыбор | Самый быстрый', kind: 'auto' },
    { display_name: 'Ютуб без рекламы', kind: 'service' },
    { display_name: 'Эстония', kind: 'location' },
    { display_name: 'Нидерланды', kind: 'location' },
    { display_name: 'Албания', kind: 'location' },
    { display_name: 'Лучший обход', kind: 'bypass' },
  ] : []
  const fallbackTariffs = import.meta.env.DEV ? [
    ['economy',1,95,2,0],['standard',1,145,3,45],['family',1,329,8,115],
    ['economy',3,259,2,0],['standard',3,399,3,45],['family',3,899,8,115],
    ['economy',6,479,2,0],['standard',6,759,3,45],['family',6,1699,8,115],
    ['economy',12,929,2,0],['standard',12,1469,3,45],['family',12,3389,8,115],
  ].map((p, i) => ({ id:i+1, product_code:p[0], period_months:p[1], price_rub:p[2], monthly_rub:Math.round(p[2]/p[1]), device_limit:p[3], lte_quota_gb:p[4] })) : []

  let scrolled = false
  let menuOpen = false
  let activeSection = 'subscription'
  let profiles = []
  let tariffs = []
  let config = {}
  let dataError = false
  let selectedProfile = 0
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
  let mobileMenu
  let navRoot
  let previousFocus

  $: currentProfile = profiles[selectedProfile] || null
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
  function closeMenu() {
    menuOpen = false
    previousFocus?.focus?.()
  }
  async function toggleMenu(event) {
    previousFocus = event.currentTarget
    menuOpen = !menuOpen
    if (menuOpen) {
      await tick()
      mobileMenu?.querySelector('a')?.focus()
    }
  }
  function menuKeydown(event) {
    if (!menuOpen) return
    if (event.key === 'Escape') closeMenu()
    if (event.key !== 'Tab') return
    const focusable = [...mobileMenu.querySelectorAll('a,button')]
    const first = focusable[0]
    const last = focusable.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
  function windowClick(event) {
    if (menuOpen && navRoot && !navRoot.contains(event.target)) closeMenu()
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
      const [tariffResponse, catalogResponse, configResponse] = await Promise.all([
        fetch('/api/public/tariffs'), fetch('/api/public/subscription-catalog'), fetch('/api/public/config'),
      ])
      if (!tariffResponse.ok || !catalogResponse.ok || !configResponse.ok) throw new Error('public data')
      tariffs = (await tariffResponse.json()).tariffs || []
      profiles = (await catalogResponse.json()).profiles || []
      config = await configResponse.json()
    } catch (_) {
      tariffs = fallbackTariffs
      profiles = fallbackProfiles
      dataError = !import.meta.env.DEV
    }
  }
  function chooseProfile(index) {
    selectedProfile = index
  }
  function profileInitial(name) {
    const text = String(name || '').replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u, '').trim()
    return text.slice(0, 1) || '•'
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

<svelte:window on:keydown={menuKeydown} on:click={windowClick} />

<svelte:head>
  <meta name="theme-color" content="#030508" />
  <meta property="og:title" content="ArcVPN — одна подписка для свободного интернета" />
  <meta property="og:description" content="Подключение через Happ и INCY, актуальные тарифы и управление устройствами в личном кабинете." />
</svelte:head>

<div class="landing">
  <div class="guide guide-left" aria-hidden="true"></div>
  <div class="guide guide-right" aria-hidden="true"></div>
  <a class="skip" href="#main">К содержанию</a>

  <header class:compact={scrolled} class="landing-nav" bind:this={navRoot}>
    <a class="brand" href="#top" aria-label="ArcVPN — наверх">
      <img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" />
      <b>ArcVPN</b>
    </a>
    <nav class="desktop-nav" aria-label="Основная навигация">
      {#each [['subscription','Подписка'],['apps','Приложения'],['tariffs','Тарифы'],['cabinet','Кабинет'],['faq','Вопросы']] as item}
        <a class:active={activeSection === item[0]} href={`#${item[0]}`}>{item[1]}</a>
      {/each}
    </nav>
    <a class="nav-cta" href="/app" on:click={() => track('landing_cabinet_click', { place:'nav' })}>Личный кабинет <ArcIcon name="arrow" size={17} /></a>
    <button class="menu-button" aria-label="Открыть меню" aria-expanded={menuOpen} on:click={toggleMenu}><span></span><span></span></button>
    {#if menuOpen}
      <nav class="mobile-nav" bind:this={mobileMenu} aria-label="Мобильная навигация">
        {#each [['subscription','Подписка'],['apps','Приложения'],['tariffs','Тарифы'],['cabinet','Кабинет'],['faq','Вопросы']] as item}
          <a href={`#${item[0]}`} on:click={closeMenu}>{item[1]} <ArcIcon name="arrow" size={17} /></a>
        {/each}
      </nav>
    {/if}
  </header>

  <main id="main">
    <section class="hero" id="top">
      <img class="hero-current" src={`${base}assets/landing/northern-flow.webp`} alt="" aria-hidden="true" />
      <div class="hero-copy">
        <p class="hero-note">Подписка для Happ и INCY</p>
        <h1>Одна подписка.<br /><span>Свободный интернет.</span></h1>
        <p class="hero-text">Добавьте ArcVPN один раз и выбирайте Автовыбор, обычные локации или специальные профили для сложных сетей.</p>
        <div class="hero-actions">
          <a class="primary" href="/app" on:click={() => track('landing_cabinet_click', { place:'hero' })}>Открыть личный кабинет <ArcIcon name="arrow" size={18} /></a>
          <a class="quiet-link" href="#subscription">Посмотреть подписку</a>
        </div>
      </div>
      <div class="platform-line"><span>iPhone / iPad</span><span>Android</span><span>Windows</span><span>Linux</span></div>
    </section>

    <section class="client-section" id="subscription" data-nav-section>
      <div class="intro split-intro">
        <h2>Всё нужное уже<br />внутри подписки</h2>
        <p>Ссылка добавляется один раз. ArcVPN обновляет список профилей, а приложение показывает их привычным списком — без настройки серверов вручную.</p>
      </div>

      <div class="client-window" aria-label="Предпросмотр подписки ArcVPN">
        <div class="window-titlebar">
          <div class="traffic"><i></i><i></i><i></i></div>
          <span>ArcVPN — подписка в приложении</span>
          <em>Предпросмотр</em>
        </div>
        <div class="client-body">
          <aside aria-hidden="true">
            <img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" />
            <i class="active"><ArcIcon name="signal" size={20} /></i>
            <i><ArcIcon name="settings" size={20} /></i>
            <i><ArcIcon name="question" size={20} /></i>
          </aside>
          <div class="client-content">
            <div class="subscription-head">
              <span><small>Текущая подписка</small><b>ArcVPN</b></span>
              <div class="subscription-meta"><b>Обновляется автоматически</b><small>Одна ссылка для всех профилей</small></div>
            </div>
            {#if profiles.length}
              <div class="server-list">
                {#each profiles.slice(0, 7) as profile, index}
                  <button class:selected={selectedProfile === index} on:click={() => chooseProfile(index)}>
                    <i class:service={profile.kind === 'service'} class:bypass={profile.kind === 'bypass'}>
                      {#if profile.kind === 'location'}<span>{profileInitial(profile.display_name)}</span>{:else}<ArcIcon name={profile.kind === 'bypass' ? 'signal' : 'pulse'} size={18} />{/if}
                    </i>
                    <span><b>{profile.display_name}</b><small>{profileCopy[profile.kind] || profileCopy.location}</small></span>
                    <em><u></u>{selectedProfile === index ? 'Выбрано' : 'Доступно'}</em>
                  </button>
                {/each}
              </div>
              <div class="selection-note"><span>Сейчас выбран</span><b>{currentProfile?.display_name}</b><small>Это демонстрация интерфейса — подключение выполняется в Happ или INCY.</small></div>
            {:else if dataError}
              <div class="data-error"><b>Список подключений временно не загрузился</b><span>Актуальная подписка доступна в личном кабинете.</span><a href="/app">Открыть кабинет</a></div>
            {:else}
              <div class="loading" aria-label="Загружаем список"><span></span></div>
            {/if}
          </div>
        </div>
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
          <p>Выберите приложение и платформу. В кабинете получите точную инструкцию и ссылку импорта.</p>
          <div class="device-tabs" role="group" aria-label="Платформа">
            {#each devices as device}
              <button class:active={selectedDevice === device.id} on:click={() => selectedDevice = device.id}>
                <DeviceIcon name={device.icon} size={20} /><span>{device.label}</span>
              </button>
            {/each}
          </div>
          <div class="app-actions">
            <a class="primary" href={selectedStore} target="_blank" rel="noopener" on:click={() => track('landing_app_install_click', { app:selectedApp, platform:selectedDevice })}>Установить {appCatalog[selectedApp].label} <ArcIcon name="arrow" size={18} /></a>
            <a class="quiet-link" href="/app?screen=connect">Инструкция подключения</a>
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
        <h2>Запас для сложных сетей</h2>
        <p>Основной трафик остаётся безлимитным. Отдельный объём расходуют только специальные профили обхода. Когда запас закончится, обычные подключения продолжат работать.</p>
        <a href="#tariffs">Тарифы с обходом <ArcIcon name="arrow" size={18} /></a>
      </div>
      <dl><div><dt>Обычные профили</dt><dd>Безлимитно</dd></div><div><dt>Обход</dt><dd>Отдельный запас</dd></div><div><dt>После исчерпания</dt><dd>Основные профили работают</dd></div></dl>
    </section>

    <section class="pricing-section" id="tariffs" data-nav-section>
      <div class="intro pricing-intro">
        <h2>Тарифы без мелкого шрифта</h2>
        <p>Цена, устройства и объём обхода приходят из действующего каталога ArcVPN.</p>
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
          <span>{customMonths} мес. · {customDevices} устр. · {customLte} ГБ обхода</span>
          <b>{quoteBusy ? '…' : customQuote ? `${customQuote.price_rub.toLocaleString('ru-RU')} ₽` : 'Цена недоступна'}</b>
          {#if customQuote?.monthly_rub}<small>{customQuote.monthly_rub.toLocaleString('ru-RU')} ₽ в месяц{customQuote.preview ? ' · preview' : ''}</small>{/if}
          <a href="/app?screen=custom-tariff" on:click={() => track('landing_custom_tariff_click')}>Создать тариф <ArcIcon name="arrow" size={17} /></a>
        </div>
      </div>
    </section>

    <section class="cabinet-section" id="cabinet" data-nav-section>
      <div class="intro split-intro">
        <h2>Подписка всегда<br />под рукой</h2>
        <p>Один кабинет для срока, трафика, устройств, продления, уведомлений и поддержки. Ниже — подготовленные места под реальные обезличенные скриншоты.</p>
      </div>
      <div class="device-stage">
        <div class="laptop">
          <div class="laptop-top"><i></i><span>arccnet.space/app</span><em>Скриншот будет здесь</em></div>
          <div class="laptop-screen">
            <nav><img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" /><b>ArcVPN</b><span>Главная</span><span>Устройства</span><span>Поддержка</span></nav>
            <div class="desktop-cabinet"><small>Ваша подписка</small><h3>Остался 41 день</h3><p>Основной трафик безлимитный</p><div><span><b>2 из 3</b><small>устройства</small></span><span><b>32 ГБ</b><small>обхода осталось</small></span></div><button>Продлить подписку</button></div>
          </div>
          <div class="laptop-base"></div>
        </div>
        <div class="phone">
          <div class="phone-island"></div>
          <div class="phone-screen"><img src={`${base}assets/arc-flow/arc-logo.svg`} alt="" /><small>ArcVPN</small><h3>41</h3><p>день подписки</p><div><span>2 / 3 устройства</span><span>32 ГБ обхода</span></div><button>Подключить VPN</button><em>Место под mobile screenshot</em></div>
        </div>
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
  :global(.landing-document){scroll-behavior:smooth;scroll-padding-top:105px;background:#030508}
  :global(body:has(.landing)){min-width:320px;overflow-x:hidden;color:#f4f7fa;background:#030508;overscroll-behavior-y:auto}
  :global(body:has(.landing) #app){max-width:none;overflow:visible}
  .landing{--ink:#030508;--carbon:#0a0d12;--surface:#0e131a;--line:rgba(219,234,247,.12);--line-strong:rgba(219,234,247,.22);--snow:#f4f7fa;--steel:#8d98a7;--blue:#66bfff;--deep-blue:#06274a;width:100%;overflow:hidden;color:var(--snow);background:var(--ink);font-family:'Manrope',system-ui,sans-serif}
  .landing *{box-sizing:border-box}.landing a{color:inherit;text-decoration:none}.landing button{border:0;color:inherit;font:inherit;cursor:pointer}.landing h1,.landing h2,.landing h3,.landing p{margin-top:0}.landing :is(a,button,input):focus-visible{outline:2px solid #9edcff;outline-offset:4px}
  .guide{position:fixed;z-index:20;top:0;bottom:0;width:1px;background:rgba(255,255,255,.055);pointer-events:none}.guide-left{left:calc(50% - 590px)}.guide-right{right:calc(50% - 590px)}
  .skip{position:fixed;z-index:100;top:8px;left:8px;padding:12px 18px;border-radius:999px;color:#030508!important;background:#fff;transform:translateY(-150%)}.skip:focus{transform:none}
  .landing-nav{position:fixed;z-index:50;top:18px;left:50%;width:min(calc(100% - 40px),1120px);height:64px;display:flex;align-items:center;gap:28px;padding:7px 9px 7px 18px;border:1px solid rgba(255,255,255,.1);border-radius:999px;background:rgba(3,5,8,.72);box-shadow:0 20px 70px rgba(0,0,0,.3);transform:translateX(-50%);backdrop-filter:blur(22px);transition:transform .24s ease,background .24s ease}.landing-nav.compact{background:rgba(3,5,8,.92);transform:translateX(-50%) translateY(-8px)}
  .brand{display:flex;align-items:center;gap:9px;flex:none}.brand img{width:25px;height:25px}.brand b{font-size:16px;letter-spacing:-.03em}.desktop-nav{display:flex;justify-content:center;gap:24px;flex:1}.desktop-nav a{position:relative;padding:12px 0;color:#7e8894;font-size:11px;font-weight:700}.desktop-nav a:hover,.desktop-nav a.active{color:#fff}.desktop-nav a.active::after{content:'';position:absolute;right:0;bottom:6px;left:0;height:1px;background:var(--blue)}
  .nav-cta,.primary{min-height:48px;display:inline-flex;align-items:center;justify-content:center;gap:9px;padding:0 20px;border-radius:999px;color:#02070b!important;background:#f5f8fb;font-size:11px;font-weight:800;transition:transform .18s ease,background .18s ease}.nav-cta:hover,.primary:hover{background:#cceeff}.nav-cta:active,.primary:active{transform:scale(.98)}
  .menu-button{position:relative;width:44px;height:44px;display:none;place-items:center;border-radius:50%;background:#111820}.menu-button span{position:absolute;width:16px;height:1px;background:#fff;transform:translateY(-3px)}.menu-button span+span{transform:translateY(3px)}.mobile-nav{position:absolute;top:calc(100% + 8px);right:0;left:0;display:grid;padding:12px 18px;border:1px solid var(--line);border-radius:24px;background:#080c11f7;box-shadow:0 30px 90px #000}.mobile-nav a{min-height:52px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);font-size:13px;font-weight:700}.mobile-nav a:last-child{border:0}
  .hero{position:relative;min-height:920px;display:grid;place-items:center;isolation:isolate;padding:145px 24px 110px;border-bottom:1px solid var(--line)}.hero::before{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(ellipse 55% 50% at 50% 42%,transparent 0%,rgba(3,5,8,.28) 52%,rgba(3,5,8,.9) 88%),linear-gradient(180deg,rgba(3,5,8,.12),rgba(3,5,8,.04) 58%,#030508 97%)}.hero-current{position:absolute;z-index:-2;inset:0;width:100%;height:100%;object-fit:cover;object-position:center}.hero-copy{width:min(100%,980px);text-align:center}.hero-note{margin-bottom:24px;color:#a7b1bc;font-size:11px}.hero h1{margin:0;font-size:clamp(58px,7.3vw,112px);font-weight:700;line-height:.88;letter-spacing:-.075em}.hero h1 span{display:inline-block;color:#dce5ed}.hero-text{max-width:620px;margin:34px auto 0;color:#9aa5b1;font-size:15px;line-height:1.7}.hero-actions{display:flex;align-items:center;justify-content:center;gap:25px;margin-top:34px}.quiet-link{display:inline-flex;align-items:center;min-height:44px;color:#d1d8df!important;font-size:11px;font-weight:750;border-bottom:1px solid rgba(255,255,255,.28)}.platform-line{position:absolute;right:24px;bottom:27px;left:24px;display:flex;justify-content:center;gap:34px;color:#697480;font-size:9px;font-weight:700}
  .client-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{width:min(calc(100% - 48px),1180px);margin:0 auto;padding:132px 0}.intro h2{margin:0;font-size:clamp(42px,5.4vw,76px);font-weight:650;line-height:.98;letter-spacing:-.065em;text-wrap:balance}.intro>p{max-width:540px;margin:0;color:var(--steel);font-size:14px;line-height:1.75}.split-intro{display:grid;grid-template-columns:1fr .72fr;align-items:end;gap:80px;margin-bottom:65px}
  .client-window{overflow:hidden;border:1px solid var(--line-strong);border-radius:20px;background:#111318;box-shadow:0 60px 150px -70px rgba(55,150,220,.38)}.window-titlebar{height:48px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 17px;border-bottom:1px solid rgba(255,255,255,.08);background:#0b0d11}.window-titlebar>span{color:#858d96;font-size:10px}.window-titlebar>em{justify-self:end;color:#5f6973;font-size:9px;font-style:normal}.traffic{display:flex;gap:7px}.traffic i{width:9px;height:9px;border-radius:50%;background:#393d43}.traffic i:first-child{background:#59616c}.client-body{min-height:615px;display:grid;grid-template-columns:68px 1fr}.client-body>aside{display:flex;align-items:center;flex-direction:column;gap:15px;padding:20px 10px;border-right:1px solid rgba(255,255,255,.08);background:#0d0f13}.client-body>aside img{width:28px;height:28px;margin-bottom:18px}.client-body>aside i{width:42px;height:42px;display:grid;place-items:center;border-radius:10px;color:#6f7780;font-style:normal}.client-body>aside i.active{color:#bce7ff;background:#182534}.client-content{padding:30px 38px 26px}.subscription-head{display:flex;align-items:end;justify-content:space-between;gap:35px;padding:0 5px 24px;border-bottom:1px solid rgba(255,255,255,.1)}.subscription-head>span,.subscription-meta{display:flex;flex-direction:column}.subscription-head small{color:#737a83;font-size:9px}.subscription-head b{margin-top:5px;font-size:20px}.subscription-meta{text-align:right}.subscription-meta b{font-size:10px}.subscription-meta small{margin-top:5px;color:#69717a;font-size:9px}.server-list{padding:10px 0}.server-list button{width:100%;min-height:67px;display:flex;align-items:center;gap:14px;padding:8px 14px;border:1px solid transparent;border-radius:12px;background:transparent;text-align:left}.server-list button:hover{background:#171a20}.server-list button.selected{border-color:#477fc5;background:#1b2637}.server-list button>i{width:40px;height:40px;display:grid;place-items:center;flex:none;border-radius:9px;color:#8ed3fa;background:#192531;font-style:normal}.server-list button>i span{font-size:15px;font-weight:800}.server-list button>i.service{color:#d7aee5;background:#28202e}.server-list button>i.bypass{color:#78d5ae;background:#152821}.server-list button>span{min-width:0;display:flex;flex:1;flex-direction:column}.server-list button b{font-size:13px}.server-list button small{margin-top:4px;overflow:hidden;color:#767e88;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.server-list em{display:flex;align-items:center;gap:7px;color:#7e8791;font-size:9px;font-style:normal}.server-list u{width:7px;height:7px;border-radius:50%;background:#52dc96;text-decoration:none}.selection-note{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:4px 16px;padding:18px 20px;border-top:1px solid rgba(255,255,255,.09);background:#0d1015}.selection-note span{color:#6e7781;font-size:8px}.selection-note b{font-size:11px}.selection-note small{grid-column:1/-1;color:#626b75;font-size:8px}.loading,.data-error,.pricing-error{min-height:260px;display:grid;place-content:center;place-items:center;gap:10px;text-align:center}.loading span{width:26px;height:26px;border:2px solid #23313e;border-top-color:#82cef4;border-radius:50%;animation:spin .8s linear infinite}.data-error span,.pricing-error span{color:var(--steel);font-size:11px}.data-error a,.pricing-error a{color:#9ddcff;font-size:11px;font-weight:800}
  .apps-section{padding-top:40px}.apps-proof{min-height:680px;display:grid;grid-template-columns:1.05fr .95fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.phone-well{position:relative;display:grid;place-items:end center;overflow:hidden;background:radial-gradient(circle at 50% 70%,rgba(29,113,172,.22),transparent 55%)}.phone-well>img{width:min(78%,390px);height:585px;object-fit:contain;object-position:bottom}.app-switch{position:absolute;z-index:2;top:28px;display:flex;gap:3px;padding:4px;border:1px solid var(--line);border-radius:999px;background:#070a0e}.app-switch button{min-width:84px;min-height:38px;border-radius:999px;background:transparent;color:#7e8994;font-size:10px;font-weight:800}.app-switch button.active{color:#05090c;background:#eef6fb}.app-copy{display:flex;justify-content:center;flex-direction:column;padding:60px 70px;border-left:1px solid var(--line)}.app-copy h2{margin:0;font-size:clamp(38px,4.2vw,62px);line-height:.98;letter-spacing:-.06em}.app-copy>p{max-width:460px;margin:25px 0 0;color:var(--steel);font-size:13px;line-height:1.7}.device-tabs{display:grid;grid-template-columns:1fr 1fr;margin-top:36px;border-top:1px solid var(--line)}.device-tabs button{min-height:67px;display:flex;align-items:center;gap:11px;padding:0 5px;border-bottom:1px solid var(--line);background:transparent;color:#798490;font-size:10px;text-align:left}.device-tabs button:nth-child(odd){border-right:1px solid var(--line)}.device-tabs button.active{color:#dff4ff}.app-actions{display:flex;align-items:center;gap:24px;margin-top:34px}.feature-ledger{display:grid;grid-template-columns:1fr 1fr;margin-top:100px;border-top:1px solid var(--line)}.feature-ledger article{min-height:185px;padding:35px 38px;border-bottom:1px solid var(--line)}.feature-ledger article:nth-child(odd){border-right:1px solid var(--line)}.feature-ledger h3{margin:0;font-size:19px;letter-spacing:-.03em}.feature-ledger p{max-width:430px;margin:15px 0 0;color:var(--steel);font-size:12px;line-height:1.65}
  .bypass-section{width:min(calc(100% - 48px),1180px);min-height:390px;display:grid;grid-template-columns:1fr .85fr;align-items:center;gap:90px;margin:0 auto;padding:72px;border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);background:linear-gradient(105deg,rgba(6,39,74,.56),rgba(5,9,14,.2) 55%,rgba(2,7,12,.4))}.bypass-section h2{margin:0;font-size:clamp(38px,4.7vw,66px);line-height:1;letter-spacing:-.06em}.bypass-section p{max-width:600px;margin:22px 0 0;color:#9aa6b2;font-size:13px;line-height:1.75}.bypass-section a{display:inline-flex;align-items:center;gap:8px;margin-top:25px;color:#a6e0ff;font-size:11px;font-weight:800}.bypass-section dl{margin:0;border-top:1px solid var(--line)}.bypass-section dl div{display:flex;justify-content:space-between;gap:20px;padding:18px 0;border-bottom:1px solid var(--line)}.bypass-section dt{color:#88939f;font-size:11px}.bypass-section dd{margin:0;color:#dceaf2;font-size:11px;font-weight:800;text-align:right}
  .pricing-section{padding-bottom:80px}.pricing-intro{display:flex;align-items:end;justify-content:space-between;gap:80px}.pricing-intro h2{max-width:750px}.pricing-intro p{max-width:360px}.periods{width:max-content;display:flex;gap:3px;margin:45px 0 35px;padding:4px;border:1px solid var(--line);border-radius:999px}.periods button{min-width:80px;min-height:38px;border-radius:999px;background:transparent;color:#77818c;font-size:9px;font-weight:800}.periods button.active{color:#03070b;background:#eef6fb}.tariff-grid{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.tariff-grid article{min-height:470px;display:flex;flex-direction:column;padding:34px 32px;background:#070a0e}.tariff-grid article+article{border-left:1px solid var(--line)}.tariff-grid article.recommended{background:#0b121a}.tariff-grid header{display:flex;align-items:center;justify-content:space-between}.tariff-grid header span{font-size:18px;font-weight:800}.tariff-grid header em{padding:5px 8px;border:1px solid #315d7b;border-radius:999px;color:#9bdcff;font-size:8px;font-style:normal}.tariff-grid article>p{min-height:40px;margin:15px 0 32px;color:#7f8994;font-size:11px;line-height:1.5}.plan-price{display:flex;align-items:baseline;gap:8px}.plan-price b{font-size:38px;letter-spacing:-.055em}.plan-price span,.tariff-grid article>small{color:#6e7883;font-size:9px}.tariff-grid ul{display:grid;gap:13px;margin:30px 0;padding:26px 0 0;border-top:1px solid var(--line);list-style:none}.tariff-grid li{color:#aeb8c2;font-size:11px}.tariff-grid li::before{content:'—';margin-right:10px;color:#6f7c88}.tariff-grid article>button{min-height:48px;display:flex;align-items:center;justify-content:center;gap:8px;margin-top:auto;border:1px solid var(--line-strong);border-radius:999px;background:transparent;font-size:10px;font-weight:800}.tariff-grid article.recommended>button{border-color:#dbeef8;color:#03080b;background:#eff7fb}.custom-builder{display:grid;grid-template-columns:.72fr 1.35fr .62fr;gap:45px;margin-top:86px;padding:40px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.custom-heading h3{margin:0;font-size:27px;letter-spacing:-.045em}.custom-heading p{margin:12px 0 0;color:#7f8994;font-size:10px;line-height:1.6}.custom-controls{display:grid;gap:22px}.custom-controls label{display:grid;grid-template-columns:100px 1fr;align-items:center;gap:20px}.custom-controls label>span{color:#909aa5;font-size:9px}.custom-controls label>span b{float:right;color:#e4edf4}.custom-controls label>div{display:flex;gap:3px}.custom-controls button{min-width:42px;min-height:34px;border:1px solid var(--line);border-radius:8px;background:#0b1016;color:#6e7984;font-size:9px}.custom-controls button.active{border-color:#6197bc;color:#dcf3ff;background:#112132}.custom-controls input{width:100%;accent-color:#75c7f2}.custom-total{display:flex;align-items:flex-start;flex-direction:column;border-left:1px solid var(--line);padding-left:35px}.custom-total>span{color:#76808b;font-size:8px;line-height:1.5}.custom-total>b{margin-top:12px;font-size:30px;letter-spacing:-.05em}.custom-total>small{margin-top:3px;color:#7a8691;font-size:8px}.custom-total>a{display:flex;align-items:center;gap:7px;margin-top:auto;color:#a5ddfb;font-size:10px;font-weight:800}
  .cabinet-section{padding-top:105px}.device-stage{position:relative;min-height:700px;display:grid;place-items:center;margin-top:10px;overflow:hidden;background:radial-gradient(ellipse 55% 48% at 50% 58%,rgba(22,96,153,.22),transparent 70%)}.laptop{position:relative;width:min(86%,930px);transform:translateX(-5%)}.laptop-top{height:38px;display:flex;align-items:center;justify-content:center;border:1px solid #303842;border-bottom:0;border-radius:16px 16px 0 0;background:#0a0d12}.laptop-top>i{position:absolute;left:16px;width:7px;height:7px;border-radius:50%;background:#414a54;box-shadow:13px 0 #363e47,26px 0 #303741}.laptop-top span{color:#6e7882;font-size:9px}.laptop-top em{position:absolute;right:15px;color:#4f5964;font-size:8px;font-style:normal}.laptop-screen{height:500px;display:grid;grid-template-columns:170px 1fr;overflow:hidden;border:1px solid #303842;background:#080b10}.laptop-screen>nav{display:flex;flex-direction:column;gap:17px;padding:28px 25px;border-right:1px solid var(--line);color:#66717c;font-size:9px}.laptop-screen>nav img{width:28px;height:28px}.laptop-screen>nav b{margin:-40px 0 25px 39px;color:#eef5fa;font-size:13px}.laptop-screen>nav span:first-of-type{color:#c5eaff}.desktop-cabinet{padding:65px 70px}.desktop-cabinet>small{color:#71808d;font-size:9px}.desktop-cabinet h3{margin:13px 0 0;font-size:44px;letter-spacing:-.055em}.desktop-cabinet>p{margin:8px 0 35px;color:#83909c;font-size:10px}.desktop-cabinet>div{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.desktop-cabinet>div span{display:flex;flex-direction:column;padding:25px 0}.desktop-cabinet>div span+span{padding-left:30px;border-left:1px solid var(--line)}.desktop-cabinet>div b{font-size:23px}.desktop-cabinet>div small{margin-top:5px;color:#76818d;font-size:8px}.desktop-cabinet button{min-height:45px;margin-top:30px;padding:0 19px;border-radius:999px;color:#071019;background:#b9e8ff;font-size:9px;font-weight:800}.laptop-base{height:18px;margin:-1px -34px 0;border:1px solid #303842;border-radius:0 0 50% 50%;background:linear-gradient(#20262d,#090c10)}.phone{position:absolute;right:3%;bottom:20px;width:218px;height:445px;padding:8px;border:1px solid #48535f;border-radius:36px;background:#05070a;box-shadow:0 30px 70px rgba(0,0,0,.7);transform:rotate(2deg)}.phone-island{position:absolute;z-index:2;top:16px;left:50%;width:65px;height:17px;border-radius:999px;background:#020305;transform:translateX(-50%)}.phone-screen{height:100%;display:flex;align-items:center;flex-direction:column;padding:48px 17px 20px;border-radius:28px;background:linear-gradient(160deg,#111c29,#070b11 60%)}.phone-screen>img{width:25px;height:25px}.phone-screen>small{margin-top:7px;color:#80909f;font-size:8px}.phone-screen h3{margin:40px 0 0;font-size:67px;line-height:1;letter-spacing:-.06em}.phone-screen>p{margin:5px 0 25px;color:#778694;font-size:8px}.phone-screen>div{width:100%;display:grid;gap:8px}.phone-screen>div span{padding:12px;border:1px solid var(--line);border-radius:11px;color:#aebdcc;font-size:7px}.phone-screen button{width:100%;min-height:38px;margin-top:auto;border-radius:999px;color:#061018;background:#aee3ff;font-size:8px;font-weight:800}.phone-screen em{margin-top:11px;color:#4e5c68;font-size:6px;font-style:normal}.cabinet-link{width:max-content;display:flex;align-items:center;gap:8px;margin:-20px auto 0;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.28);font-size:11px;font-weight:800}
  .connection-section{padding-bottom:100px}.connection-section .intro{max-width:760px}.connection-section ol{display:grid;grid-template-columns:repeat(4,1fr);margin:58px 0 0;padding:0;border-top:1px solid var(--line);list-style:none}.connection-section li{padding:30px 26px 0 0}.connection-section li+li{padding-left:26px;border-left:1px solid var(--line)}.connection-section li>span{color:#6fc7f5;font-size:10px}.connection-section li>b{display:block;margin-top:22px;font-size:14px}.connection-section li>p{margin:10px 0 0;color:#7e8994;font-size:10px;line-height:1.55}
  .faq-section{display:grid;grid-template-columns:.7fr 1.3fr;gap:90px}.faq-list{border-top:1px solid var(--line)}.faq-list article{border-bottom:1px solid var(--line)}.faq-list h3{margin:0}.faq-list button{width:100%;min-height:82px;display:flex;align-items:center;justify-content:space-between;gap:25px;padding:0;background:transparent;text-align:left}.faq-list button span{font-size:13px}.faq-list button i{color:#79c8f0;font-size:20px;font-style:normal;font-weight:400}.faq-list article>div{padding:0 45px 25px 0}.faq-list p{max-width:650px;margin:0;color:#8a95a0;font-size:11px;line-height:1.75}
  .final-section{position:relative;width:min(calc(100% - 48px),1180px);min-height:560px;display:grid;place-items:center;isolation:isolate;overflow:hidden;margin:20px auto 120px;border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);text-align:center}.final-section::after{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(circle at 50% 45%,rgba(3,5,8,.15),rgba(3,5,8,.88) 73%)}.final-section>img{position:absolute;z-index:-2;inset:0;width:100%;height:100%;object-fit:cover}.final-section>div{padding:60px 24px}.final-section h2{margin:0;font-size:clamp(50px,6.5vw,88px);line-height:.9;letter-spacing:-.07em}.final-section p{margin:28px auto 0;color:#96a2ad;font-size:12px}.final-section nav{display:flex;align-items:center;justify-content:center;gap:26px;margin-top:31px}
  .links-section{display:grid;grid-template-columns:.75fr 1.25fr;gap:90px;padding-top:20px}.links-section h2{margin:0;font-size:clamp(35px,4.5vw,58px);line-height:1;letter-spacing:-.055em}.links-section nav{border-top:1px solid var(--line)}.links-section nav a{min-height:76px;display:grid;grid-template-columns:1fr 1.2fr auto;align-items:center;gap:20px;border-bottom:1px solid var(--line)}.links-section nav b{font-size:12px}.links-section nav span{color:#77838e;font-size:9px}.links-section nav a:hover :global(.arc-icon){transform:translateX(3px)}
  .footer{width:min(calc(100% - 48px),1180px);min-height:120px;display:flex;align-items:center;gap:40px;margin:0 auto;border-top:1px solid var(--line)}.footer nav{display:flex;gap:25px;margin-left:auto}.footer nav a,.footer small{color:#75808a;font-size:9px}.footer small{margin-left:25px}
  @keyframes spin{to{transform:rotate(360deg)}}
  @media(max-width:1228px){.guide{display:none}}
  @media(max-width:900px){.landing-nav{top:12px;width:calc(100% - 24px);height:60px}.landing-nav.compact{transform:translateX(-50%) translateY(-4px)}.desktop-nav{display:none}.nav-cta{margin-left:auto}.menu-button{display:grid}.hero{min-height:850px;padding-top:125px}.hero h1{font-size:clamp(58px,10vw,86px)}.client-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{width:min(calc(100% - 32px),720px);padding:105px 0}.split-intro,.faq-section,.links-section{grid-template-columns:1fr;gap:35px}.split-intro{margin-bottom:50px}.client-body{grid-template-columns:54px 1fr}.client-content{padding:25px 20px}.apps-proof{grid-template-columns:1fr;min-height:0}.phone-well{min-height:590px}.app-copy{padding:55px 45px;border-top:1px solid var(--line);border-left:0}.feature-ledger{margin-top:70px}.bypass-section{width:min(calc(100% - 32px),720px);grid-template-columns:1fr;gap:45px;padding:60px 44px}.pricing-intro{align-items:flex-start;flex-direction:column;gap:25px}.tariff-grid{grid-template-columns:1fr}.tariff-grid article{min-height:420px}.tariff-grid article+article{border-top:1px solid var(--line);border-left:0}.custom-builder{grid-template-columns:1fr;gap:35px}.custom-total{min-height:130px;padding:25px 0 0;border-top:1px solid var(--line);border-left:0}.device-stage{min-height:610px}.laptop{width:96%;transform:translateX(-4%)}.laptop-screen{height:420px;grid-template-columns:135px 1fr}.laptop-screen>nav{padding:25px 18px}.desktop-cabinet{padding:55px 35px}.phone{right:0;width:190px;height:390px}.connection-section ol{grid-template-columns:1fr 1fr;row-gap:35px}.connection-section li:nth-child(3){padding-left:0;border-left:0}.links-section{padding-top:30px}.footer{width:calc(100% - 32px);flex-wrap:wrap;padding:35px 0}.footer nav{order:3;width:100%;margin-left:0}.footer small{margin-left:auto}}
  @media(max-width:560px){.landing-nav .brand b{display:none}.nav-cta{min-height:43px;padding:0 15px;font-size:9px}.hero{min-height:780px;place-items:start;padding:150px 16px 90px}.hero::before{background:linear-gradient(180deg,rgba(3,5,8,.3),rgba(3,5,8,.56) 55%,#030508 96%)}.hero-current{object-position:67% center}.hero-copy{text-align:left}.hero-note{margin-bottom:20px}.hero h1{font-size:clamp(52px,15.2vw,70px);line-height:.9}.hero-text{margin-top:26px;font-size:12px;line-height:1.65}.hero-actions{align-items:flex-start;justify-content:flex-start;flex-direction:column;gap:15px;margin-top:28px}.platform-line{right:16px;bottom:19px;left:16px;justify-content:space-between;gap:4px;font-size:6px}.client-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{padding:78px 0}.intro h2{font-size:42px}.intro>p{font-size:12px}.client-window{margin-inline:-8px;border-radius:15px}.window-titlebar{grid-template-columns:1fr auto;height:43px}.window-titlebar>span{display:none}.client-body{grid-template-columns:1fr;min-height:555px}.client-body>aside{display:none}.client-content{padding:20px 10px 14px}.subscription-head{align-items:flex-start;padding:0 6px 18px}.subscription-head b{font-size:17px}.subscription-meta{max-width:125px}.server-list button{min-height:65px;padding:7px 8px}.server-list button>i{width:37px;height:37px}.server-list button b{font-size:11px}.server-list button small{max-width:190px}.server-list em{font-size:7px}.selection-note{padding:15px 12px}.apps-section{padding-top:20px}.phone-well{min-height:505px}.phone-well>img{height:460px}.app-copy{padding:45px 18px}.app-copy h2{font-size:42px}.device-tabs{grid-template-columns:1fr}.device-tabs button:nth-child(odd){border-right:0}.app-actions{align-items:flex-start;flex-direction:column;gap:14px}.feature-ledger{grid-template-columns:1fr}.feature-ledger article{min-height:145px;padding:28px 5px}.feature-ledger article:nth-child(odd){border-right:0}.bypass-section{min-height:580px;padding:48px 24px}.bypass-section h2{font-size:43px}.bypass-section p{font-size:12px}.periods{width:100%;overflow-x:auto;scrollbar-width:none}.periods::-webkit-scrollbar{display:none}.periods button{min-width:70px}.tariff-grid article{min-height:410px;padding:28px 22px}.custom-controls label{grid-template-columns:1fr;gap:10px}.custom-controls label>div{overflow-x:auto;scrollbar-width:none}.custom-controls label>div::-webkit-scrollbar{display:none}.custom-total>b{font-size:37px}.cabinet-section .split-intro{margin-bottom:15px}.device-stage{min-height:540px;overflow:visible;margin-inline:-12px}.laptop{width:108%;transform:translate(-7%,-28px)}.laptop-top{height:30px}.laptop-top span{font-size:6px}.laptop-top em{display:none}.laptop-screen{height:360px;grid-template-columns:1fr}.laptop-screen>nav{display:none}.desktop-cabinet{padding:52px 25px}.desktop-cabinet h3{font-size:35px}.phone{right:-1%;bottom:0;width:157px;height:325px;border-radius:28px}.phone-screen{padding:42px 12px 15px}.phone-screen h3{margin-top:28px;font-size:52px}.phone-screen>div span{padding:9px}.laptop-base{margin-inline:-10px}.cabinet-link{margin-top:0}.connection-section ol{grid-template-columns:1fr;gap:0}.connection-section li,.connection-section li+li,.connection-section li:nth-child(3){padding:23px 0;border-top:1px solid var(--line);border-left:0}.connection-section li>b{margin-top:10px}.faq-list button{min-height:75px}.faq-list button span{font-size:12px}.final-section{width:calc(100% - 32px);min-height:500px;margin-bottom:80px}.final-section>div{padding:45px 18px}.final-section h2{font-size:52px}.final-section nav{align-items:center;flex-direction:column;gap:13px}.links-section nav a{grid-template-columns:1fr auto}.links-section nav a span{display:none}.footer{gap:20px}.footer nav{gap:18px;flex-wrap:wrap}}
  @media(prefers-reduced-motion:reduce){:global(.landing-document){scroll-behavior:auto}.landing *{transition:none!important}.loading span{animation:none}}
</style>
