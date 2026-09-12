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
  let tariffs = []
  let config = {}
  let dataError = false
  let selectedPeriod = 3
  let openFaq = -1
  let customMonths = 3
  let customDevices = 3
  let customLte = 45
  let customQuote = null
  let quoteBusy = true
  let quoteTimer

  $: periodTariffs = tariffs.filter((item) => Number(item.period_months) === selectedPeriod)
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
      {#each [['subscription','Попробовать'],['apps','Приложения'],['tariffs','Тарифы'],['faq','Вопросы']] as item}
        <a class:active={activeSection === item[0]} href={`#${item[0]}`}>{item[1]}</a>
      {/each}
    </nav>
    <a class="nav-cta" href="/app" on:click={() => track('landing_cabinet_click', { place:'nav' })}>Личный кабинет <ArcIcon name="arrow" size={17} /></a>
  </header>

  <main id="main">
    <section class="hero" id="top">
      <div class="hero-copy">
        <h1>Одна подписка.<br /><span>Свободный интернет.</span></h1>
        <p class="hero-text">Обычные подключения для каждого дня и отдельные профили обхода глушилок — когда привычной сети недостаточно.</p>
        <div class="hero-actions">
          <a class="primary" href="/app" on:click={() => track('landing_cabinet_click', { place:'hero' })}>Начать пользоваться <ArcIcon name="arrow" size={18} /></a>
        </div>
      </div>
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
      <div class="apps-intro">
        <h2>Работает на ваших устройствах</h2>
        <p>Автовыбор, обычные локации и отдельные профили обхода доступны через одну подписку.</p>
      </div>

      <div class="feature-ledger" id="features">
        {#each featureRows as feature, index}
          <article class:feature-primary={index === 0}>
            {#if index === 0}
              <div class="route-orbit" aria-hidden="true"><i></i><i></i><i></i><b></b></div>
            {:else}
              <span class="feature-index">0{index + 1}</span>
            {/if}
            <div><h3>{feature[0]}</h3><p>{feature[1]}</p></div>
          </article>
        {/each}
      </div>

      <div class="apps-proof">
        <div class="app-copy">
          <h3>Выберите привычное приложение</h3>
          <p>ArcVPN работает через Happ и INCY. Ссылка импорта и инструкция появятся в личном кабинете — выбирать приложение на этой странице не нужно.</p>
          <div class="device-list" aria-label="Поддерживаемые платформы">
            {#each devices as device}
              <span>
                <DeviceIcon name={device.icon} size={20} /><span>{device.label}</span>
              </span>
            {/each}
          </div>
        </div>
        <div class="app-icon-stage" aria-label="Поддерживаемые приложения: Happ и INCY">
          <figure class="app-phone app-phone-happ"><img src={`${base}assets/arc-flow/connect-happ-phone-v2.png`} alt="Приложение Happ на телефоне" width="480" height="712" loading="lazy" decoding="async" /></figure>
          <figure class="app-phone app-phone-incy"><img src={`${base}assets/arc-flow/connect-incy-phone-v1.png`} alt="Приложение INCY на телефоне" width="480" height="664" loading="lazy" decoding="async" /></figure>
        </div>
      </div>
    </section>

    <section class="bypass-section">
      <div class="bypass-copy">
        <span class="section-chip">Отдельный запас</span>
        <h2>Обход глушилок — отдельный запас</h2>
        <p>Основной трафик ArcVPN остаётся безлимитным. Дополнительные гигабайты расходуются только при выборе специальных профилей обхода — для сетей, где обычное подключение не справляется.</p>
        <p>Если запас закончится, Автовыбор и обычные локации продолжат работать. Объём обхода можно выбрать в тарифе или докупить позже в личном кабинете.</p>
        <small>Доступность зависит от сети, устройства и характера ограничений.</small>
        <a class="primary" href="#tariffs">Тарифы с обходом <ArcIcon name="arrow" size={18} /></a>
      </div>
      <div class="bypass-well"><dl><div><dt>Основной интернет</dt><dd>Безлимитно</dd></div><div><dt>Профили обхода</dt><dd>Отдельные гигабайты</dd></div><div><dt>После исчерпания</dt><dd>Обычные профили работают</dd></div><div><dt>Нужен ещё запас</dt><dd>Можно докупить</dd></div></dl></div>
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
                <div class="tariff-top">
                  <header><span>{productNames[code]}</span>{#if code === 'standard'}<em>Оптимальный</em>{/if}</header>
                  <p>{productCopy[code]}</p>
                  <div class="plan-price"><b>{plan.monthly_rub.toLocaleString('ru-RU')} ₽</b><span>в месяц</span></div>
                  <small>{plan.price_rub.toLocaleString('ru-RU')} ₽ за {plan.period_months} {plan.period_months === 1 ? 'месяц' : 'месяца'}</small>
                </div>
                <ul>
                  <li><ArcIcon name="signal" size={17} />Основной трафик безлимитный</li>
                  <li><ArcIcon name="devices" size={17} />{plan.device_limit} {plan.device_limit >= 2 && plan.device_limit <= 4 ? 'устройства' : 'устройств'}</li>
                  <li><ArcIcon name={plan.lte_quota_gb ? 'lte' : 'shield'} size={17} />{plan.lte_quota_gb ? `${plan.lte_quota_gb} ГБ обхода` : 'Без трафика обхода'}</li>
                </ul>
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
      <div class="arc-horizon" aria-hidden="true"></div>
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
  :global(.landing-document){scroll-padding-top:105px;background:#000}
  :global(body:has(.landing)){min-width:320px;overflow-x:hidden;color:#f4f7fa;background:#000;overscroll-behavior-y:auto}
  :global(body:has(.landing) #app){max-width:none;overflow:visible}
  .landing{--ink:#000;--carbon:#08090b;--surface:#0c0e12;--line:rgba(219,234,247,.12);--line-strong:rgba(219,234,247,.22);--snow:#f4f7fa;--steel:#8d98a7;--accent:#78cfff;--accent-hover:#a8e2ff;--accent-soft:rgba(120,207,255,.16);--accent-glow:rgba(120,207,255,.78);--accent-ink:#061018;--blue:var(--accent);--deep-blue:#06274a;width:100%;overflow:hidden;color:var(--snow);background:var(--ink);font-family:'Manrope',system-ui,sans-serif}
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

  /* Blue-light composition shared by the hero and pricing story. */
  .hero{min-height:max(900px,100svh);display:flex;align-items:center;flex-direction:column;overflow:hidden;padding:140px 24px 0;background:#02050a}
  .hero::before{z-index:-2;background:repeating-radial-gradient(ellipse 76% 62% at 50% 47%,transparent 0 95px,rgba(111,190,247,.055) 96px 97px,transparent 98px 130px),radial-gradient(ellipse 54% 42% at 50% 68%,rgba(36,145,224,.38),rgba(13,57,111,.16) 48%,transparent 73%),linear-gradient(180deg,#020409 0%,#030714 58%,#02050a 100%)}
  .hero::after{content:'';position:absolute;z-index:-1;left:50%;bottom:-320px;width:min(1120px,92vw);height:620px;border-radius:50%;background:#228ed5;filter:blur(115px);opacity:.42;transform:translateX(-50%);pointer-events:none}
  .hero-copy{position:relative;z-index:2;width:min(100%,850px);text-align:center;transform:none}
  .hero h1{font-size:clamp(52px,5.4vw,82px);font-weight:620;line-height:.98;letter-spacing:-.064em;text-shadow:none;text-wrap:balance}
  .hero-text{max-width:610px;margin:22px auto 0;color:#8d9aa8;font-size:13px}
  .hero-actions{margin-top:28px}
  .hero-stage{position:relative;z-index:2;width:min(1120px,calc(100vw - 64px));aspect-ratio:1.73;margin-top:66px;overflow:hidden;border:1px solid rgba(176,220,250,.18);border-radius:24px 24px 0 0;background:#050a11;box-shadow:0 -16px 90px rgba(66,169,236,.2),0 42px 120px rgba(0,0,0,.74)}
  .hero-stage::after{content:'';position:absolute;inset:38% 0 0;background:linear-gradient(180deg,transparent,rgba(2,5,10,.16) 45%,rgba(2,5,10,.88));pointer-events:none}
  .hero-stage>img{width:100%;height:auto;display:block}

  .trial-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section{position:relative}
  .trial-section::before,.pricing-section::before,.cabinet-section::before{content:'';position:absolute;z-index:-1;left:50%;width:min(1000px,95vw);height:420px;border-radius:50%;background:rgba(30,130,205,.13);filter:blur(120px);transform:translateX(-50%);pointer-events:none}
  .trial-section::before{top:-120px}.pricing-section::before{top:180px}.cabinet-section::before{top:220px}
  .pricing-intro{align-items:center;flex-direction:column;gap:18px;text-align:center}
  .pricing-intro h2,.pricing-intro p{max-width:720px}
  .periods{margin:34px auto 48px;padding:5px;background:#07111b;border-color:rgba(147,201,238,.13)}
  .periods button{min-width:94px;min-height:42px;color:#8493a1}.periods button.active{color:#071019;background:#eaf5fb}
  .tariff-grid{gap:18px;align-items:start}
  .tariff-grid article,.tariff-grid article.recommended{min-height:0;padding:6px;border-color:rgba(148,201,238,.14);border-radius:28px;background:#07111c;box-shadow:0 26px 80px -58px rgba(40,125,181,.46);transform:none}
  .tariff-grid article:hover,.tariff-grid article.recommended:hover{border-color:rgba(141,205,255,.42);transform:translateY(-4px)}
  .tariff-top{min-height:220px;padding:25px 24px;border-radius:22px;background:linear-gradient(145deg,#10283a,#0b1b29);box-shadow:inset 0 1px 0 rgba(255,255,255,.055)}
  .tariff-grid article:nth-child(1) .tariff-top{background:linear-gradient(145deg,#102536,#0b1925)}
  .tariff-grid article.recommended .tariff-top{background:linear-gradient(145deg,#17618f,#103d61);box-shadow:0 14px 50px rgba(56,159,218,.2),inset 0 1px 0 rgba(255,255,255,.09)}
  .tariff-grid article:nth-child(3) .tariff-top{background:linear-gradient(145deg,#173044,#0d202f)}
  .tariff-grid header span{font-size:14px;text-transform:uppercase;letter-spacing:.04em}.tariff-grid header em{color:#e6f6ff;border-color:rgba(225,244,255,.36);background:rgba(255,255,255,.08)}
  .tariff-grid .tariff-top>p{min-height:38px;margin:16px 0 23px;color:#9eb2c2;font-size:10px;line-height:1.5}
  .plan-price b{font-size:46px}.plan-price span,.tariff-grid .tariff-top>small{color:#a7bbc9}
  .tariff-grid ul{margin:0 19px;padding:24px 4px 20px;border-top:0}.tariff-grid li{color:#bdcbd5}
  .tariff-grid article>button{min-height:50px;margin:0 12px 12px;border-color:rgba(215,232,255,.15);color:#07111c;background:#edf6fb}
  .tariff-grid article>button:hover,.tariff-grid article.recommended>button:hover{color:#07101c;background:#ccecff}
  .custom-builder{margin-top:88px;border-color:rgba(117,185,242,.2);background:radial-gradient(circle at 78% 26%,rgba(51,123,218,.22),transparent 35%),linear-gradient(145deg,#0d1730,#070d1a 72%);box-shadow:0 40px 120px -72px rgba(63,151,230,.62)}

  @media(max-width:900px){.hero{min-height:850px;padding-top:128px}.hero-stage{width:min(820px,calc(100vw - 32px));margin-top:60px}.pricing-intro{align-items:center;text-align:center}.tariff-grid article,.tariff-grid article.recommended{min-height:0}.tariff-grid article.recommended:hover{transform:translateY(-4px)}}
  @media(max-width:560px){.hero{min-height:780px;align-items:center;padding:112px 16px 0}.hero::before{background:repeating-radial-gradient(ellipse 120% 54% at 50% 51%,transparent 0 62px,rgba(111,190,247,.05) 63px 64px,transparent 65px 88px),radial-gradient(ellipse 90% 38% at 50% 73%,rgba(36,145,224,.36),transparent 72%),linear-gradient(180deg,#020409,#030714 62%,#02050a)}.hero::after{bottom:-250px;width:120vw;height:500px;filter:blur(90px)}.hero-copy{text-align:center}.hero h1{font-size:clamp(41px,12vw,50px);line-height:.98}.hero-text{max-width:340px;margin:19px auto 0;font-size:11px}.hero-actions{align-items:center;justify-content:center;margin-top:24px}.hero-stage{width:calc(100vw - 24px);aspect-ratio:.92;margin-top:48px;border-radius:22px 22px 0 0}.hero-stage>img{width:auto;height:100%;max-width:none;transform:translateX(-32%)}.hero-stage::after{inset:42% 0 0}.tariff-grid article,.tariff-grid article.recommended{min-height:0;padding:6px;border-radius:27px}.tariff-top{min-height:210px;padding:23px 20px;border-radius:21px}.tariff-grid ul{margin:0 17px;padding-bottom:19px}.tariff-grid article>button{margin:0 11px 11px}.custom-builder{margin-top:64px}}
  @media(min-width:780px){.tariff-grid{grid-template-columns:repeat(3,1fr)}}
  .hero-text{margin-top:38px}
  .hero-stage{width:min(980px,calc(100vw - 96px));margin-top:58px}
  .nav-cta:hover,.primary:hover{background:#e1e4e6}
  .tariff-grid article>button:hover,.tariff-grid article.recommended>button:hover{color:#07101c;background:#dde1e4}
  @media(max-width:900px){.hero-stage{width:min(760px,calc(100vw - 48px))}}
  @media(max-width:560px){.hero-text{margin-top:30px}.hero-stage{width:calc(100vw - 38px);margin-top:42px}}
  .landing .hero-text{margin:54px auto 0}
  .hero-visual{position:relative;z-index:2;width:min(1180px,calc(100vw - 48px));display:grid;place-items:center;isolation:isolate;overflow:hidden;margin-top:56px;padding:54px 92px 0;border-radius:74px 74px 0 0}
  .hero-visual::before{content:'';position:absolute;z-index:-2;inset:0;border-radius:74px 74px 0 0;background:linear-gradient(90deg,rgba(49,133,187,.62),rgba(27,86,126,.21) 13%,rgba(3,7,12,.05) 29%,rgba(3,7,12,.05) 71%,rgba(27,86,126,.21) 87%,rgba(49,133,187,.62)),linear-gradient(180deg,rgba(35,112,166,.13),rgba(4,8,13,.92) 58%);box-shadow:inset 0 1px 0 rgba(180,225,251,.18)}
  .hero-visual::after{content:'';position:absolute;z-index:-1;inset:27px 74px 0;border:1px solid rgba(181,217,239,.16);border-bottom:0;border-radius:46px 46px 0 0;background:#02060b;box-shadow:0 -18px 70px rgba(74,169,224,.15)}
  .hero-stage{width:min(900px,100%);margin:0;border:8px solid rgba(102,145,174,.24);border-bottom:0;border-radius:30px 30px 0 0;box-shadow:0 -12px 70px rgba(72,167,224,.12),0 42px 120px rgba(0,0,0,.72)}

  .trial-section,.apps-section,.pricing-section,.cabinet-section,.connection-section,.faq-section,.links-section,.bypass-section{isolation:isolate}
  .trial-section::before,.apps-section::before,.pricing-section::before,.cabinet-section::before,.connection-section::before,.faq-section::before,.links-section::before,.bypass-section::before{content:'';position:absolute;z-index:0;top:-105px;left:50%;width:min(1220px,108vw);height:250px;border-radius:50%;background:radial-gradient(ellipse at center,rgba(71,167,226,.28),rgba(30,91,132,.12) 43%,transparent 72%);filter:blur(42px);opacity:.9;transform:translateX(-50%);pointer-events:none}
  .trial-section>* ,.apps-section>* ,.pricing-section>* ,.cabinet-section>* ,.connection-section>* ,.faq-section>* ,.links-section>* ,.bypass-section>*{position:relative;z-index:1}
  .apps-section::before,.cabinet-section::before,.faq-section::before{background:radial-gradient(ellipse at center,rgba(44,137,198,.22),rgba(23,75,110,.1) 46%,transparent 72%)}

  @media(max-width:900px){.hero-visual{width:calc(100vw - 32px);padding:45px 54px 0;border-radius:56px 56px 0 0}.hero-visual::after{inset:23px 40px 0;border-radius:38px 38px 0 0}.hero-stage{width:100%;border-width:7px}}
  @media(max-width:560px){.landing .hero-text{margin:40px auto 0}.hero-visual{width:calc(100vw - 20px);margin-top:42px;padding:31px 18px 0;border-radius:38px 38px 0 0}.hero-visual::after{inset:14px 10px 0;border-radius:30px 30px 0 0}.hero-stage{width:100%;aspect-ratio:.92;margin:0;border-width:5px;border-radius:24px 24px 0 0}.hero-stage>img{width:auto;height:100%;max-width:none;transform:translateX(-32%)}.trial-section::before,.apps-section::before,.pricing-section::before,.cabinet-section::before,.connection-section::before,.faq-section::before,.links-section::before,.bypass-section::before{top:-70px;height:180px;filter:blur(34px)}}

  /* Hero v1: a compact product-first composition derived from the approved reference. */
  .hero{min-height:max(820px,100svh);padding-top:132px}
  .hero::before{background:linear-gradient(180deg,#010204 0%,#020409 72%,#02050a 100%)}
  .hero::after{bottom:-390px;width:min(1180px,94vw);height:690px;filter:blur(130px);opacity:.12}
  .hero-copy{width:min(100%,780px)}
  .hero h1{font-size:clamp(50px,5vw,76px);line-height:1;letter-spacing:-.058em}
  .landing .hero-text{max-width:560px;margin:26px auto 0;color:#95a2ae;font-size:12px;line-height:1.6}
  .hero-actions{margin-top:27px}
  .hero-visual{width:min(1240px,calc(100vw - 32px));margin-top:42px;padding:124px 104px 0;border-radius:0 0 34px 34px}
  .hero-visual::before{border-radius:0 0 34px 34px;background:linear-gradient(90deg,rgba(84,181,237,.9) 0%,rgba(38,117,167,.3) 11%,rgba(2,6,11,0) 28%,rgba(2,6,11,0) 72%,rgba(38,117,167,.3) 89%,rgba(84,181,237,.9) 100%),linear-gradient(180deg,rgba(2,5,9,0) 0%,rgba(2,5,9,.72) 23%,rgba(11,47,76,.6) 68%,rgba(132,214,255,.96) 100%);box-shadow:inset 0 -1px 0 rgba(214,242,255,.34);-webkit-mask-image:linear-gradient(180deg,transparent 0,#000 34%,#000 100%);mask-image:linear-gradient(180deg,transparent 0,#000 34%,#000 100%)}
  .hero-visual::after{display:none}
  .hero-stage{width:min(1040px,100%);padding:8px 8px 0;border:1px solid rgba(211,235,248,.24);border-bottom:0;border-radius:30px 30px 0 0;background:linear-gradient(135deg,rgba(226,243,252,.18),rgba(109,145,166,.07) 42%,rgba(225,241,249,.13));box-shadow:inset 0 1px 0 rgba(255,255,255,.2),0 -12px 34px rgba(255,255,255,.025),0 42px 120px rgba(0,0,0,.76);backdrop-filter:blur(18px)}
  .hero-stage>picture{overflow:hidden;border-radius:21px 21px 0 0}

  @media(max-width:900px){.hero{min-height:800px;padding-top:120px}.hero-visual{width:calc(100vw - 20px);margin-top:40px;padding:88px 58px 0;border-radius:0 0 28px 28px}.hero-visual::before{border-radius:0 0 28px 28px}.hero-visual::after{inset:auto 6% 0;height:calc(100% - 72px);border-radius:28px 28px 0 0}.hero-stage{border-width:10px;border-radius:28px 28px 0 0}}
  @media(max-width:560px){.hero{min-height:735px;padding-top:106px}.hero h1{font-size:clamp(40px,11.6vw,48px);letter-spacing:-.052em}.landing .hero-text{max-width:330px;margin:22px auto 0;font-size:10.5px}.hero-actions{margin-top:23px}.hero-visual{width:calc(100vw - 8px);margin-top:32px;padding:58px 16px 0;border-radius:0 0 22px 22px}.hero-visual::before{border-radius:0 0 22px 22px;background:linear-gradient(90deg,rgba(84,181,237,.8),rgba(23,88,131,.2) 13%,transparent 29%,transparent 71%,rgba(23,88,131,.2) 87%,rgba(84,181,237,.8)),linear-gradient(180deg,transparent,rgba(2,5,9,.68) 25%,rgba(12,52,84,.58) 70%,rgba(125,210,253,.9))}.hero-visual::after{inset:auto 3% 0;height:calc(100% - 48px);border-radius:21px 21px 0 0}.hero-stage{aspect-ratio:1.08;border-width:7px;border-radius:21px 21px 0 0}.hero-stage>img{transform:translateX(-27%)}}

  /* Hero-to-trial transition and the second section stay on true black. */
  .hero{border-bottom:0;background:#000}
  .hero::before{background:#000}
  .trial-section{width:min(calc(100% - 48px),1080px);padding:132px 0 144px;background:#000}
  .trial-section::before,.trial-panel::before{display:none}
  .trial-intro{display:flex;align-items:center;flex-direction:column;gap:22px;margin-bottom:58px;text-align:center}
  .trial-intro h2{max-width:720px;font-size:clamp(44px,4.7vw,66px);line-height:1.02;letter-spacing:-.055em}
  .trial-intro>p{max-width:650px;color:#818992;font-size:12px;line-height:1.7}
  .trial-panel{display:grid;grid-template-columns:1.16fr .84fr;gap:16px;overflow:visible;border:0;border-radius:0;background:none;box-shadow:none}
  .trial-panel article{min-height:350px;padding:38px 40px;border:1px solid rgba(255,255,255,.09);border-radius:24px;background:#08090b;box-shadow:none}
  .trial-panel article+article{border-left:1px solid rgba(255,255,255,.09)}
  .trial-panel span{color:#757e87;font-size:10px}
  .trial-panel strong{margin-top:20px;font-size:clamp(42px,4.2vw,58px)}
  .trial-panel p{max-width:410px;margin-top:22px;color:#858d96}
  .trial-panel a{border-color:rgba(255,255,255,.16);background:#0d1014}
  .trial-panel a:hover{border-color:rgba(255,255,255,.28);background:#14171b}
  .trial-free a{border-color:#f0f2f4;background:#f0f2f4}
  .trial-free a:hover{background:#dfe2e5}

  @media(max-width:900px){.trial-section{width:min(calc(100% - 32px),720px);padding:112px 0 124px}.trial-panel{grid-template-columns:1fr 1fr}.trial-panel article{min-height:330px;padding:34px 30px}}
  @media(max-width:620px){.trial-section{padding:92px 0 104px}.trial-intro{gap:18px;margin-bottom:40px}.trial-intro h2{font-size:42px}.trial-panel{grid-template-columns:1fr;gap:12px}.trial-panel article{min-height:300px;padding:30px 24px;border-radius:20px}.trial-panel article+article{border-left:1px solid rgba(255,255,255,.09)}.trial-panel strong{font-size:44px}}

  /* Third section: product facts first, then one focused install scene. */
  .hero-stage>picture,.hero-stage>picture>img{width:100%;height:auto;display:block}
  .apps-section{width:min(calc(100% - 48px),1080px);padding:132px 0 0;background:#000}
  .apps-section::before{display:none}
  .apps-intro{display:flex;align-items:center;flex-direction:column;gap:20px;text-align:center}
  .apps-intro h2{max-width:760px;margin:0;font-size:clamp(44px,4.7vw,66px);font-weight:650;line-height:1.02;letter-spacing:-.055em;text-wrap:balance}
  .apps-intro p{max-width:620px;margin:0;color:#818992;font-size:12px;line-height:1.7}
  .apps-section .feature-ledger{grid-template-columns:repeat(4,1fr);gap:12px;margin-top:56px;border:0}
  .apps-section .feature-ledger article{min-height:190px;padding:28px 25px;border:1px solid rgba(255,255,255,.09)!important;border-radius:20px;background:#08090b}
  .apps-section .feature-ledger h3{font-size:18px;line-height:1.15}
  .apps-section .feature-ledger p{margin-top:17px;color:#818992;font-size:10px;line-height:1.6}
  .apps-proof{min-height:720px;display:flex;align-items:center;flex-direction:column;margin-top:118px;border:0;background:#000}
  .app-copy{position:relative;z-index:2;display:flex;align-items:center;flex-direction:column;width:min(100%,760px);padding:0;border:0;text-align:center}
  .app-copy h3{margin:26px 0 0;font-size:clamp(36px,4vw,54px);font-weight:620;line-height:1.04;letter-spacing:-.05em}
  .app-copy>p{max-width:520px;margin:18px auto 0;color:#818992;font-size:11px;line-height:1.65}
  .app-switch{position:static;order:-1;width:max-content;margin:0 auto;padding:4px;border-color:rgba(255,255,255,.11);background:#08090b}
  .device-tabs{display:flex;justify-content:center;gap:4px;margin-top:28px;padding:4px;border:1px solid rgba(255,255,255,.1);border-radius:999px;background:#08090b}
  .device-tabs button,.device-tabs button:nth-child(odd){min-height:42px;padding:0 16px;border:0;border-radius:999px}
  .device-tabs button.active{color:#02070b;background:#eef4f7}
  .app-actions{justify-content:center;margin-top:24px}
  .phone-well{position:relative;width:100%;min-height:390px;display:grid;place-items:start center;margin-top:54px;overflow:visible;background:none}
  .phone-well::before{content:'';position:absolute;z-index:0;top:42%;left:50%;width:100vw;height:330px;background:radial-gradient(ellipse at center,rgba(126,211,255,.92) 0%,rgba(54,148,210,.48) 34%,rgba(16,62,96,.16) 58%,transparent 74%);filter:blur(18px);transform:translate(-50%,-50%);pointer-events:none}
  .phone-well::after{content:'';position:absolute;z-index:0;top:44%;left:50%;width:100vw;height:2px;background:linear-gradient(90deg,transparent,rgba(196,235,255,.72),transparent);filter:blur(1px);transform:translateX(-50%)}
  .phone-well>img{position:relative;z-index:1;width:auto;height:390px;object-fit:contain;object-position:top;filter:drop-shadow(0 34px 45px rgba(0,0,0,.6))}

  @media(max-width:900px){.apps-section{width:min(calc(100% - 32px),720px);padding-top:112px}.apps-section .feature-ledger{grid-template-columns:1fr 1fr}.apps-proof{margin-top:96px}.device-tabs{flex-wrap:wrap;border-radius:24px}.phone-well::before,.phone-well::after{width:100vw}}
  @media(max-width:620px){.hero-stage{aspect-ratio:568/912}.hero-stage>picture{width:100%;height:100%}.hero-stage>picture>img{width:100%;height:100%;object-fit:cover;object-position:top;transform:none}.apps-section{padding-top:92px}.apps-intro h2{font-size:42px}.apps-section .feature-ledger{grid-template-columns:1fr;gap:10px;margin-top:40px}.apps-section .feature-ledger article{min-height:0;padding:24px 22px}.apps-proof{min-height:660px;margin-top:84px}.app-copy h3{font-size:38px}.device-tabs{display:grid;grid-template-columns:1fr 1fr;width:100%;padding:5px}.device-tabs button{justify-content:center;padding:0 10px}.phone-well{min-height:360px;margin-top:44px}.phone-well::before{height:250px}.phone-well>img{height:340px}}

  /* Static compatibility story and the fourth reference-led section. */
  .apps-section .feature-ledger{grid-template-columns:repeat(2,1fr);gap:12px;width:min(100%,900px);margin:56px auto 0}
  .apps-section .feature-ledger article{min-height:150px}
  .apps-proof{min-height:650px;margin-top:108px}
  .supported-apps{display:flex;align-items:center;gap:11px;color:#dce8ef;font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
  .supported-apps span{display:inline-flex;align-items:center;gap:8px}
  .supported-apps span+span::before{content:'';width:3px;height:3px;border-radius:50%;background:#77c9f5;box-shadow:0 0 12px #77c9f5}
  .device-list{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:23px;margin-top:30px;color:#8f9aa5;font-size:10px;font-weight:700}
  .device-list>span{display:inline-flex;align-items:center;gap:8px;white-space:nowrap}
  .device-list :global(.arc-icon){color:#b7c5cf}
  .phone-well{min-height:470px;display:flex;align-items:flex-start;justify-content:center;gap:22px;margin-top:42px;padding-top:38px}
  .phone-well::before{top:51%;width:112vw;height:420px;background:radial-gradient(ellipse 30% 24% at 13% 51%,rgba(126,211,255,.82),rgba(48,145,205,.36) 45%,transparent 76%),radial-gradient(ellipse 32% 25% at 87% 50%,rgba(139,218,255,.9),rgba(48,145,205,.34) 45%,transparent 77%),radial-gradient(ellipse 76% 17% at 50% 50%,rgba(211,241,255,.82),rgba(89,181,231,.4) 38%,rgba(18,66,98,.12) 66%,transparent 82%);filter:blur(24px)}
  .phone-well::after{content:'';position:absolute;z-index:0;top:48%;left:50%;width:112vw;height:230px;background:radial-gradient(ellipse 58% 27% at 50% 48%,rgba(205,239,255,.56),rgba(73,164,216,.22) 44%,transparent 76%);filter:blur(42px);transform:translate(-50%,-50%);pointer-events:none}
  .app-phone{position:relative;z-index:1;width:188px;margin:0;filter:drop-shadow(0 32px 42px rgba(0,0,0,.68))}
  .app-phone-incy{margin-top:62px}
  .app-phone img{display:block;width:100%;height:auto}
  .app-phone figcaption{position:absolute;top:13px;left:50%;padding:7px 12px;border:1px solid rgba(255,255,255,.16);border-radius:999px;background:rgba(3,8,13,.66);box-shadow:inset 0 1px 0 rgba(255,255,255,.1);backdrop-filter:blur(12px);color:#e8f4fa;font-size:9px;font-weight:800;letter-spacing:.04em;transform:translateX(-50%)}

  .bypass-section{position:relative;width:min(calc(100% - 48px),1080px);min-height:900px;display:flex;align-items:center;flex-direction:column;gap:0;overflow:visible;padding:132px 0 0;border:0;background:#000;text-align:center}
  .bypass-section::before{display:none}
  .bypass-copy{display:flex;align-items:center;flex-direction:column;max-width:760px}
  .section-chip{padding:8px 14px;border:1px solid rgba(255,255,255,.11);border-radius:999px;color:#939da6;font-size:8px;font-weight:800}
  .bypass-section h2{max-width:720px;margin:27px 0 0;font-size:clamp(44px,4.7vw,66px);font-weight:620;line-height:1.02;letter-spacing:-.055em;text-wrap:balance}
  .bypass-section p{max-width:610px;margin:20px auto 0;color:#858e97;font-size:11px;line-height:1.7}
  .bypass-section p+p{margin-top:8px}.bypass-section small{margin-top:14px;color:#626b74}.bypass-section .primary{margin-top:27px;color:#03070b!important}
  .bypass-well{position:relative;width:100vw;min-height:430px;display:grid;place-items:start center;overflow:hidden;margin-top:48px;padding-top:83px}
  .bypass-well::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 34% 23% at 10% 50%,rgba(116,204,251,.78),rgba(40,133,190,.28) 47%,transparent 78%),radial-gradient(ellipse 35% 24% at 90% 49%,rgba(132,212,255,.84),rgba(43,139,198,.3) 46%,transparent 78%),radial-gradient(ellipse 75% 16% at 50% 49%,rgba(216,242,255,.72),rgba(83,177,228,.34) 39%,rgba(17,61,91,.1) 66%,transparent 82%);filter:blur(26px)}
  .bypass-well::after{content:'';position:absolute;top:49%;left:50%;width:108vw;height:220px;background:radial-gradient(ellipse 58% 25% at 50% 50%,rgba(202,237,255,.5),rgba(72,164,217,.18) 46%,transparent 76%);filter:blur(44px);transform:translate(-50%,-50%)}
  .bypass-section dl{position:relative;z-index:1;width:min(calc(100% - 32px),520px);margin:0;padding:18px 24px;border:0;border-radius:24px;background:#070a0e;box-shadow:0 32px 90px rgba(0,0,0,.66),inset 0 1px 0 rgba(255,255,255,.07);text-align:left}
  .bypass-section dl div{padding:14px 0;border-color:rgba(255,255,255,.07)}

  @media(max-width:900px){.apps-section .feature-ledger{grid-template-columns:1fr 1fr}.bypass-section{width:min(calc(100% - 32px),720px);min-height:820px;padding-top:112px}.bypass-well{width:100vw}}
  @media(max-width:620px){.hero-visual{width:calc(100vw - 24px);padding-right:14px;padding-left:14px}.hero-stage{padding:5px 5px 0}.hero-stage>picture{border-radius:16px 16px 0 0}.apps-section .feature-ledger{grid-template-columns:1fr}.apps-proof{min-height:650px;margin-top:82px}.app-copy h3{font-size:37px}.device-list{gap:18px 20px}.phone-well{min-height:340px;gap:10px;padding-top:32px}.phone-well::before{height:290px}.app-phone{width:min(43vw,158px)}.app-phone-incy{margin-top:44px}.app-phone figcaption{top:9px;padding:6px 10px;font-size:8px}.bypass-section{min-height:780px;padding-top:92px}.bypass-section h2{font-size:42px}.bypass-section p{font-size:10.5px}.bypass-well{min-height:390px;padding-top:72px}.bypass-section dl{width:calc(100% - 42px);padding:16px 20px}.bypass-section dl div{align-items:flex-start;gap:16px}.bypass-section dd{max-width:145px}}

  /* Complete lower-page composition. */
  .apps-section{padding-bottom:80px}
  .apps-proof{min-height:760px;margin-top:72px;justify-content:flex-start}
  .app-copy .section-chip{margin-bottom:0}
  .app-copy h3{max-width:690px;margin-top:26px;font-size:clamp(42px,4.8vw,68px)}
  .app-copy>p{max-width:590px}
  .device-list{gap:30px;margin-top:34px}
  .app-icon-stage{position:relative;width:100vw;min-height:450px;display:flex;align-items:center;justify-content:center;gap:36px;isolation:isolate;margin-top:34px;overflow:hidden}
  .app-icon-stage::before{content:'';position:absolute;z-index:-2;top:50%;left:50%;width:100vw;height:300px;background:linear-gradient(180deg,transparent 5%,rgba(7,15,23,.25) 25%,rgba(81,174,230,.16) 44%,rgba(189,231,255,.62) 49%,rgba(84,174,228,.3) 55%,rgba(8,25,39,.16) 72%,transparent 96%),radial-gradient(ellipse 58% 48% at 50% 50%,rgba(126,211,255,.68),rgba(48,140,199,.3) 42%,transparent 74%);filter:blur(16px);transform:translate(-50%,-50%)}
  .app-icon-stage::after{content:'';position:absolute;z-index:-1;top:50%;left:50%;width:100vw;height:190px;background:radial-gradient(ellipse 62% 28% at 50% 50%,rgba(205,239,255,.35),rgba(73,164,216,.14) 46%,transparent 76%);filter:blur(38px);transform:translate(-50%,-50%)}
  .app-icon-object{position:relative;width:210px;height:230px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:18px;border:1px solid rgba(224,241,250,.2);border-radius:42px;background:linear-gradient(145deg,rgba(43,58,69,.72),rgba(5,8,12,.9) 64%);box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 38px 90px rgba(0,0,0,.68);backdrop-filter:blur(24px)}
  .app-icon-object:nth-child(2){margin-top:86px}
  .app-icon-object i{width:104px;height:104px;display:grid;place-items:center;border:1px solid rgba(255,255,255,.2);border-radius:30px;background:linear-gradient(145deg,#f3f6f8,#77838c);box-shadow:0 16px 44px rgba(0,0,0,.38),inset 0 1px 0 #fff;color:#080b0e;font-size:44px;font-style:normal;font-weight:900;letter-spacing:-.08em}
  .app-icon-object b{font-size:13px;letter-spacing:.04em}
  .app-icon-incy i{background:linear-gradient(145deg,#14191e,#030507);color:#edf4f7;letter-spacing:-.1em}

  .bypass-section{min-height:940px;padding-top:145px}
  .bypass-copy{position:relative;z-index:3}
  .bypass-well{min-height:470px;margin-top:42px;padding-top:102px}
  .bypass-well::before{inset:-25% -12%;background:radial-gradient(ellipse 41% 32% at 9% 14%,rgba(140,214,252,.82),rgba(49,150,208,.31) 44%,transparent 72%),radial-gradient(ellipse 48% 25% at 51% 49%,rgba(207,239,255,.72),rgba(61,162,218,.24) 44%,transparent 75%),radial-gradient(ellipse 39% 34% at 91% 84%,rgba(119,204,248,.8),rgba(39,135,193,.27) 46%,transparent 75%);filter:blur(29px);transform:rotate(4deg)}
  .bypass-well::after{top:48%;width:118vw;height:290px;background:linear-gradient(165deg,transparent 12%,rgba(194,234,255,.18) 37%,rgba(74,172,225,.12) 52%,transparent 76%);filter:blur(48px);transform:translate(-50%,-50%) skewY(3deg)}
  .bypass-section dl{width:min(calc(100% - 32px),560px);padding:22px 30px;border:1px solid rgba(255,255,255,.14);border-radius:28px;background:rgba(5,8,11,.78);backdrop-filter:blur(28px)}

  .pricing-section{width:min(calc(100% - 48px),1120px);padding:150px 0}
  .pricing-section::before{display:none}
  .pricing-intro{align-items:center;flex-direction:column;gap:20px;text-align:center}
  .pricing-intro h2{max-width:800px;font-size:clamp(46px,5vw,70px)}
  .pricing-intro p{max-width:620px}
  .periods{margin:42px auto 38px;background:#07090c;box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}
  .tariff-grid{gap:12px}
  .tariff-grid article,.tariff-grid article.recommended{padding:0;overflow:hidden;border:1px solid rgba(255,255,255,.1);border-radius:22px;background:#07080a;box-shadow:none;transform:none}
  .tariff-grid article:hover,.tariff-grid article.recommended:hover{border-color:rgba(255,255,255,.22);transform:translateY(-4px)}
  .tariff-top{min-height:248px;padding:30px 28px;border-radius:0!important;background:linear-gradient(155deg,#12151a,#080a0d)!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.055)!important}
  .tariff-grid article.recommended .tariff-top{background:radial-gradient(circle at 86% 6%,rgba(118,202,246,.23),transparent 42%),linear-gradient(155deg,#182630,#090d11)!important}
  .tariff-grid ul{margin:0;padding:25px 28px 24px}
  .tariff-grid article>button{margin:0 20px 20px;border-radius:14px}
  .custom-builder{grid-template-columns:.72fr 1.2fr .74fr;gap:34px;margin-top:22px;padding:34px;border:1px solid rgba(255,255,255,.1);border-radius:22px;background:radial-gradient(circle at 88% 18%,rgba(71,157,210,.18),transparent 33%),#07090c;box-shadow:none}
  .custom-total{border-radius:17px}

  .cabinet-section{padding:150px 0 130px}
  .cabinet-section::before{display:none}
  .cabinet-section .split-intro{align-items:center;grid-template-columns:1fr;text-align:center}
  .cabinet-section .split-intro h2{font-size:clamp(48px,5.2vw,72px)}
  .cabinet-section .split-intro p{max-width:620px;margin:auto}
  .cabinet-proof{min-height:670px;margin-top:56px;padding:0 78px 50px;background:radial-gradient(ellipse 58% 42% at 50% 62%,rgba(54,151,210,.18),transparent 72%)}
  .cabinet-proof figure{border:0;background:transparent;box-shadow:0 45px 110px -54px #000}
  .cabinet-desktop-shot{width:100%;border-radius:24px}
  .cabinet-mobile-shot{right:28px;bottom:0;width:215px;padding:5px;border:1px solid rgba(255,255,255,.18)!important;background:rgba(9,13,18,.68)!important;backdrop-filter:blur(18px)}

  .connection-section{padding:130px 0}
  .connection-section::before{display:none}
  .connection-section .intro{max-width:820px;margin:auto;text-align:center}
  .connection-section .intro h2{font-size:clamp(44px,4.8vw,66px)}
  .connection-section ol{gap:10px;margin-top:58px;border:0}
  .connection-section li,.connection-section li+li{min-height:190px;padding:24px;border:1px solid rgba(255,255,255,.09);border-radius:18px;background:linear-gradient(155deg,#0c0e12,#060709);box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
  .connection-section li>span{width:34px;height:34px;display:grid;place-items:center;border-radius:50%;color:#061018;background:#a8ddf8}

  .faq-section{gap:70px;padding:140px 0}
  .faq-section::before{display:none}
  .faq-section .intro h2{font-size:clamp(42px,4.7vw,64px)}
  .faq-list{border-top-color:rgba(255,255,255,.16)}
  .faq-list article{border-bottom-color:rgba(255,255,255,.12)}
  .faq-list button{min-height:94px}
  .faq-list button i{width:34px;height:34px;display:grid;place-items:center;border:1px solid rgba(255,255,255,.12);border-radius:50%}

  .final-section{width:100%;min-height:720px;margin:20px auto 0;border:0}
  .final-section::after{background:linear-gradient(180deg,#000 0%,rgba(0,0,0,.32) 32%,rgba(0,0,0,.6) 70%,#000 100%)}
  .final-section>img{opacity:.78;transform:scale(1.08)}
  .final-section h2{font-size:clamp(54px,6vw,82px)}
  .links-section{width:min(calc(100% - 48px),1080px);grid-template-columns:.75fr 1.25fr;gap:90px;padding:120px 0 110px}
  .links-section::before{display:block;top:auto;bottom:-170px;left:-10%;width:65%;height:420px;background:radial-gradient(ellipse,rgba(54,154,214,.28),transparent 70%);filter:blur(70px);transform:none}
  .links-section nav a{padding:0 10px;border-color:rgba(255,255,255,.1)}
  .footer{position:relative;width:100%;min-height:190px;padding:55px max(32px,calc((100vw - 1080px)/2));border-top:1px solid rgba(255,255,255,.09);background:#000}

  @media(max-width:900px){.app-icon-stage{min-height:410px}.pricing-section{width:min(calc(100% - 32px),720px)}.custom-builder{grid-template-columns:1fr}.cabinet-proof{min-height:500px;padding:0 55px 40px}.connection-section ol{grid-template-columns:1fr 1fr}.faq-section,.links-section{grid-template-columns:1fr}.links-section{width:min(calc(100% - 32px),720px)}}
  @media(max-width:620px){.apps-proof{min-height:620px}.app-copy .section-chip{display:inline-flex}.app-icon-stage{min-height:320px;gap:12px;margin-top:25px}.app-icon-stage::before{height:300px}.app-icon-object{width:140px;height:160px;gap:11px;border-radius:28px}.app-icon-object:nth-child(2){margin-top:52px}.app-icon-object i{width:70px;height:70px;border-radius:21px;font-size:30px}.pricing-section{padding:105px 0}.pricing-intro h2{font-size:42px}.periods{max-width:100%;overflow-x:auto}.tariff-grid{gap:12px}.tariff-top{min-height:220px}.custom-builder{padding:20px}.cabinet-section{padding:105px 0}.cabinet-proof{min-height:0;padding:0}.cabinet-mobile-shot{right:auto;width:min(62%,220px);justify-self:end}.connection-section{padding:95px 0}.connection-section ol{grid-template-columns:1fr;gap:9px}.connection-section li,.connection-section li+li{min-height:150px}.faq-section{padding:100px 0}.final-section{min-height:620px}.final-section h2{font-size:44px;line-height:.94}.links-section{gap:48px;padding:95px 0}.footer{padding:42px 20px}}

  /* Owner-approved Nexio composition, scoped below the unchanged trial section. */
  .apps-section{width:min(calc(100% - 48px),1120px);padding:164px 0 150px}
  .apps-intro h2{max-width:820px;font-size:clamp(48px,5.2vw,72px);font-weight:620;letter-spacing:-.06em}
  .apps-intro p{max-width:570px;font-size:12px}
  .apps-section .feature-ledger{grid-template-columns:repeat(12,1fr);gap:14px;width:100%;margin-top:68px}
  .apps-section .feature-ledger article{position:relative;min-height:230px;display:flex;justify-content:flex-end;flex-direction:column;overflow:hidden;padding:34px;border-radius:26px;background:radial-gradient(circle at 85% 5%,rgba(103,193,240,.13),transparent 42%),linear-gradient(145deg,#101317,#07090c 72%)}
  .apps-section .feature-ledger article::before{content:'';position:absolute;top:28px;right:28px;width:42px;height:42px;border:1px solid rgba(255,255,255,.12);border-radius:50%;box-shadow:inset 0 0 0 10px rgba(255,255,255,.018),0 0 36px rgba(99,190,239,.08)}
  .apps-section .feature-ledger article:nth-child(1),.apps-section .feature-ledger article:nth-child(4){grid-column:span 7}
  .apps-section .feature-ledger article:nth-child(2),.apps-section .feature-ledger article:nth-child(3){grid-column:span 5}
  .apps-section .feature-ledger article:nth-child(2),.apps-section .feature-ledger article:nth-child(4){background:radial-gradient(circle at 12% 100%,rgba(78,169,222,.13),transparent 40%),linear-gradient(145deg,#0d1014,#060709 72%)}
  .apps-section .feature-ledger h3{max-width:360px;font-size:22px;letter-spacing:-.025em}
  .apps-section .feature-ledger p{max-width:460px;margin-top:12px;font-size:11px}

  .apps-proof{min-height:610px;display:grid;grid-template-columns:.86fr 1.14fr;align-items:stretch;margin-top:110px;overflow:hidden;border:1px solid rgba(255,255,255,.1);border-radius:32px;background:linear-gradient(145deg,#0b0d11,#050608);box-shadow:0 55px 140px -95px rgba(92,190,244,.62)}
  .app-copy{align-items:flex-start;justify-content:center;width:auto;padding:64px;text-align:left}
  .app-copy h3{max-width:470px;margin-top:24px;font-size:clamp(42px,4.4vw,62px)}
  .app-copy>p{max-width:440px;margin:20px 0 0;font-size:11.5px}
  .device-list{justify-content:flex-start;gap:22px 26px;margin-top:34px}
  .app-icon-stage{width:auto;min-height:610px;align-self:stretch;gap:24px;margin:0;overflow:hidden;background:radial-gradient(ellipse 88% 62% at 100% 55%,rgba(79,177,232,.31),transparent 70%)}
  .app-icon-stage::before{top:55%;width:130%;height:390px;background:radial-gradient(ellipse 44% 58% at 18% 50%,rgba(144,218,255,.72),rgba(42,136,195,.22) 52%,transparent 78%),radial-gradient(ellipse 46% 58% at 92% 54%,rgba(125,207,250,.7),rgba(32,116,174,.18) 54%,transparent 80%);filter:blur(27px);transform:translate(-48%,-50%) rotate(-8deg)}
  .app-icon-stage::after{top:58%;width:115%;height:250px;background:linear-gradient(168deg,transparent 18%,rgba(210,241,255,.24) 45%,rgba(70,168,221,.11) 58%,transparent 78%);filter:blur(42px);transform:translate(-50%,-50%) skewY(-4deg)}
  .app-icon-object{width:190px;height:218px;border-radius:36px;background:linear-gradient(145deg,rgba(40,54,65,.78),rgba(4,7,10,.92) 65%)}
  .app-icon-object:nth-child(2){margin-top:96px}

  .bypass-section{min-height:920px;padding-top:150px}
  .bypass-section h2{font-size:clamp(48px,5vw,70px)}
  .bypass-well{margin-top:58px}
  .bypass-section dl{padding:25px 32px;border-radius:30px;background:linear-gradient(145deg,rgba(14,20,26,.88),rgba(4,7,10,.84));box-shadow:0 48px 130px rgba(0,0,0,.72),inset 0 1px 0 rgba(255,255,255,.08)}

  .pricing-section{padding:165px 0}
  .pricing-intro h2{font-size:clamp(48px,5.2vw,72px);font-weight:620;letter-spacing:-.06em}
  .tariff-grid{gap:14px}
  .tariff-grid article,.tariff-grid article.recommended{border-radius:26px;background:#060709}
  .tariff-top{min-height:265px;padding:34px 32px}
  .tariff-grid article.recommended{border-color:rgba(136,211,250,.32);box-shadow:0 42px 110px -80px rgba(89,190,244,.72)}
  .custom-builder{margin-top:18px;border-radius:26px}

  .cabinet-section{width:min(calc(100% - 48px),1120px);padding:165px 0 145px}
  .cabinet-section .split-intro{gap:18px;margin-bottom:68px}
  .cabinet-section .split-intro h2{font-size:clamp(50px,5.4vw,74px);font-weight:620;letter-spacing:-.06em}
  .cabinet-proof{position:relative;min-height:690px;overflow:hidden;padding:72px 92px 0;border-radius:34px;background:radial-gradient(ellipse 80% 58% at 50% 100%,rgba(79,175,231,.34),rgba(20,68,101,.12) 50%,transparent 78%),#050608}
  .cabinet-proof::before{content:'';position:absolute;inset:auto -15% -20% -15%;height:55%;background:radial-gradient(ellipse,rgba(166,224,253,.32),rgba(55,157,216,.13) 42%,transparent 72%);filter:blur(48px)}
  .cabinet-desktop-shot{position:relative;z-index:1}
  .cabinet-mobile-shot{z-index:2;right:34px;bottom:24px}

  .connection-section{width:min(calc(100% - 48px),1120px);padding:145px 0}
  .connection-section .intro h2{font-size:clamp(48px,5vw,70px);font-weight:620;letter-spacing:-.06em}
  .connection-section ol{position:relative;gap:14px}
  .connection-section ol::before{content:'';position:absolute;top:41px;right:9%;left:9%;height:1px;background:linear-gradient(90deg,transparent,rgba(146,213,248,.38),transparent)}
  .connection-section li,.connection-section li+li{position:relative;z-index:1;min-height:210px;padding:28px;border-radius:22px;background:linear-gradient(155deg,#0c0f13,#050608 75%)}

  .faq-section{width:min(calc(100% - 48px),1080px);grid-template-columns:.78fr 1.22fr;padding:155px 0}
  .faq-section .intro h2{font-size:clamp(46px,4.8vw,66px);font-weight:620;letter-spacing:-.055em}
  .faq-list button{min-height:100px}
  .faq-list button:hover i{border-color:rgba(137,211,249,.46);background:rgba(93,184,232,.08)}

  .final-section{min-height:760px}
  .final-section::after{background:linear-gradient(180deg,#000 0%,rgba(0,0,0,.3) 28%,rgba(0,0,0,.52) 68%,#000 100%),radial-gradient(ellipse at center,transparent 20%,rgba(0,0,0,.32) 76%)}
  .final-section h2{font-size:clamp(56px,6.2vw,86px);font-weight:620;letter-spacing:-.06em}
  .links-section{padding:135px 0 120px}

  @media(max-width:900px){
    .apps-section{width:min(calc(100% - 32px),720px);padding:128px 0}
    .apps-section .feature-ledger{grid-template-columns:1fr 1fr}
    .apps-section .feature-ledger article,.apps-section .feature-ledger article:nth-child(n){grid-column:auto;min-height:210px}
    .apps-proof{grid-template-columns:1fr;min-height:0;margin-top:88px}
    .app-copy{padding:56px 52px;text-align:center;align-items:center}
    .device-list{justify-content:center}
    .app-icon-stage{min-height:470px}
    .cabinet-section,.connection-section,.faq-section{width:min(calc(100% - 32px),720px)}
    .cabinet-proof{min-height:520px;padding:58px 58px 0}
    .faq-section{grid-template-columns:1fr;gap:54px}
  }

  @media(max-width:620px){
    .apps-section{padding:105px 0}
    .apps-intro h2{font-size:42px}
    .apps-section .feature-ledger{grid-template-columns:1fr;gap:10px;margin-top:42px}
    .apps-section .feature-ledger article,.apps-section .feature-ledger article:nth-child(n){min-height:175px;padding:26px 24px;border-radius:20px}
    .apps-section .feature-ledger article::before{top:22px;right:22px;width:34px;height:34px}
    .apps-proof{min-height:0;margin-top:72px;border-radius:24px}
    .app-copy{padding:44px 24px}
    .app-copy h3{font-size:39px}
    .device-list{gap:17px 19px}
    .app-icon-stage{min-height:340px;margin:0}
    .app-icon-object{width:136px;height:158px;border-radius:27px}
    .app-icon-object:nth-child(2){margin-top:54px}
    .bypass-section{min-height:800px;padding-top:112px}
    .bypass-section h2{font-size:42px}
    .pricing-section{padding:115px 0}
    .cabinet-section{padding:115px 0 105px}
    .cabinet-section .split-intro{margin-bottom:44px}
    .cabinet-section .split-intro h2{font-size:44px}
    .cabinet-proof{min-height:0;padding:0;border-radius:24px;background:none}
    .connection-section{padding:105px 0}
    .connection-section .intro h2{font-size:42px}
    .connection-section ol::before{display:none}
    .connection-section li,.connection-section li+li{min-height:160px}
    .faq-section{padding:110px 0}
    .final-section{min-height:650px}
    .final-section h2{font-size:46px}
  }

  /* Direct visual corrections from the owner's screenshots. */
  .app-copy h3{margin-top:0}
  .apps-intro{position:relative}
  .apps-intro::before{content:'';position:absolute;z-index:-1;top:50%;left:50%;width:min(720px,86vw);height:270px;border-radius:50%;background:radial-gradient(ellipse,rgba(54,157,216,.16),rgba(16,60,89,.06) 45%,transparent 72%);filter:blur(38px);transform:translate(-50%,-50%)}
  .app-icon-stage{position:relative;align-items:flex-end;justify-content:center;gap:0;padding:54px 20px 0}
  .app-phone{position:relative;z-index:1;flex:none;margin:0;filter:drop-shadow(0 36px 58px rgba(0,0,0,.78))}
  .app-phone-happ{z-index:1;width:215px;transform:translate(42px,38px) rotate(-2.2deg)}
  .app-phone-incy{z-index:2;width:276px;transform:translateX(-28px) rotate(1.2deg)}
  .app-phone img{display:block;width:100%;height:auto}

  .bypass-well{overflow:hidden;background:#000}
  .bypass-well::before{inset:-8% -3%;width:106%;height:116%;background:radial-gradient(ellipse 39% 58% at -4% 54%,rgba(191,235,255,.98) 0%,rgba(93,192,241,.72) 20%,rgba(35,127,183,.34) 43%,transparent 73%),radial-gradient(ellipse 39% 58% at 104% 54%,rgba(191,235,255,.98) 0%,rgba(93,192,241,.72) 20%,rgba(35,127,183,.34) 43%,transparent 73%),radial-gradient(ellipse 78% 35% at 50% 56%,rgba(154,216,248,.42),rgba(55,153,207,.2) 38%,rgba(8,34,52,.05) 68%,transparent 84%);filter:blur(31px);transform:none}
  .bypass-well::after{top:57%;width:126vw;height:430px;background:linear-gradient(166deg,transparent 16%,rgba(110,200,245,.07) 31%,rgba(220,244,255,.3) 47%,rgba(71,169,222,.13) 58%,transparent 78%);filter:blur(48px);transform:translate(-50%,-50%) skewY(-2deg)}
  .bypass-section dl{box-shadow:0 54px 140px rgba(0,0,0,.78),inset 0 1px 0 rgba(255,255,255,.08),0 0 100px rgba(79,178,231,.11)}

  @media(max-width:900px){
    .app-icon-stage{padding:46px 32px 0}
    .app-phone-happ{width:205px;transform:translate(36px,34px) rotate(-2deg)}
    .app-phone-incy{width:262px;transform:translateX(-25px) rotate(1deg)}
  }

  @media(max-width:620px){
    .app-icon-stage{align-items:flex-end;gap:4px;padding:35px 10px 0}
    .app-phone-happ{width:min(44vw,172px);transform:translate(27px,25px) rotate(-2deg)}
    .app-phone-incy{width:min(55vw,215px);margin:0;transform:translateX(-20px) rotate(1deg)}
    .bypass-well::before{inset:-10% -8%;width:116%;height:120%;background:radial-gradient(ellipse 67% 54% at -18% 55%,rgba(188,233,255,.94),rgba(73,172,226,.5) 35%,transparent 72%),radial-gradient(ellipse 67% 54% at 118% 55%,rgba(188,233,255,.94),rgba(73,172,226,.5) 35%,transparent 72%),radial-gradient(ellipse 96% 31% at 50% 57%,rgba(158,216,246,.34),rgba(44,139,194,.14) 44%,transparent 82%)}
  }

  /* Keep the app proof neutral: the phones are the visual focus, not another light field. */
  .apps-proof{box-shadow:none}
  .app-icon-stage{background:#050608}
  .app-icon-stage::before,.app-icon-stage::after{display:none}

  .app-phone-incy{top:4px}
  .landing-nav:not(.compact){border-color:transparent;border-radius:0;background:transparent;box-shadow:none;backdrop-filter:none}
  .landing-nav.compact{border-color:rgba(255,255,255,.1);border-radius:999px;box-shadow:0 20px 70px rgba(0,0,0,.3);backdrop-filter:blur(22px)}

  /* Focused light sources for bypass proof: no full-width grey fog. */
  .bypass-well::before{inset:12% -2%;width:104%;height:76%;background:radial-gradient(ellipse 31% 54% at -4% 55%,rgba(128,211,255,.92) 0%,rgba(31,143,205,.54) 23%,rgba(7,63,101,.2) 48%,transparent 73%),radial-gradient(ellipse 31% 54% at 104% 55%,rgba(128,211,255,.92) 0%,rgba(31,143,205,.54) 23%,rgba(7,63,101,.2) 48%,transparent 73%);filter:blur(25px);transform:none}
  .bypass-well::after{display:none}
  .bypass-section dl{box-shadow:0 48px 120px rgba(0,0,0,.82),inset 0 1px 0 rgba(255,255,255,.08)}

  @media(min-width:720px) and (max-width:900px){
    .tariff-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}
    .tariff-top{min-height:190px;padding:22px 18px}
    .tariff-grid header{gap:8px}.tariff-grid header span{font-size:12px}.tariff-grid header em{padding:5px 7px;font-size:7px}
    .tariff-grid .tariff-top>p{min-height:48px;margin:13px 0 17px;font-size:9px}
    .plan-price b{font-size:36px}.plan-price{gap:5px}
    .tariff-grid ul{gap:11px;margin:0;padding:18px 18px 16px}.tariff-grid li{gap:7px;font-size:9px}
    .tariff-grid article>button{min-height:44px;margin:0 12px 12px}
  }

  @media(max-width:620px){
    .bypass-well::before{inset:15% -8%;width:116%;height:70%;background:radial-gradient(ellipse 47% 50% at -13% 55%,rgba(120,207,253,.88),rgba(27,135,197,.44) 30%,rgba(7,54,87,.14) 52%,transparent 76%),radial-gradient(ellipse 47% 50% at 113% 55%,rgba(120,207,253,.88),rgba(27,135,197,.44) 30%,rgba(7,54,87,.14) 52%,transparent 76%)}
  }

  /* Approved hierarchy and pacing pass. */
  .hero{min-height:100svh;align-content:start;padding:104px 20px 0}
  .hero-copy{transform:none}
  .hero-visual{width:min(1040px,calc(100vw - 32px));margin-top:28px;padding:38px 70px 0}
  .hero-stage{width:min(820px,100%)}

  .apps-section{padding-top:112px;padding-bottom:108px}
  .apps-intro{align-items:center;text-align:center}
  .apps-intro::before{left:50%;width:min(620px,72vw);transform:translate(-50%,-50%)}
  .apps-section .feature-ledger{grid-template-columns:minmax(0,1.35fr) minmax(260px,.65fr);grid-template-rows:repeat(3,minmax(112px,auto));gap:12px;margin-top:52px}
  .apps-section .feature-ledger article,.apps-section .feature-ledger article:nth-child(n){grid-column:2;min-height:0;display:flex;align-items:center;justify-content:space-between;flex-direction:row;gap:24px;padding:24px 28px;border-radius:22px;background:#080a0d}
  .apps-section .feature-ledger article.feature-primary{grid-column:1;grid-row:1 / 4;align-items:flex-start;justify-content:flex-end;flex-direction:column;min-height:360px;padding:38px;background:radial-gradient(circle at 68% 28%,rgba(80,174,226,.18),transparent 35%),linear-gradient(145deg,#10151a,#06080a 72%)}
  .apps-section .feature-ledger article::before{display:none}
  .apps-section .feature-ledger h3{font-size:20px}.apps-section .feature-ledger article.feature-primary h3{font-size:32px}
  .apps-section .feature-ledger p{margin-top:8px}
  .feature-index{align-self:flex-start;color:#63717d;font-size:10px;font-weight:800;letter-spacing:.16em}
  .route-orbit{position:absolute;top:38px;right:38px;left:38px;height:185px;border:1px solid rgba(144,213,249,.14);border-radius:999px;transform:rotate(-8deg)}
  .route-orbit::before,.route-orbit::after,.route-orbit i,.route-orbit b{content:'';position:absolute;width:12px;height:12px;border:1px solid rgba(160,222,253,.38);border-radius:50%;background:#0c1820;box-shadow:0 0 24px rgba(75,179,232,.3)}
  .route-orbit::before{top:22%;left:9%}.route-orbit::after{right:12%;bottom:16%}.route-orbit i:nth-child(1){top:5%;left:55%}.route-orbit i:nth-child(2){right:30%;bottom:3%}.route-orbit i:nth-child(3){bottom:18%;left:22%}
  .route-orbit b{top:50%;left:50%;width:42px;height:42px;border-color:rgba(177,226,250,.42);background:#0b1720;box-shadow:inset 0 0 0 10px rgba(103,195,241,.06),0 0 44px rgba(76,180,232,.22);transform:translate(-50%,-50%)}
  .apps-proof{margin-top:76px}
  .bypass-section{min-height:820px;padding-top:122px}
  .pricing-section{padding:128px 0}
  .connection-section{padding:112px 0}.faq-section{padding:120px 0}.links-section{padding:110px 0 96px}

  .tariff-grid article,.tariff-grid article.recommended{height:100%;transform:none}
  .tariff-grid article:hover,.tariff-grid article.recommended:hover{transform:translateY(-3px)}

  .final-section{isolation:isolate;min-height:700px;overflow:hidden;background:#000}
  .final-section>div:not(.arc-horizon){position:relative;z-index:2}
  .arc-horizon{position:absolute!important;z-index:0!important;inset:0;overflow:hidden;background:#000}
  .arc-horizon::before,.arc-horizon::after{content:'';position:absolute;border-radius:50%;background:radial-gradient(ellipse at 58% 28%,rgba(17,58,80,.88),rgba(4,13,20,.92) 38%,#010204 68%);box-shadow:0 -1px 0 rgba(118,205,248,.45),0 -20px 70px rgba(42,147,204,.13)}
  .arc-horizon::before{right:-18%;bottom:-46%;width:94%;height:104%;transform:rotate(-16deg)}
  .arc-horizon::after{bottom:-62%;left:-26%;width:92%;height:92%;opacity:.72;transform:rotate(13deg)}
  .final-section::after{z-index:1;background:radial-gradient(ellipse at center,rgba(0,0,0,.08),rgba(0,0,0,.58) 72%),linear-gradient(180deg,#000 0%,transparent 24%,rgba(0,0,0,.2) 68%,#000 100%)}

  @media(min-width:901px) and (max-height:900px){
    .hero{padding-top:94px}.hero h1{font-size:clamp(48px,4.6vw,64px)}.landing .hero-text{margin-top:18px}.hero-actions{margin-top:19px}
    .hero-visual{margin-top:22px;padding-top:24px}.hero-stage{width:min(710px,100%)}
  }

  @media(min-width:901px) and (max-height:800px){
    .hero{padding-top:88px}.hero h1{font-size:clamp(46px,4.3vw,59px)}
    .hero-visual{margin-top:18px;padding-top:18px}.hero-stage{width:min(650px,100%)}
  }

  @media(max-width:900px){
    .hero{min-height:100svh;padding-top:96px}.hero-visual{width:calc(100vw - 20px);margin-top:26px;padding:30px 38px 0}.hero-stage{width:min(680px,100%);border-width:7px}
    .apps-intro{align-items:center;text-align:center}.apps-intro::before{left:50%;transform:translate(-50%,-50%)}
    .apps-section .feature-ledger{grid-template-columns:1.1fr .9fr;grid-template-rows:repeat(3,minmax(104px,auto))}
    .apps-section .feature-ledger article.feature-primary{min-height:330px;padding:30px}.apps-section .feature-ledger article,.apps-section .feature-ledger article:nth-child(n){padding:20px 22px}
    .route-orbit{top:30px;right:30px;left:30px;height:158px}
  }

  @media(min-width:720px) and (max-width:900px){.tariff-grid article:hover,.tariff-grid article.recommended:hover{transform:none}}

  @media(max-width:620px){
    .landing-nav{width:calc(100vw - 24px);gap:10px;padding-left:13px}.brand{gap:7px}.brand b{font-size:14px}.nav-cta{min-height:44px;padding:0 14px;font-size:9.5px}
    .hero{min-width:0;display:block;overflow:hidden;padding:92px 12px 0}.hero-copy{min-width:0;width:100%;margin:0 auto}.hero h1{width:100%;font-size:34px}.hero h1 span{display:block;max-width:100%;white-space:nowrap}.landing .hero-text{max-width:330px;margin:18px auto 0}.hero-actions{margin-top:20px}
    .hero-visual{width:calc(100vw - 12px);margin:22px auto 0;padding:22px 12px 0}.hero-stage{width:min(300px,80vw,calc((100svh - 360px)*.623));min-width:188px;aspect-ratio:568/912;margin:0 auto;border-width:5px}
    .apps-section{padding-top:92px;padding-bottom:88px}.apps-section .feature-ledger{grid-template-columns:1fr;grid-template-rows:auto;gap:10px;margin-top:38px}
    .apps-section .feature-ledger article,.apps-section .feature-ledger article:nth-child(n),.apps-section .feature-ledger article.feature-primary{grid-column:1;grid-row:auto;min-height:126px;padding:23px 22px}
    .apps-section .feature-ledger article.feature-primary{min-height:300px}.route-orbit{top:24px;right:24px;left:24px;height:145px}
    .apps-section .feature-ledger h3,.apps-section .feature-ledger article.feature-primary h3{font-size:21px}
    .apps-proof{margin-top:60px}.bypass-section{padding-top:96px}.pricing-section{padding:104px 0}.connection-section,.faq-section{padding:96px 0}
    .final-section{min-height:610px}.arc-horizon::before{right:-58%;bottom:-34%;width:150%;height:86%}.arc-horizon::after{bottom:-58%;left:-62%;width:142%;height:78%}
  }
  /* Pricing: calm comparison cards with one deliberate Standard accent. */
  .pricing-section{width:min(calc(100% - 48px),1200px);padding:150px 0 140px}
  .pricing-intro h2{max-width:760px;font-size:clamp(46px,4.8vw,68px)}
  .pricing-intro p{max-width:590px;color:#7f858d}
  .periods{margin:38px auto 32px;padding:4px;border-color:rgba(255,255,255,.09);background:#111216}
  .periods button{min-width:88px;min-height:38px;color:#858a92}
  .periods button.active{color:#f5f7f8;background:#35373d;box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}
  .tariff-grid{align-items:stretch;gap:12px}
  .tariff-grid article,.tariff-grid article.recommended{min-height:0;padding:0;border-color:rgba(255,255,255,.09);border-radius:22px;background:linear-gradient(155deg,#111216,#090a0d 72%);box-shadow:inset 0 1px 0 rgba(255,255,255,.025);transform:none}
  .tariff-grid article.recommended{overflow:hidden;border-color:rgba(255,255,255,.09);background:radial-gradient(ellipse 140% 78% at 50% 118%,var(--accent-glow) 0,rgba(45,159,211,.56) 36%,rgba(19,83,116,.24) 62%,transparent 84%),linear-gradient(155deg,#111216,#090a0d 72%);box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}
  .tariff-top,.tariff-grid article.recommended .tariff-top{min-height:250px;padding:30px 28px;border-radius:0!important;background:transparent!important;box-shadow:none!important}
  .tariff-grid header span{font-size:13px;font-weight:780;letter-spacing:.08em}
  .tariff-grid header em{border-color:rgba(137,215,255,.28);background:rgba(102,196,244,.08)}
  .tariff-grid .tariff-top>p{margin:17px 0 27px;color:#a1a7af;font-size:12.5px}
  .plan-price b{font-size:44px;font-weight:560}
  .tariff-grid ul{flex:1;margin:0;padding:25px 28px 22px;border-top:0}
  .tariff-grid li{align-items:center;color:#b8bdc5;font-size:12px}
  .tariff-grid li::before{content:none}
  .tariff-grid li :global(.arc-icon){width:20px;height:20px;color:inherit}
  .tariff-grid article.recommended li{color:#eef9ff}
  .tariff-grid article>button,.tariff-grid article.recommended>button{min-height:48px;margin:0 20px 20px;border-color:rgba(255,255,255,.12);border-radius:999px;color:#f2f4f6;background:#27292e}
  .tariff-grid article.recommended>button{border-color:rgba(255,255,255,.7);color:#071018;background:#f5fbfe}
  .custom-builder{grid-template-columns:.78fr 1.25fr .67fr;align-items:stretch;gap:48px;margin-top:12px;padding:36px 38px;border-color:rgba(255,255,255,.09);border-radius:22px;background:linear-gradient(155deg,#111216,#090a0d 72%);box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}
  .custom-heading{align-self:center}.custom-heading h3{font-size:34px}.custom-heading p{max-width:300px;color:#9ba1aa;font-size:12px}
  .custom-controls{align-content:center;gap:0}.custom-controls label{min-height:56px;grid-template-columns:105px minmax(0,1fr);gap:18px;border-bottom:1px solid rgba(255,255,255,.07)}.custom-controls label:first-child{border-top:1px solid rgba(255,255,255,.07)}.custom-controls label>span{color:#aeb4bc;font-size:11px}.custom-controls label>div{padding:2px;border:0;border-radius:10px;background:#090b0e}.custom-controls button{min-height:34px;color:#8f969f;font-size:10px}.custom-controls button:hover{color:var(--accent)}.custom-controls button.active{color:var(--accent-ink);background:var(--accent)}.custom-controls input{accent-color:var(--accent)}.custom-total{min-height:216px;padding:24px;border-color:var(--accent-soft);border-radius:18px;background:linear-gradient(155deg,#15191e,#0b0d10)}.custom-total .custom-label{color:#aab0b8;font-size:9px}.custom-total>span{color:#969da6;font-size:9.5px}.custom-total>b{margin-top:18px;font-size:42px}.custom-total>small:not(.custom-label){color:#a3aab3;font-size:9px}.custom-total>a{width:100%;min-height:46px;justify-content:center;margin-top:28px;border-radius:999px;color:var(--accent-ink);background:var(--accent);font-size:11px}.custom-total>a:hover{background:var(--accent-hover)}
  @media(hover:hover) and (min-width:901px){.tariff-grid article:hover{border-color:rgba(151,214,247,.25);transform:translateY(-4px)}.tariff-grid article.recommended:hover{border-color:rgba(255,255,255,.09)}}
  @media(max-width:900px){.pricing-section{width:min(calc(100% - 32px),760px);padding:115px 0}.tariff-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.tariff-grid article,.tariff-grid article.recommended,.tariff-grid article:hover,.tariff-grid article.recommended:hover{min-height:430px;transform:none}.tariff-top,.tariff-grid article.recommended .tariff-top{min-height:205px;padding:24px 18px}.tariff-grid header{align-items:flex-start;flex-direction:column;gap:9px}.tariff-grid .tariff-top>p{min-height:48px;margin:13px 0 20px}.plan-price{align-items:flex-start;flex-direction:column;gap:5px}.plan-price b{font-size:34px}.tariff-grid ul{padding:20px 18px 18px}.tariff-grid article>button,.tariff-grid article.recommended>button{margin:0 14px 14px}.custom-builder{grid-template-columns:1fr;gap:24px;padding:26px}.custom-heading p{max-width:520px}.custom-total{min-height:190px}}
  @media(max-width:620px){.pricing-section{padding:100px 0}.pricing-intro h2{font-size:42px}.periods{width:100%;margin:30px auto 24px}.periods button{min-width:72px}.tariff-grid{grid-template-columns:1fr}.tariff-grid article,.tariff-grid article.recommended{min-height:0}.tariff-top,.tariff-grid article.recommended .tariff-top{min-height:215px;padding:25px 22px}.tariff-grid header{align-items:center;flex-direction:row}.plan-price{align-items:baseline;flex-direction:row}.tariff-grid .tariff-top>p{min-height:0}.tariff-grid ul{padding:22px}.custom-builder{padding:22px}}

  /* Final Hero: centered message over one continuous ArcVPN light field. */
  .hero{min-height:100svh;display:grid;place-items:center;padding:132px 24px 110px;overflow:hidden;background:radial-gradient(ellipse 92% 48% at 50% 104%,rgba(218,243,255,.92) 0,rgba(120,207,255,.74) 20%,rgba(45,159,211,.5) 48%,rgba(19,83,116,.16) 72%,transparent 86%),radial-gradient(ellipse 72% 52% at 50% 66%,rgba(66,186,242,.42),rgba(7,75,112,.2) 48%,transparent 76%),linear-gradient(180deg,#02050b 0,#06131f 42%,#073453 76%,#04131f 100%)}
  .hero::before,.hero::after{content:none}
  .hero-copy{position:relative;z-index:1;width:min(100%,960px);text-align:center;transform:translateY(5svh)}
  .hero h1{font-size:clamp(58px,7vw,102px);font-weight:560;line-height:.94;letter-spacing:-.067em;text-shadow:0 8px 46px rgba(0,12,42,.62)}
  .hero h1 span{color:#eef7ff}
  .landing .hero-text{max-width:610px;margin:30px auto 0;color:#b4c8dc;font-size:14px;line-height:1.7}
  .hero-actions{justify-content:center;margin-top:34px}
  .tariff-grid article.recommended{isolation:isolate;background:linear-gradient(155deg,#111216,#090a0d 72%)}
  .tariff-grid article.recommended::before{content:'';position:absolute;z-index:0;top:20%;right:-14%;bottom:-18%;left:-14%;border-radius:50%;background:radial-gradient(ellipse at 50% 82%,rgba(120,207,255,.86) 0,rgba(45,159,211,.58) 38%,rgba(19,83,116,.24) 62%,transparent 80%);filter:blur(18px);pointer-events:none}
  .tariff-grid article.recommended>*{position:relative;z-index:1}
  @media(max-width:900px){.hero{min-height:100svh;padding:120px 24px 96px}.hero-copy{transform:translateY(4svh)}.hero h1{font-size:clamp(56px,9vw,78px)}.landing .hero-text{max-width:560px}}
  @media(max-width:560px){.hero{min-height:100svh;padding:112px 18px 82px}.hero-copy{transform:translateY(2.5svh)}.hero h1{max-width:100%;font-size:clamp(38px,10.5vw,46px);line-height:.98}.hero h1 span{white-space:normal}.landing .hero-text{max-width:350px;margin-top:24px;font-size:11.5px;line-height:1.65}.hero-actions{margin-top:28px}}
</style>
