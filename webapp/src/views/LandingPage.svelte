<script>
  import { onMount } from 'svelte'
  import { slide } from 'svelte/transition'
  import { fetchPublicConfig } from '../lib/api.js'
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
    ['Автовыбор', 'Подходящий профиль без ручной настройки.'],
    ['Локации', 'Выбирайте страну сами.'],
    ['Обход глушилок', 'Отдельный запас для сложных сетей.'],
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
  let reducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  function reveal(node, order = 0) {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (preference.matches || !('IntersectionObserver' in window)) return {}
    node.classList.add('reveal-pending')
    node.style.setProperty('--reveal-delay', `${Math.min(order, 3) * 70}ms`)
    const show = () => {
      node.classList.remove('reveal-pending')
      node.classList.add('reveal-visible')
      observer.disconnect()
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) show()
    }, { rootMargin: '0px 0px -32px', threshold: .08 })
    const changeMotion = () => { if (preference.matches) show() }
    observer.observe(node)
    node.addEventListener('focusin', show)
    preference.addEventListener('change', changeMotion)
    return { destroy() { observer.disconnect(); node.removeEventListener('focusin', show); preference.removeEventListener('change', changeMotion) } }
  }

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
    if (import.meta.env.DEV) {
      const price = previewCustomPrice(months, devicesCount, lte)
      customQuote = price ? { price_rub:price, monthly_rub:Math.round(price/months), preview:true } : null
      quoteBusy = false
      return
    }
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
    if (import.meta.env.DEV) {
      tariffs = fallbackTariffs
      config = await fetchPublicConfig()
      return
    }
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
    document.title = 'ArcVPN (Арк ВПН) — VPN для телефона и компьютера'
    const description = document.querySelector('meta[name="description"]')
    if (description) description.content = 'ArcVPN (Арк ВПН) — VPN для iPhone, Android, Windows и Linux. Подключение через Happ и INCY, безлимитный основной трафик, тарифы и поддержка.'
    document.documentElement.classList.add('landing-document')
    loadPublicData()
    let scrollFrame
    const updateScroll = () => {
      scrolled = scrollY > 36
      const sections = [...document.querySelectorAll('[data-nav-section]')]
      const current = sections.reverse().find(section => section.getBoundingClientRect().top <= innerHeight * .35)
      activeSection = current?.id || 'subscription'
      scrollFrame = null
    }
    const handleScroll = () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateScroll) }
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const changeMotion = (event) => reducedMotion = event.matches
    motion.addEventListener('change', changeMotion)
    addEventListener('scroll', handleScroll, { passive: true })
    addEventListener('resize', handleScroll, { passive: true })
    updateScroll()
    return () => {
      removeEventListener('scroll', handleScroll)
      removeEventListener('resize', handleScroll)
      cancelAnimationFrame(scrollFrame)
      motion.removeEventListener('change', changeMotion)
      clearTimeout(quoteTimer)
      document.documentElement.classList.remove('landing-document')
    }
  })
</script>

<svelte:head>
  <meta name="theme-color" content="#030508" />
  <meta property="og:title" content="ArcVPN (Арк ВПН) — VPN для телефона и компьютера" />
  <meta property="og:description" content="VPN для iPhone, Android, Windows и Linux. Подключение через Happ и INCY, тарифы и поддержка ArcVPN." />
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
        <h1>Свободный интернет.<br /><span>От 80 ₽ в месяц.</span></h1>
        <p class="hero-text">Стабильные локации на каждый день и отдельные профили обхода глушилок — качественное подключение даже в сложных сетях.</p>
        <div class="hero-actions">
          <a class="primary" href="/app" on:click={() => track('landing_cabinet_click', { place:'hero' })}>Начать пользоваться <ArcIcon name="arrow" size={18} /></a>
        </div>
      </div>
    </section>

    <section class="story trial-story" id="subscription" data-nav-section>
      <div class="story-heading" use:reveal><h2>Попробуйте<br />на своей сети</h2><p>На сайте — 1 день бесплатно, без карты. В Telegram — 7 дней и 5 ГБ обхода.</p></div>
      <div class="trial-choices">
        <article use:reveal><div><span>Через Telegram</span><h3>Бесплатно</h3><p>Бот активирует пробную подписку для нового пользователя.</p></div>{#if config.bot_url}<a class="story-action" href={config.bot_url} target="_blank" rel="noopener" on:click={() => track('landing_trial_click', { channel:'bot' })}>Попробовать в боте <ArcIcon name="arrow" size={18} /></a>{/if}</article>
        <article use:reveal={1}><div><span>На сайте</span><h3>1 день бесплатно</h3><p>Новому email-аккаунту — без карты и автосписания. По желанию ещё 7 дней за 10 ₽, затем месячный Стандарт с автопродлением.</p></div><a class="story-action secondary-action" href="/app" on:click={() => track('landing_trial_click', { channel:'site' })}>Попробовать на сайте <ArcIcon name="arrow" size={18} /></a></article>
      </div>
    </section>

    <section class="story apps-story" id="apps" data-nav-section>
      <div class="apps-description"><div class="story-heading" use:reveal><h2>На&nbsp;телефоне<br />и&nbsp;на&nbsp;компьютере</h2><p>Happ или&nbsp;INCY. Инструкция и&nbsp;ссылка — в&nbsp;кабинете.</p></div>
        <div class="platforms" use:reveal aria-label="Поддерживаемые платформы">{#each devices as device}<span><DeviceIcon name={device.icon} size={25}/>{device.label}</span>{/each}</div>
        <dl class="profile-list">{#each featureRows as feature}<div use:reveal><dt>{feature[0]}</dt><dd>{feature[1]}</dd></div>{/each}</dl>
      </div>
      <div class="client-proof" use:reveal={1} aria-label="Приложения Happ и INCY"><figure class="phone-happ"><img src={base+'assets/arc-flow/connect-happ-phone-v2.png'} alt="Приложение Happ на телефоне" width="480" height="712" loading="lazy" decoding="async"/></figure><figure class="phone-incy"><img src={base+'assets/arc-flow/connect-incy-phone-v1.png'} alt="Приложение INCY на телефоне" width="480" height="712" loading="lazy" decoding="async"/></figure></div>
    </section>

    <section class="story bypass-story">
      <div class="story-heading" use:reveal><h2>Когда обычного<br />VPN недостаточно</h2><p>Для сложных сетей в подписке есть специальные профили обхода глушилок. Они используют отдельный запас гигабайтов.</p><a class="text-action" href="#tariffs">Выбрать тариф с обходом <ArcIcon name="arrow" size={18}/></a></div>
      <div class="traffic-explanation" use:reveal={1}><div><ArcIcon name="signal" size={25}/><span>Основной трафик<strong>Безлимит</strong><small>Автовыбор и обычные локации</small></span></div><div><ArcIcon name="lte" size={25}/><span>Трафик обхода<strong>Отдельный запас</strong><small>Объём зависит от тарифа; можно докупить</small></span></div><p><ArcIcon name="check" size={18}/>Если запас обхода закончится, обычные профили продолжат работать.</p><small class="network-note">Доступность зависит от сети, устройства и характера ограничений.</small></div>
    </section>

    <section class="story pricing-story" id="tariffs" data-nav-section>
      <div class="pricing-heading"><div class="story-heading" use:reveal><h2>Подписка под<br />ваши устройства</h2><p>Основной трафик безлимитный во всех тарифах.</p></div><div class="period-control" use:reveal={1} role="group" aria-label="Срок подписки">{#each [1,3,6,12] as month}<button class:active={selectedPeriod===month} aria-pressed={selectedPeriod===month} on:click={() => selectedPeriod=month}>{month} {month===1?'месяц':'мес.'}</button>{/each}</div></div>
      {#if periodTariffs.length}<div class="plan-comparison">{#each ['economy','standard','family'] as code, index}{@const plan=periodTariffs.find(item => item.product_code===code)}{#if plan}<article use:reveal={index} class:recommended={code==='standard'}><header><h3>{productNames[code]}</h3></header><p class="plan-audience">{productCopy[code]}</p><p class="comparison-price"><strong>{plan.monthly_rub.toLocaleString('ru-RU')} ₽</strong><span>/ месяц</span></p><p class="comparison-total">{plan.price_rub.toLocaleString('ru-RU')} ₽ за {plan.period_months} {plan.period_months===1?'месяц':plan.period_months<5?'месяца':'месяцев'}</p><ul><li><ArcIcon name="check" size={17}/>Основной трафик безлимитный</li><li><ArcIcon name="devices" size={17}/>{plan.device_limit} {plan.device_limit>=2&&plan.device_limit<=4?'устройства':'устройств'}</li><li><ArcIcon name="lte" size={17}/>{plan.lte_quota_gb?plan.lte_quota_gb+' ГБ обхода':'Без трафика обхода'}</li></ul><button class="story-action" on:click={() => selectTariff(plan)}>Выбрать {productNames[code]}</button></article>{/if}{/each}</div>
      {:else if dataError}<div class="catalog-state" role="status"><b>Тарифы временно не загрузились</b><p>Актуальные цены доступны в личном кабинете.</p><a class="text-action" href="/app">Открыть кабинет</a></div>{:else}<div class="catalog-state" role="status">Загружаем тарифы…</div>{/if}
      <details class="custom-plan" use:reveal><summary>Нужны другие параметры? <span>Собрать свой тариф <ArcIcon name="settings" size={18}/></span></summary><div class="custom-layout"><div class="custom-fields"><fieldset><legend>Срок подписки</legend><div>{#each [1,3,6,12] as month}<button class:active={customMonths===month} aria-pressed={customMonths===month} on:click={() => customMonths=month}>{month} мес.</button>{/each}</div></fieldset><label class="device-range"><span>Устройства <b>{customDevices}</b></span><input aria-label="Количество устройств" type="range" min="1" max="15" bind:value={customDevices}/></label><fieldset><legend>Трафик обхода</legend><div>{#each [0,15,30,45,75,115,175,225,500] as gb}<button class:active={customLte===gb} aria-pressed={customLte===gb} on:click={() => customLte=gb}>{gb?gb+' ГБ':'Без обхода'}</button>{/each}</div></fieldset></div><div class="custom-result" aria-live="polite"><span>{customMonths} мес. · {customDevices} устр. · {customLte} ГБ обхода</span><strong>{quoteBusy?'…':customQuote?customQuote.price_rub.toLocaleString('ru-RU')+' ₽':'Цена недоступна'}</strong>{#if customQuote?.monthly_rub}<small>{customQuote.monthly_rub.toLocaleString('ru-RU')} ₽ в месяц</small>{/if}<a class="story-action" href="/app?screen=custom-tariff" on:click={() => track('landing_custom_tariff_click')}>Создать тариф</a></div></div></details>
    </section>

    <section class="story setup-story" id="steps"><div class="story-heading" use:reveal><h2>От подписки<br />до подключения</h2><p>Всё необходимое — в личном кабинете.</p></div><ol><li use:reveal><span>1</span><h3>Выберите тариф</h3><p>Готовый вариант или свои параметры.</p></li><li use:reveal={1}><span>2</span><h3>Получите ссылку</h3><p>Она появится после активации.</p></li><li use:reveal={2}><span>3</span><h3>Установите приложение</h3><p>Подойдут Happ или INCY.</p></li><li use:reveal={3}><span>4</span><h3>Импортируйте подписку</h3><p>Выберите Автовыбор и подключитесь.</p></li></ol></section>

    <section class="story answers-story" id="faq" data-nav-section><div class="story-heading" use:reveal><h2>Перед<br />подключением</h2><p>Ответы на частые вопросы.</p>{#if config.support_url}<a class="text-action" href={config.support_url}>Написать в поддержку <ArcIcon name="arrow" size={18}/></a>{/if}</div><div class="answers-list">{#each faqs as faq,index}<article use:reveal={index}><h3><button aria-expanded={openFaq===index} aria-controls={'answer-'+index} on:click={() => {openFaq=openFaq===index?-1:index;track('landing_faq_open',{index})}}><span>{faq[0]}</span><i class:expanded={openFaq===index}><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v14M3 10h14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></i></button></h3>{#if openFaq===index}<div id={'answer-'+index} transition:slide={{duration:reducedMotion?0:220}}><p>{faq[1]}</p></div>{/if}</article>{/each}</div></section>

    <section class="story closing-story" use:reveal><img src={base+'assets/arc-flow/arc-logo.svg'} alt=""/><h2>ArcVPN готов<br />к подключению</h2><p>ArcVPN — VPN для телефона и&nbsp;компьютера.<br />Одна подписка. Управление через сайт и&nbsp;Telegram.</p><nav><a class="story-action" href="/app">Личный кабинет <ArcIcon name="arrow" size={18}/></a><a class="text-action" href="#tariffs">Посмотреть тарифы</a></nav></section>
  </main>

  <footer class="site-footer">
    <div class="footer-top">
      <nav class="footer-navigation" aria-label="Разделы сайта"><a href="#top">Главная</a><a href="#apps">Приложения</a><a href="#tariffs">Тарифы</a><a href="#faq">Вопросы</a></nav>
      <div class="footer-contact">
        <a class="footer-logo" href="#top" aria-label="ArcVPN — в начало"><img src={base+'assets/arc-flow/arc-logo.svg'} alt=""/></a>
        <nav class="footer-social" aria-label="Сообщество">{#if config.channel_url}<a href={config.channel_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click',{channel:'channel'})}>Telegram</a>{/if}{#if config.instagram_url}<a href={config.instagram_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click',{channel:'instagram'})}>Instagram</a>{/if}{#if config.tiktok_url}<a href={config.tiktok_url} target="_blank" rel="noopener" on:click={() => track('landing_social_click',{channel:'tiktok'})}>TikTok</a>{/if}</nav>
        <nav class="footer-service" aria-label="Управление и помощь"><a href="/app">Личный кабинет</a>{#if config.bot_url}<a href={config.bot_url} target="_blank" rel="noopener">Telegram-бот</a>{/if}{#if config.support_url}<a href={config.support_url}>Поддержка</a>{/if}{#if config.status_url}<a href={config.status_url}>Статус сервиса</a>{/if}</nav>
      </div>
    </div>
    <div class="footer-meta"><small>© {new Date().getFullYear()} ArcVPN</small><a href="/legal/user-agreement">Пользовательское соглашение</a></div>
    <div class="footer-wordmark" aria-hidden="true">ArcVPN</div>
  </footer>
</div>

<style>
:global(.landing-document){scroll-padding-top:105px;background:#000}
:global(body:has(.landing)){min-width:320px;overflow-x:hidden;color:#f4f7fa;background:#000;overscroll-behavior-y:auto}
.landing{--ink:#000;--carbon:#08090b;--surface:#0c0e12;--line:rgba(219,234,247,.12);--line-strong:rgba(219,234,247,.22);--snow:#f4f7fa;--steel:#8d98a7;--accent:#78cfff;--accent-hover:#a8e2ff;--accent-soft:rgba(120,207,255,.16);--accent-glow:rgba(120,207,255,.78);--accent-ink:#061018;--blue:var(--accent);--deep-blue:#06274a;width:100%;overflow:hidden;color:var(--snow);background:var(--ink);font-family:'Manrope',system-ui,sans-serif}
.landing *{box-sizing:border-box}
.landing a{color:inherit;text-decoration:none}
.landing button{border:0;color:inherit;font:inherit;cursor:pointer}
.landing h1,.landing h2,.landing h3,.landing p{margin-top:0}
.landing :is(a,button,input):focus-visible{outline:2px solid #9edcff;outline-offset:4px}
.landing-nav{position:fixed;z-index:50;top:18px;left:50%;width:min(calc(100% - 40px),1120px);height:64px;display:flex;align-items:center;gap:28px;padding:7px 9px 7px 18px;border:1px solid rgba(255,255,255,.1);border-radius:999px;background:rgba(3,5,8,.72);box-shadow:0 20px 70px rgba(0,0,0,.3);transform:translateX(-50%);backdrop-filter:blur(22px);transition:transform .24s ease,background .24s ease}
.landing-nav.compact{background:rgba(3,5,8,.92);transform:translateX(-50%) translateY(-8px)}
.brand{display:flex;align-items:center;gap:9px;flex:none}
.brand img{width:25px;height:25px}
.brand b{font-size:16px;letter-spacing:-.03em}
.desktop-nav{display:flex;justify-content:center;gap:24px;flex:1}
.desktop-nav a{position:relative;padding:12px 0;color:#7e8894;font-size:11px;font-weight:700}
.desktop-nav a:hover,.desktop-nav a.active{color:#fff}
.desktop-nav a.active::after{content:'';position:absolute;right:0;bottom:6px;left:0;height:1px;background:var(--blue)}
.nav-cta,.primary{min-height:48px;display:inline-flex;align-items:center;justify-content:center;gap:9px;padding:0 20px;border-radius:999px;color:#02070b!important;background:#f5f8fb;font-size:11px;font-weight:800;transition:transform .18s ease,background .18s ease}
.nav-cta:hover,.primary:hover{background:#cceeff}
.nav-cta:active,.primary:active{transform:scale(.98)}
.hero{position:relative;min-height:max(760px,100svh);display:grid;place-items:center;isolation:isolate;padding:132px 24px 105px;border-bottom:1px solid var(--line)}
.hero::before{content:'';position:absolute;z-index:-1;inset:0;background:radial-gradient(ellipse 48% 38% at 50% 45%,rgba(3,5,8,.62),rgba(3,5,8,.24) 62%,transparent 100%),linear-gradient(180deg,rgba(3,5,8,.24),transparent 24%,transparent 62%,#030508 98%)}
.hero-copy{width:min(100%,930px);text-align:center;transform:translateY(-1.5vh)}
.hero h1{margin:0;font-size:clamp(54px,6.25vw,94px);font-weight:700;line-height:.97;letter-spacing:-.066em;text-shadow:0 3px 28px rgba(0,0,0,.68)}
.hero h1 span{display:inline-block;color:#e3eaf0}
.hero-text{max-width:610px;margin:26px auto 0;color:#a7b1bc;font-size:14px;line-height:1.65;text-wrap:balance}
.hero-actions{display:flex;align-items:center;justify-content:center;gap:25px;margin-top:30px}
@media(max-width:900px){.landing-nav{top:12px;width:calc(100% - 24px);height:60px}
.landing-nav.compact{transform:translateX(-50%) translateY(-4px)}
.desktop-nav{display:none}
.nav-cta{margin-left:auto}
.hero{min-height:850px;padding-top:125px}
.hero h1{font-size:clamp(54px,9vw,76px)}}
@media(max-width:560px){.landing-nav{gap:12px;padding:7px 8px 7px 18px}
.landing-nav .brand{gap:7px}
.landing-nav .brand img{width:23px;height:23px}
.landing-nav .brand b{display:block;font-size:13px}
.nav-cta{min-height:42px;padding:0 13px;font-size:8.5px}
.nav-cta :global(.arc-icon){width:14px;height:14px}
.hero{min-height:800px;place-items:center;padding:125px 17px 92px}
.hero::before{background:radial-gradient(ellipse 85% 43% at 50% 44%,rgba(3,5,8,.16),rgba(3,5,8,.62) 78%),linear-gradient(180deg,rgba(3,5,8,.3),transparent 26%,rgba(3,5,8,.16) 58%,#030508 96%)}
.hero-copy{text-align:left;transform:translateY(-2vh)}
.hero h1{font-size:clamp(42px,12.2vw,48px);line-height:1;letter-spacing:-.058em}
.hero-text{max-width:350px;margin:23px 0 0;font-size:11.5px;line-height:1.62;text-wrap:pretty}
.hero-actions{align-items:flex-start;justify-content:flex-start;flex-direction:column;gap:13px;margin-top:27px}}
@media(prefers-reduced-motion:reduce){.landing *{transition:none!important}}
/* Blue-light composition shared by the hero and pricing story. */
  .hero{min-height:max(900px,100svh);display:flex;align-items:center;flex-direction:column;overflow:hidden;padding:140px 24px 0;background:#02050a}
.hero::before{z-index:-2;background:repeating-radial-gradient(ellipse 76% 62% at 50% 47%,transparent 0 95px,rgba(111,190,247,.055) 96px 97px,transparent 98px 130px),radial-gradient(ellipse 54% 42% at 50% 68%,rgba(36,145,224,.38),rgba(13,57,111,.16) 48%,transparent 73%),linear-gradient(180deg,#020409 0%,#030714 58%,#02050a 100%)}
.hero::after{content:'';position:absolute;z-index:-1;left:50%;bottom:-320px;width:min(1120px,92vw);height:620px;border-radius:50%;background:#228ed5;filter:blur(115px);opacity:.42;transform:translateX(-50%);pointer-events:none}
.hero-copy{position:relative;z-index:2;width:min(100%,850px);text-align:center;transform:none}
.hero h1{font-size:clamp(52px,5.4vw,82px);font-weight:620;line-height:.98;letter-spacing:-.064em;text-shadow:none;text-wrap:balance}
.hero-text{max-width:610px;margin:22px auto 0;color:#8d9aa8;font-size:13px}
.hero-actions{margin-top:28px}
@media(max-width:900px){.hero{min-height:850px;padding-top:128px}}
@media(max-width:560px){.hero{min-height:780px;align-items:center;padding:112px 16px 0}
.hero::before{background:repeating-radial-gradient(ellipse 120% 54% at 50% 51%,transparent 0 62px,rgba(111,190,247,.05) 63px 64px,transparent 65px 88px),radial-gradient(ellipse 90% 38% at 50% 73%,rgba(36,145,224,.36),transparent 72%),linear-gradient(180deg,#020409,#030714 62%,#02050a)}
.hero::after{bottom:-250px;width:120vw;height:500px;filter:blur(90px)}
.hero-copy{text-align:center}
.hero h1{font-size:clamp(41px,12vw,50px);line-height:.98}
.hero-text{max-width:340px;margin:19px auto 0;font-size:11px}
.hero-actions{align-items:center;justify-content:center;margin-top:24px}}
.hero-text{margin-top:38px}
.nav-cta:hover,.primary:hover{background:#e1e4e6}
@media(max-width:560px){.hero-text{margin-top:30px}}
.landing .hero-text{margin:54px auto 0}
@media(max-width:560px){.landing .hero-text{margin:40px auto 0}}
/* Hero v1: a compact product-first composition derived from the approved reference. */
  .hero{min-height:max(820px,100svh);padding-top:132px}
.hero::before{background:linear-gradient(180deg,#010204 0%,#020409 72%,#02050a 100%)}
.hero::after{bottom:-390px;width:min(1180px,94vw);height:690px;filter:blur(130px);opacity:.12}
.hero-copy{width:min(100%,780px)}
.hero h1{font-size:clamp(50px,5vw,76px);line-height:1;letter-spacing:-.058em}
.landing .hero-text{max-width:560px;margin:26px auto 0;color:#95a2ae;font-size:12px;line-height:1.6}
.hero-actions{margin-top:27px}
@media(max-width:900px){.hero{min-height:800px;padding-top:120px}}
@media(max-width:560px){.hero{min-height:735px;padding-top:106px}
.hero h1{font-size:clamp(40px,11.6vw,48px);letter-spacing:-.052em}
.landing .hero-text{max-width:330px;margin:22px auto 0;font-size:10.5px}
.hero-actions{margin-top:23px}}
/* Hero-to-trial transition and the second section stay on true black. */
  .hero{border-bottom:0;background:#000}
.hero::before{background:#000}
/* Third section: product facts first, then one focused install scene. */
.landing-nav:not(.compact){border-color:transparent;border-radius:0;background:transparent;box-shadow:none;backdrop-filter:none}
.landing-nav.compact{border-color:rgba(255,255,255,.1);border-radius:999px;box-shadow:0 20px 70px rgba(0,0,0,.3);backdrop-filter:blur(22px)}
/* Approved hierarchy and pacing pass. */
  .hero{min-height:100svh;align-content:start;padding:104px 20px 0}
.hero-copy{transform:none}
@media(min-width:901px) and (max-height:900px){.hero{padding-top:94px}
.hero h1{font-size:clamp(48px,4.6vw,64px)}
.landing .hero-text{margin-top:18px}
.hero-actions{margin-top:19px}}
@media(min-width:901px) and (max-height:800px){.hero{padding-top:88px}
.hero h1{font-size:clamp(46px,4.3vw,59px)}}
@media(max-width:900px){.hero{min-height:100svh;padding-top:96px}}
@media(max-width:620px){.landing-nav{width:calc(100vw - 24px);gap:10px;padding-left:13px}
.brand{gap:7px}
.brand b{font-size:14px}
.nav-cta{min-height:44px;padding:0 14px;font-size:9.5px}
.hero{min-width:0;display:block;overflow:hidden;padding:92px 12px 0}
.hero-copy{min-width:0;width:100%;margin:0 auto}
.hero h1{width:100%;font-size:34px}
.hero h1 span{display:block;max-width:100%;white-space:nowrap}
.landing .hero-text{max-width:330px;margin:18px auto 0}
.hero-actions{margin-top:20px}}
/* Final Hero: centered message over one continuous ArcVPN light field. */
  .hero{min-height:100svh;display:grid;place-content:center;place-items:center;padding:112px 24px 72px;overflow:hidden;background:radial-gradient(ellipse 42% 68% at -5% 38%,rgba(45,120,187,.25),transparent 72%),radial-gradient(ellipse 46% 70% at 105% 46%,rgba(107,189,233,.2),transparent 72%),radial-gradient(ellipse 46% 36% at 50% 62%,rgba(107,189,233,.11),transparent 72%),radial-gradient(ellipse 70% 40% at 50% 108%,rgba(36,93,150,.17),transparent 74%),#03070e}
.hero::before,.hero::after{content:none}
.hero-copy{position:relative;z-index:1;width:min(100%,960px);text-align:center;transform:translateY(3svh)}
.hero h1{font-size:clamp(58px,7vw,102px);font-weight:560;line-height:.94;letter-spacing:-.067em;text-shadow:0 8px 46px rgba(0,12,42,.62)}
.hero h1 span{color:#b6e7ff}
.landing .hero-text{max-width:650px;margin:30px auto 0;color:#9cafc0;font-size:14px;line-height:1.7}
.hero-actions{justify-content:center;margin-top:34px}
.hero .primary{color:#07131d!important;background:linear-gradient(125deg,#b6e7ff,#6bc0ef);box-shadow:inset 0 1px rgba(255,255,255,.58),0 18px 52px -24px rgba(91,183,235,.55)}
.hero .primary:hover{background:linear-gradient(125deg,#d5f2ff,#8fd3f5)}
@media(max-width:900px){.hero{min-height:100svh;padding:104px 24px 64px}
.hero-copy{transform:translateY(3svh)}
.hero h1{font-size:clamp(56px,9vw,78px)}
.landing .hero-text{max-width:590px}}
@media(max-width:560px){.hero{min-height:100svh;padding:96px 18px 52px}
.hero-copy{transform:translateY(2svh)}
.hero h1{max-width:100%;font-size:clamp(38px,10.5vw,46px);line-height:.98}
.hero h1 span{white-space:normal}
.landing .hero-text{max-width:360px;margin-top:24px;font-size:11.5px;line-height:1.65}
.hero-actions{margin-top:28px}}
.landing main{background:var(--cabinet-bg)}
.hero{background:radial-gradient(ellipse 48% 72% at -7% 42%,rgba(45,120,187,.33),transparent 72%),radial-gradient(ellipse 50% 74% at 107% 48%,rgba(107,189,233,.27),transparent 72%),radial-gradient(ellipse 44% 36% at 50% 62%,rgba(107,189,233,.14),transparent 72%),radial-gradient(ellipse 72% 42% at 50% 108%,rgba(36,93,150,.21),transparent 74%),var(--cabinet-bg)}
.hero .primary{border:1px solid #3c6f8f;color:#b9e2fb!important;background:rgba(7,13,23,.34);box-shadow:inset 0 1px rgba(255,255,255,.04)}
.hero .primary:hover{border-color:#8bd3fa;color:#d8f2ff!important;background:rgba(112,199,244,.07)}
@media(max-width:620px){.landing .hero-text{font-size:14px;line-height:1.6}}
.landing-nav.compact{background:#09131bad}
  :global(body:has(.landing) #app){max-width:none;overflow:visible}
  .landing{--cabinet-bg:#03070e;--ink:#03070e;--surface:#0a111b;--raised:#101a27;--snow:#f7f9fd;--steel:#adb8c7}
  .skip{position:fixed;z-index:100;top:8px;left:8px;padding:12px 18px;border-radius:999px;color:#030508!important;background:#fff;transform:translateY(-150%)}.skip:focus{transform:none}
  :global(.landing-document) { scroll-behavior:smooth; scrollbar-width:thin; scrollbar-color:#405260 #000; }
  .story { width:min(calc(100% - 64px),1120px); margin:0 auto; padding:104px 0; scroll-margin-top:0; }
  .story h2 { margin:0; font-size:clamp(36px,4.4vw,58px); font-weight:650; line-height:1.06; letter-spacing:-.05em; text-wrap:balance; }
  .story-heading > p { max-width:430px; margin:22px 0 0; color:var(--steel); font-size:16px; line-height:1.75; }
  .story-action { min-height:48px; display:inline-flex; align-items:center; justify-content:center; gap:12px; padding:0 22px; border:1px solid transparent; border-radius:999px; color:#07131c!important; background:#a7dcfa; font-size:15px; font-weight:750; transition:background .2s ease,transform .2s ease; }
  .story-action:hover { background:#d5eeff; }
  .story-action:active { transform:scale(.98); }
  .secondary-action { color:#e9f5fc!important; background:transparent; border-color:#425462; }
  .secondary-action:hover { background:#12202a; }
  .text-action { display:inline-flex; min-height:44px; align-items:center; gap:12px; color:#acdafa!important; font-size:15px; font-weight:650; }
  .text-action:hover { color:#fff!important; }
  .trial-story { display:grid; grid-template-columns:1fr 1.25fr; gap:88px; align-items:center; }
  .trial-choices article { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:30px 0; }
  .trial-choices article > div { max-width:280px; }
  .trial-choices span { color:var(--steel); font-size:15px; }
  .trial-choices h3 { margin:9px 0 12px; font-size:32px; font-weight:600; letter-spacing:-.04em; }
  .trial-choices p { margin:0; color:var(--steel); font-size:16px; line-height:1.7; }
  .trial-choices .story-action { flex:none; padding-inline:18px; font-size:15px; }
  .apps-story { display:grid; grid-template-columns:1fr 1fr; gap:68px; align-items:center; }
  .apps-description .story-heading > p { margin-top:28px; font-size:18px; color:#c4cfdf; line-height:1.7; }
  .platforms { display:flex; flex-wrap:wrap; gap:22px 26px; margin:34px 0 40px; color:#e3ebf5; }
  .platforms > span { display:flex; align-items:center; gap:10px; font-size:16px; }
  .profile-list { display:grid; gap:28px; margin:0; }
  .profile-list > div { padding:0; }
  .profile-list dt { font-size:16px; font-weight:700; }
  .profile-list dd { max-width:460px; margin:8px 0 0; font-size:16px; color:#bcc8d7; line-height:1.65; }
  .client-proof { position:relative; min-width:0; aspect-ratio:1.12; overflow:hidden; isolation:isolate; background:radial-gradient(ellipse at 56% 52%,rgba(49,127,174,.25),transparent 70%); mask-image:linear-gradient(to bottom,#000 65%,transparent 100%); -webkit-mask-image:linear-gradient(to bottom,#000 65%,transparent 100%); }
  .client-proof figure { position:absolute; margin:0; }
  .client-proof .phone-happ { z-index:1; top:37%; left:8%; width:47%; transform:rotate(-2.2deg); }
  .client-proof .phone-incy { z-index:2; top:10%; left:37%; width:60%; transform:rotate(1.2deg); }
  .client-proof img { display:block; width:100%; height:auto; filter:brightness(1.12) drop-shadow(0 0 2px rgba(162,211,239,.28)) drop-shadow(0 20px 24px #0008); }
  .bypass-story { display:grid; grid-template-columns:1fr 1fr; gap:90px; align-items:center; }
  .bypass-story .text-action { margin-top:24px; }
  .traffic-explanation { padding:12px 0 12px 32px; }
  .traffic-explanation > div { display:flex; align-items:flex-start; gap:18px; padding:22px 0; color:#91ceeF; }
  .traffic-explanation span { color:var(--steel); font-size:15px; }
  .traffic-explanation strong { display:block; margin:8px 0; color:#f1f7fc; font-size:28px; font-weight:600; letter-spacing:-.035em; }
  .traffic-explanation small { color:var(--steel); font-size:14px; line-height:1.6; }
  .traffic-explanation > p { display:flex; gap:12px; margin:18px 0 12px; color:#b5ccd9; font-size:15px; line-height:1.7; }
  .traffic-explanation > p :global(.arc-icon) { flex:none; margin-top:3px; }
  .traffic-explanation .network-note { display:block; color:var(--steel); }
  .pricing-heading { display:flex; align-items:flex-end; justify-content:space-between; gap:30px; margin-bottom:36px; }
  .period-control { display:flex; gap:3px; flex:none; padding:4px; border:1px solid var(--line); border-radius:999px; background:var(--surface); }
  .period-control button { min-height:44px; min-width:70px; padding:0 14px; border-radius:999px; color:var(--steel); background:transparent; font-size:15px; transition:color .2s,background .2s; }
  .period-control button.active { color:#07121b; background:#b1ddf7; }
  .plan-comparison { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
  .plan-comparison article { display:flex; flex-direction:column; padding:26px; border:1px solid var(--line); border-radius:24px; background:var(--surface); }
  .plan-comparison article.recommended { border-color:#477e9c; background:var(--raised); }
  .plan-comparison header { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .plan-comparison h3 { margin:0; font-size:20px; letter-spacing:-.025em; }
  .plan-audience { min-height:3.4em; margin:13px 0 28px; color:var(--steel); font-size:15px; line-height:1.7; }
  .comparison-price { display:flex; align-items:baseline; gap:9px; margin:0; }
  .comparison-price strong { font-size:42px; font-weight:600; letter-spacing:-.055em; }
  .comparison-price span { color:#a1afbb; font-size:14px; }
  .comparison-total { margin:8px 0 0; color:var(--steel); font-size:14px; }
  .plan-comparison ul { flex:1; display:grid; gap:14px; list-style:none; padding:24px 0; margin:26px 0 0; }
  .plan-comparison li { display:flex; align-items:center; gap:10px; color:#c3d1db; font-size:15px; }
  .plan-comparison li :global(.arc-icon) { color:#89c5e7; flex:none; }
  .plan-comparison .story-action { width:100%; background:#1c2d39; color:#ddecf6!important; }
  .plan-comparison .recommended .story-action { color:#07131c!important; background:#b2ddf7; }
  .plan-comparison .story-action:hover { background:#cfeaff; color:#07131c!important; }
  .catalog-state { display:grid; place-content:center; min-height:260px; color:#adbfcc; text-align:center; }
  .custom-plan { margin-top:24px; padding:0 24px; border-radius:20px; background:var(--surface); }
  .custom-plan summary { display:flex; justify-content:space-between; align-items:center; gap:18px; min-height:76px; cursor:pointer; list-style:none; color:#abb8c3; font-size:15px; }
  .custom-plan summary::-webkit-details-marker { display:none; }
  .custom-plan summary > span { display:flex; align-items:center; gap:12px; color:#c3e7fc; font-weight:650; }
  .custom-plan summary:focus-visible { outline:2px solid #9edcff; outline-offset:4px; }
  .custom-layout { display:grid; grid-template-columns:1fr 280px; gap:52px; padding:12px 0 30px; }
  .custom-fields { display:grid; gap:24px; }
  .custom-fields fieldset { min-width:0; margin:0; padding:0; border:0; }
  .custom-fields legend,.device-range > span { display:block; margin-bottom:12px; color:#c6d2dc; font-size:15px; }
  .custom-fields fieldset > div { display:flex; flex-wrap:wrap; gap:7px; }
  .custom-fields button { min-height:44px; padding:0 14px; border:1px solid #273845; border-radius:12px; background:var(--surface); color:var(--steel); font-size:15px; }
  .custom-fields button.active { background:#b2ddf7; color:#07131c; }
  .device-range { display:block; }
  .device-range > span { display:flex; justify-content:space-between; }
  .device-range input { width:100%; min-height:32px; accent-color:#a7dcfa; }
  .custom-result { display:flex; flex-direction:column; align-items:flex-start; justify-content:center; padding-left:30px; }
  .custom-result > span,.custom-result small { color:var(--steel); font-size:14px; line-height:1.65; }
  .custom-result strong { margin:16px 0 6px; font-size:40px; font-weight:600; letter-spacing:-.04em; }
  .custom-result .story-action { width:100%; margin-top:22px; }
  .setup-story ol { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:24px; margin:48px 0 0; padding:0; list-style:none; }
  .setup-story li { position:relative; }
  .setup-story li > span { width:38px; height:38px; display:grid; place-items:center; border:1px solid #446277; border-radius:50%; color:#b2def9; font-size:15px; }
  .setup-story h3 { margin:24px 0 10px; font-size:17px; letter-spacing:-.02em; }
  .setup-story li p { max-width:220px; margin:0; color:var(--steel); font-size:16px; line-height:1.7; }
  .answers-story { display:grid; grid-template-columns:.85fr 1.15fr; gap:88px; }
  .answers-story .text-action { margin-top:22px; }
  .answers-list article { padding:0 18px; margin-bottom:10px; border-radius:16px; background:var(--surface); }
  .answers-list h3 { margin:0; }
  .answers-list button { width:100%; min-height:82px; display:flex; justify-content:space-between; align-items:center; gap:20px; padding:22px 0; background:none; text-align:left; font-size:15px; font-weight:650; line-height:1.5; }
  .answers-list i { display:flex; flex:none; color:#aad9f4; transition:transform .22s ease; }
  .answers-list i.expanded { transform:rotate(45deg); }
  .answers-list p { margin:0; padding:0 30px 26px 0; color:var(--steel); font-size:16px; line-height:1.8; }
  .closing-story { padding:88px 0 104px; text-align:center; }
  .closing-story > img { width:40px; height:40px; margin-bottom:24px; }
  .closing-story > p { margin:24px 0 28px; color:var(--steel); font-size:16px; line-height:1.75; }
  .closing-story nav { display:flex; align-items:center; justify-content:center; gap:28px; }
  .site-footer { position:relative; isolation:isolate; width:100%; overflow:hidden; margin:0; padding:48px 32px 0; background:var(--ink); }
  .site-footer::before { content:''; position:absolute; z-index:-1; inset:0; background:radial-gradient(ellipse at 91% 108%,rgba(119,216,255,.82),rgba(53,133,211,.48) 24%,rgba(23,52,116,.3) 47%,transparent 74%); mask-image:linear-gradient(to bottom,transparent,#000 42%); -webkit-mask-image:linear-gradient(to bottom,transparent,#000 42%); pointer-events:none; }
  @media (min-width:601px) and (max-width:900px) { .plan-audience { min-height:5.1em; } }
  /* ArcVPN glass: near-black body, cold light edge and translucent active pill. */
  .landing .landing-nav,.landing .landing-nav:not(.compact),.landing .landing-nav.compact { border:1px solid rgba(177,221,245,.19); border-radius:999px; background:linear-gradient(115deg,rgba(198,231,249,.07),rgba(127,200,244,.025) 45%,rgba(255,255,255,.045)),rgba(3,9,15,.46); box-shadow:inset 0 1px 0 rgba(224,244,255,.14),inset 0 -1px 0 rgba(139,208,249,.035),0 12px 36px rgba(0,0,0,.24); backdrop-filter:blur(24px) saturate(1.08); -webkit-backdrop-filter:blur(24px) saturate(1.08); }
  .landing .landing-nav.compact { background:linear-gradient(115deg,rgba(198,231,249,.065),rgba(127,200,244,.02) 45%,rgba(255,255,255,.04)),rgba(3,9,15,.66); }
  .landing .desktop-nav { gap:6px; }
  .landing .desktop-nav a { padding:10px 15px; border-radius:999px; color:#b4b9c2; font-size:13px; font-weight:600; transition:color .2s ease,background .2s ease,box-shadow .2s ease; }
  .landing .desktop-nav a:hover { color:#f7f9fd; background:rgba(255,255,255,.06); }
  .landing .desktop-nav a.active { color:#f7f9fd; background:linear-gradient(130deg,rgba(180,227,255,.16),rgba(91,170,220,.08)); box-shadow:inset 0 1px 0 rgba(255,255,255,.12); }
  .landing .desktop-nav a.active::after { display:none; }
  .landing .landing-nav:not(.compact) { border-color:transparent; border-radius:0; background:transparent; box-shadow:none; backdrop-filter:none; -webkit-backdrop-filter:none; }
  .landing .landing-nav:not(.compact) .desktop-nav a.active { background:transparent; box-shadow:none; }
  .landing .landing-nav:not(.compact) .desktop-nav a.active::after { display:none; }
  .landing-nav .brand { transform:translateX(8px); }
  .landing .story-action,.landing .plan-comparison .recommended .story-action,.landing .period-control button.active,.landing .custom-fields button.active { color:#03101d!important; background:linear-gradient(128deg,#b3e4ff 0%,#72c5f4 48%,#448fcf 100%); box-shadow:inset 0 1px 0 rgba(255,255,255,.7),0 18px 44px -25px rgba(71,172,239,.9); font-weight:800; }
  .landing .period-control button,.landing .custom-fields button { font-weight:600; }
  .landing .period-control { display:grid; grid-template-columns:repeat(4,1fr); gap:4px; padding:5px; }
  .landing .period-control button { min-width:0; padding:0 12px; line-height:1; letter-spacing:0; white-space:nowrap; }
  .landing .period-control button.active,.landing .custom-fields button.active { font-weight:700; box-shadow:inset 0 1px 0 rgba(255,255,255,.7); }
  .landing .story-action:hover,.landing .period-control button.active:hover,.landing .custom-fields button.active:hover { filter:brightness(1.06); }
  .landing .plan-comparison article:not(.recommended) .story-action,.landing .story-action.secondary-action { color:#e9f5fc!important; background:#172530; border:1px solid #354652; box-shadow:none; font-weight:700; }
  .landing .plan-comparison article:not(.recommended) .story-action:hover,.landing .story-action.secondary-action:hover { background:#12202a; filter:none; }
  .closing-story { margin-bottom:72px; }
  .footer-top,.footer-meta { width:min(100%,1120px); margin-inline:auto; }
  .footer-top { display:flex; justify-content:space-between; gap:64px; }
  .footer-navigation { display:grid; align-content:start; gap:6px; }
  .footer-navigation a { display:flex; align-items:center; min-height:44px; width:fit-content; font-size:clamp(22px,2.2vw,32px); letter-spacing:-.035em; color:var(--snow); }
  .footer-contact { display:flex; flex-direction:column; align-items:flex-end; gap:14px; text-align:right; }
  .footer-logo { display:grid; place-items:center; width:44px; height:44px; }
  .footer-logo img { width:36px; height:36px; }
  .footer-social { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px 24px; }
  .footer-service { display:grid; justify-items:end; gap:2px; }
  .footer-social a,.footer-service a { display:flex; align-items:center; min-height:44px; font-size:15px; color:#c0cfdf; }
  .site-footer a:hover { color:var(--accent-hover); }
  .footer-meta { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-top:28px; }
  .footer-meta small,.footer-meta a { display:flex; align-items:center; min-height:44px; color:#b7c6d7; font-size:14px; line-height:1.5; }
  .footer-wordmark { margin:24px auto -.08em; width:fit-content; max-width:100%; font-size:clamp(88px,25vw,520px); font-weight:650; line-height:.95; letter-spacing:-.075em; color:rgba(169,219,255,.2); user-select:none; }
  .landing :global(.reveal-pending) { opacity:0; transform:translateY(22px); }
  .landing :global(.reveal-visible) { opacity:1; transform:none; transition:opacity .6s ease var(--reveal-delay,0ms),transform .7s cubic-bezier(.22,1,.36,1) var(--reveal-delay,0ms); }
  @media(max-width:1050px) {
    .story { width:calc(100% - 48px); padding:80px 0; }
    .trial-story,.apps-story,.bypass-story,.answers-story { gap:42px; }
    .trial-choices article { align-items:flex-start; flex-direction:column; gap:18px; }
    .plan-comparison { gap:10px; }
    .plan-comparison article { padding:20px; }
    .plan-comparison header { align-items:flex-start; flex-direction:column; min-height:58px; }
    .plan-comparison li { align-items:flex-start; font-size:15px; }
    .pricing-heading { align-items:flex-start; flex-direction:column; }
    .profile-list dd { font-size:16px; }
    .traffic-explanation { padding-left:22px; }
    .traffic-explanation strong { font-size:24px; }
    .setup-story ol { gap:16px; }
    .setup-story h3 { font-size:15px; }
  }
  @media(max-width:650px) {
    .story { width:calc(100% - 40px); padding:64px 0; }
    .story h2 { font-size:36px; }
    .story-heading > p { font-size:16px; margin-top:18px; }
    .trial-story,.apps-story,.bypass-story,.answers-story { grid-template-columns:1fr; gap:32px; }
    .trial-choices article { display:grid; grid-template-columns:1fr; gap:18px; padding:24px 0; }
    .trial-choices article > div { max-width:none; }
    .trial-choices .story-action { justify-self:start; }
    .apps-story { position:relative; }
    .apps-description { display:contents; }
    .apps-description .story-heading { order:0; }
    .platforms { order:1; margin:4px 0 8px; gap:18px 22px; }
    .client-proof { order:2; margin:0 -8px; }
    .profile-list { order:3; margin:8px 0 0; }
    .profile-list dd { font-size:16px; }
    .traffic-explanation { padding:0 0 0 20px; }
    .pricing-heading { margin-bottom:24px; }
    .period-control { width:100%; }
    .period-control button { min-width:0; flex:1; padding-inline:8px; }
    .plan-comparison { grid-template-columns:1fr; gap:12px; }
    .plan-comparison article { display:grid; grid-template-columns:1fr auto; gap:0 16px; padding:24px; }
    .plan-comparison header { grid-column:1/-1; flex-direction:row; align-items:center; min-height:0; }
    .plan-audience { grid-column:1/-1; min-height:0; margin:10px 0 20px; }
    .comparison-price { grid-column:1/-1; }
    .comparison-price strong { font-size:36px; }
    .comparison-total { grid-column:1/-1; }
    .plan-comparison ul { grid-column:1/-1; margin:20px 0 0; padding:20px 0; gap:12px; }
    .plan-comparison li { align-items:center; font-size:15px; }
    .plan-comparison .story-action { grid-column:1/-1; }
    .custom-plan summary { align-items:flex-start; justify-content:center; flex-direction:column; gap:8px; padding:18px 0; font-size:15px; }
    .custom-layout { grid-template-columns:1fr; gap:28px; }
    .custom-result { padding:24px 0 0; }
    .setup-story ol { grid-template-columns:1fr; gap:26px; margin-top:32px; }
    .setup-story li { display:grid; grid-template-columns:38px 1fr; gap:6px 16px; }
    .setup-story li > span { grid-row:1/3; }
    .setup-story h3 { margin:2px 0 0; font-size:16px; }
    .setup-story li p { max-width:none; grid-column:2; }
    .answers-list button { min-height:76px; font-size:15px; }
    .closing-story nav { flex-direction:column; gap:14px; }
    .closing-story { margin-bottom:48px; }
    .site-footer { padding:36px 20px 0; }
    .footer-top { gap:24px; }
    .footer-contact { gap:8px; }
    .footer-social { gap:0 14px; }
    .footer-social a,.footer-service a { font-size:14px; }
    .footer-meta { align-items:flex-start; flex-direction:column; gap:0; margin-top:24px; }
    .footer-wordmark { margin-top:24px; font-size:25vw; }
  }
  @media(prefers-reduced-motion:reduce) {
    :global(.landing-document) { scroll-behavior:auto; }
    .landing :global(.reveal-pending),.landing :global(.reveal-visible) { opacity:1; transform:none; transition:none; }
    .landing *, .landing *::before, .landing *::after { transition-duration:0s!important; }
  }

</style>
