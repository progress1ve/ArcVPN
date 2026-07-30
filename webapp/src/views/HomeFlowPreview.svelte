<script>
  import { onDestroy } from 'svelte'
  import { fade, fly } from 'svelte/transition'
  import { cubicOut } from 'svelte/easing'
  import { status, tariffs, referral, loadStatus, loadTariffs, loadReferral } from '../lib/data.js'
  import { getUser, haptic, selectionHaptic, openExternal, openTelegram, openPayment, setNativeBackHandler } from '../lib/telegram.js'
  import { copyText } from '../lib/ui.js'
  import { fetchAccount, fetchPreferences, fetchDevices, fetchSupportMessages, sendSupportMessage, savePreferences, requestEmailCode, verifyEmailCode, unlinkEmail, createSbpPayment, fetchSbpPayment } from '../lib/api.js'
  import { daysLeft, daysWord, formatBytes, formatDate } from '../lib/format.js'
  import ArcIcon from '../components/ArcIcon.svelte'
  import DeviceIcon from '../components/DeviceIcon.svelte'

  loadStatus()
  loadTariffs()
  loadReferral()

  const asset = `${import.meta.env.BASE_URL}assets/arc-flow`
  const user = getUser()
  const tabs = [
    { id: 'home', icon: 'home', label: 'Главная' },
    { id: 'friends', icon: 'gift', label: 'Друзья' },
    { id: 'support', icon: 'headset', label: 'Поддержка' },
    { id: 'settings', icon: 'settings', label: 'Настройки' },
  ]
  const faqs = [
    ['VPN не подключается', 'Обновите подписку в приложении, затем переключитесь на другой сервер. Если ошибка осталась — напишите нам в чат.'],
    ['Как установить VPN?', 'Нажмите «Подключить VPN» на главной, выберите устройство и импортируйте подписку в Happ.'],
    ['Интернет стал медленнее', 'Попробуйте сервер со значком молнии или переключитесь между XHTTP, TCP и Hysteria 2.'],
    ['Нашли баг или ошибку?', 'Опишите проблему в чате поддержки. Версия устройства и скриншот помогут решить её быстрее.'],
  ]
  const quickSupportQuestions = [
    'Как настроить обход блокировок?',
    'Не подключается к серверу',
    'Проблема с оплатой/подпиской',
    'Низкая скорость интернета',
  ]
  const stores = {
    iphone: 'https://apps.apple.com/app/happ-proxy-utility/id6504287215',
    android: 'https://play.google.com/store/apps/details?id=com.happproxy',
    windows: 'https://happ.su/',
  }
  const devicesList = [
    { id: 'iphone', label: 'iPhone / iPad', icon: 'apple' },
    { id: 'android', label: 'Android', icon: 'android' },
    { id: 'windows', label: 'Windows', icon: 'windows' },
  ]

  let active = 'home'
  let openFaq = -1
  let referralLinkType = 'site'
  let connectOpen = false
  let connectStage = 'device'
  let selectedDevice = 'iphone'
  let settingsPage = 'main'
  let account = null
  let preferences = { expiry: true, traffic: true, connection: true }
  let registeredDevices = []
  let deviceOnlineTotal = 0
  let accountLoading = true
  let settingsError = ''
  let emailInput = ''
  let emailCode = ''
  let emailStep = 'email'
  let emailBusy = false
  let emailMessage = ''
  let supportChatOpen = false
  let supportMessages = []
  let supportInput = ''
  let supportBusy = false
  let supportError = ''
  let supportPoll = null
  let purchaseOpen = false
  let selectedPlanId = null
  let purchaseDevices = 2
  let purchaseLteGb = 20
  let paymentBusy = false
  let paymentOrderId = ''
  let paymentMessage = ''
  const extraDeviceMonthlyRub = 25
  const includedLteGb = 20
  const extraLteGbMonthlyRub = Math.max(0, Number(import.meta.env.VITE_EXTRA_LTE_GB_MONTHLY_RUB || 2))

  Promise.allSettled([fetchAccount(), fetchPreferences(), fetchDevices()]).then(([accountResult, preferenceResult, deviceResult]) => {
    if (accountResult.status === 'fulfilled') account = accountResult.value
    if (preferenceResult.status === 'fulfilled') preferences = preferenceResult.value.notifications
    if (deviceResult.status === 'fulfilled') {
      registeredDevices = deviceResult.value.devices || []
      deviceOnlineTotal = Number(deviceResult.value.online_total || 0)
    }
    accountLoading = false
  })

  $: keys = $status.data?.keys ?? []
  $: activeKeys = keys.filter((key) => key.is_active)
  $: primary = activeKeys[0] ?? keys[0] ?? null
  $: links = $status.data?.links ?? {}
  $: plans = $tariffs.data?.tariffs ?? []
  $: preferredPlan = plans.length >= 3 ? plans[1] : plans[0]
  $: if (!selectedPlanId && plans.length) selectedPlanId = preferredPlan?.id || plans[0].id
  $: selectedPlan = plans.find((plan) => plan.id === selectedPlanId) || preferredPlan || null
  $: purchaseMonths = Math.max(1, Math.round(Number(selectedPlan?.duration_days || 30) / 30))
  $: purchaseBaseRub = Number(selectedPlan?.price_rub || 0)
  $: purchaseDeviceRub = Math.max(0, purchaseDevices - 2) * extraDeviceMonthlyRub * purchaseMonths
  $: purchaseLteRub = Math.max(0, purchaseLteGb - includedLteGb) * extraLteGbMonthlyRub * purchaseMonths
  $: purchaseTotalRub = purchaseBaseRub + purchaseDeviceRub + purchaseLteRub
  $: purchaseMonthlyRub = Math.round(purchaseTotalRub / purchaseMonths)
  $: supportTimeline = supportMessages.map((message, index) => {
    const day = chatDayKey(message.created_at)
    return { ...message, showDay: index === 0 || day !== chatDayKey(supportMessages[index - 1]?.created_at), dayLabel: chatDayLabel(message.created_at) }
  })
  $: remainingDays = primary?.is_active ? daysLeft(primary.expires_at_unix) : 0
  $: onlineDevices = activeKeys.reduce((total, key) => total + Number(key.online_devices || 0), 0)
  $: trafficRemaining = primary?.traffic_limit
    ? Math.max(0, Number(primary.traffic_limit) - Number(primary.traffic_used || 0))
    : 0
  $: trafficValue = primary?.traffic_limit ? formatBytes(trafficRemaining) : '∞'
  $: ref = $referral.data ?? {}
  $: referralBonus = Number(ref.purchase_bonus_days || 15)
  $: referralSiteLink = ref.site_link || (ref.code ? `${location.origin}/invite/${encodeURIComponent(ref.code)}` : '')
  $: referralStatsLink = ref.stats_link || import.meta.env.VITE_REFERRAL_STATS_URL || referralSiteLink
  $: referralTelegramLink = ref.link || ''
  $: currentReferralLink = referralLinkType === 'site' ? referralSiteLink : referralTelegramLink
  $: subKey = activeKeys.find((key) => key.has_sub) || keys.find((key) => key.has_sub) || null
  $: currentDevice = devicesList.find((item) => item.id === selectedDevice) || devicesList[0]
  $: displayName = user ? [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Пользователь' : 'Пользователь ArcVPN'
  $: username = user?.username ? `@${user.username}` : 'Telegram подключён'
  $: telegramId = $status.data?.telegram_id || user?.id || null
  $: {
    purchaseOpen
    supportChatOpen
    settingsPage
    connectOpen
    setNativeBackHandler(
      purchaseOpen || supportChatOpen || settingsPage !== 'main' || connectOpen
        ? handleNativeBack
        : null,
    )
  }

  function handleNativeBack() {
    haptic('light')
    if (connectOpen) return closeConnect()
    if (purchaseOpen) return closePurchase()
    if (supportChatOpen) return closeSupportChat()
    if (settingsPage !== 'main') settingsPage = 'main'
  }

  function selectTab(id) {
    if (id === active) return
    selectionHaptic()
    active = id
    if (id !== 'support') closeSupportChat()
    if (id !== 'settings') settingsPage = 'main'
    openFaq = -1
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function openSettingsPage(page) {
    haptic('light')
    settingsError = ''
    settingsPage = page
    if (page === 'devices') refreshDevices()
  }

  async function refreshDevices() {
    try {
      const result = await fetchDevices()
      registeredDevices = result.devices || []
      deviceOnlineTotal = Number(result.online_total || 0)
    } catch (_) {
      settingsError = 'Не удалось обновить список устройств'
    }
  }

  function openDevices() {
    active = 'settings'
    openSettingsPage('devices')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function togglePreference(key) {
    const previous = preferences
    preferences = { ...preferences, [key]: !preferences[key] }
    haptic('light')
    try {
      const result = await savePreferences({ [key]: preferences[key] })
      preferences = result.notifications
    } catch (_) {
      preferences = previous
      settingsError = 'Не удалось сохранить настройку'
    }
  }

  async function sendEmailCode(purpose = 'link') {
    emailBusy = true
    emailMessage = ''
    try {
      await requestEmailCode(emailInput.trim(), purpose)
      emailStep = 'code'
      emailMessage = import.meta.env.DEV ? 'Тестовый код: 123456' : 'Код отправлен. Проверьте почту.'
    } catch (error) {
      emailMessage = error.reason === 'email_unavailable' ? 'Отправка писем ещё не настроена на сервере.' : 'Не удалось отправить код. Проверьте email.'
    } finally { emailBusy = false }
  }

  async function confirmEmailCode(purpose = 'link') {
    emailBusy = true
    emailMessage = ''
    try {
      const result = await verifyEmailCode(emailInput.trim(), emailCode.trim(), purpose)
      if (purpose === 'login') {
        await Promise.all([loadStatus({ force: true }), loadTariffs({ force: true }), loadReferral({ force: true })])
        account = await fetchAccount()
        emailMessage = ''
      } else {
        account = { ...(account || {}), email: result.email, email_verified: true }
        emailMessage = 'Email подтверждён и теперь подходит для входа.'
      }
    } catch (error) {
      emailMessage = error.reason === 'email_in_use' ? 'Этот email уже привязан к другому аккаунту.' : 'Неверный или просроченный код.'
    } finally { emailBusy = false }
  }

  async function removeEmail() {
    emailBusy = true
    try {
      await unlinkEmail()
      account = { ...(account || {}), email: null, email_verified: false }
      emailInput = ''
      emailCode = ''
      emailStep = 'email'
      emailMessage = 'Email отвязан.'
    } catch (_) { emailMessage = 'Не удалось отвязать email.' }
    finally { emailBusy = false }
  }

  function deviceIcon(platform) {
    if (platform === 'ios' || platform === 'macos') return 'apple'
    if (platform === 'android') return 'android'
    return 'windows'
  }

  function chatTime(value) {
    if (!value) return ''
    const date = chatDate(value)
    return Number.isNaN(date.getTime()) ? String(value).slice(11, 16) : new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(date)
  }

  function chatDate(value) {
    const normalized = String(value || '').includes('T') ? String(value || '') : `${String(value || '').replace(' ', 'T')}Z`
    return new Date(normalized)
  }

  function chatDayKey(value) {
    const date = chatDate(value)
    return Number.isNaN(date.getTime()) ? String(value || '').slice(0, 10) : `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
  }

  function chatDayLabel(value) {
    const date = chatDate(value)
    if (Number.isNaN(date.getTime())) return ''
    const today = new Date()
    const yesterday = new Date(); yesterday.setDate(today.getDate() - 1)
    if (chatDayKey(date.toISOString()) === chatDayKey(today.toISOString())) return 'Сегодня'
    if (chatDayKey(date.toISOString()) === chatDayKey(yesterday.toISOString())) return 'Вчера'
    return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' }).format(date)
  }

  function toggleFaq(index) {
    haptic('light')
    openFaq = openFaq === index ? -1 : index
  }

  async function buy(plan = preferredPlan) {
    if (!plan || paymentBusy) return
    if (purchaseDevices !== 2 || purchaseLteGb !== 20) {
      paymentMessage = 'Дополнительные лимиты скоро появятся. Для оплаты выберите 2 устройства и 20 ГБ LTE.'
      return
    }
    paymentBusy = true
    paymentMessage = ''
    try {
      const result = await createSbpPayment(plan.id, purchaseDevices, purchaseLteGb)
      paymentOrderId = result.order_id
      openPayment(result.confirmation_url)
      paymentMessage = 'Оплатите в приложении банка, вернитесь сюда и проверьте оплату.'
    } catch (error) {
      paymentMessage = error.reason === 'payment_provider_unavailable'
        ? 'СБП временно недоступна. Попробуйте через минуту.'
        : 'Не удалось создать платёж. Попробуйте ещё раз.'
    } finally { paymentBusy = false }
  }

  async function checkPayment() {
    if (!paymentOrderId || paymentBusy) return
    paymentBusy = true
    try {
      const result = await fetchSbpPayment(paymentOrderId)
      if (result.applied) {
        paymentMessage = 'Оплата получена. Подписка обновлена.'
        haptic('success')
        await loadStatus()
      } else {
        paymentMessage = result.status === 'canceled' ? 'Платёж отменён.' : 'Платёж пока не найден. Проверьте через несколько секунд.'
      }
    } catch (_) { paymentMessage = 'Не удалось проверить платёж. Попробуйте ещё раз.' }
    finally { paymentBusy = false }
  }

  function openPurchase() {
    haptic('medium')
    purchaseOpen = true
    selectedPlanId ||= preferredPlan?.id || plans[0]?.id || null
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  function closePurchase() {
    haptic('light')
    purchaseOpen = false
  }

  function choosePlan(id) {
    selectionHaptic()
    selectedPlanId = id
  }

  function changePurchaseDevices(delta) {
    purchaseDevices = Math.min(10, Math.max(2, purchaseDevices + delta))
    selectionHaptic()
  }

  function changeLteTraffic(delta) {
    purchaseLteGb = Math.min(500, Math.max(includedLteGb, purchaseLteGb + delta * 5))
    selectionHaptic()
  }

  function planMonthly(plan) {
    const months = Math.max(1, Math.round(Number(plan?.duration_days || 30) / 30))
    return Math.round(Number(plan?.price_rub || 0) / months)
  }

  function planBadge(plan) {
    const months = Math.max(1, Math.round(Number(plan?.duration_days || 30) / 30))
    if (months === 3) return 'Популярный'
    if (months === 12) return 'Лучшая цена'
    return ''
  }

  function planPeriod(plan) {
    const months = Math.max(1, Math.round(Number(plan?.duration_days || 30) / 30))
    return `${months} ${months === 1 ? 'месяц' : months >= 2 && months <= 4 ? 'месяца' : 'месяцев'}`
  }

  function rub(value) {
    return `${Math.round(Number(value) || 0).toLocaleString('ru-RU')} ₽`
  }

  function openConnect() {
    haptic('medium')
    connectStage = 'device'
    connectOpen = true
  }

  function closeConnect() {
    haptic('light')
    connectOpen = false
  }

  function chooseDevice(id) {
    selectionHaptic()
    selectedDevice = id
  }

  function continueConnect() {
    haptic('medium')
    connectStage = 'guide'
  }

  function shareReferral() {
    if (!currentReferralLink) return
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(currentReferralLink)}&text=${encodeURIComponent('Подключайся к ArcVPN — после первой оплаты получим по 15 дней')}`
    openTelegram(shareUrl)
  }

  async function loadSupportMessages() {
    try {
      const after = supportMessages.at(-1)?.id || 0
      const result = await fetchSupportMessages(after)
      const incoming = result.messages || []
      const known = new Set(supportMessages.map((item) => item.id))
      supportMessages = [...supportMessages, ...incoming.filter((item) => !known.has(item.id))]
      supportError = ''
    } catch (_) { supportError = 'Не удалось обновить диалог.' }
  }

  function openSupport() {
    haptic('light')
    active = 'support'
    supportChatOpen = true
    loadSupportMessages()
    clearInterval(supportPoll)
    supportPoll = setInterval(loadSupportMessages, 5000)
  }

  function closeSupportChat() {
    supportChatOpen = false
    clearInterval(supportPoll)
    supportPoll = null
  }

  async function submitSupportMessage(bodyOverride = '') {
    const body = typeof bodyOverride === 'string' && bodyOverride.trim()
      ? bodyOverride.trim()
      : supportInput.trim()
    if (!body || supportBusy) return
    supportBusy = true
    supportError = ''
    try {
      const result = await sendSupportMessage(body)
      supportMessages = [...supportMessages, result.message]
      supportInput = ''
      haptic('light')
    } catch (error) {
      supportError = error.reason === 'try_later' ? 'Слишком много сообщений. Подождите минуту.' : 'Сообщение не отправлено. Попробуйте ещё раз.'
    } finally { supportBusy = false }
  }

  function sendQuickSupportQuestion(text) {
    selectionHaptic()
    submitSupportMessage(text)
  }

  onDestroy(() => {
    clearInterval(supportPoll)
    setNativeBackHandler(null)
  })
</script>

<div class="flow-preview">
  <div class="aurora" aria-hidden="true">
    <i class="aurora-blob blob-one"></i>
    <i class="aurora-blob blob-two"></i>
    <i class="aurora-blob blob-three"></i>
  </div>
  <div class="grain" aria-hidden="true"></div>

  {#key active}
    <main in:fly={{ y: 14, duration: 260, easing: cubicOut }} out:fade={{ duration: 90 }}>
      {#if purchaseOpen}
        <section class="screen purchase-screen" aria-label="Покупка подписки">
          <header class="purchase-head native-back-head">
            <div><h1>Выберите свой<br />ритм подключения</h1><span>Срок, устройства и запас трафика — в одной подписке.</span></div>
          </header>

          {#if plans.length}
            <div class="plan-viewport">
              <div class="plan-strip" aria-label="Выбор тарифа">
                {#each plans as plan}
                  <button class="plan-card" class:active={selectedPlanId === plan.id} on:click={() => choosePlan(plan.id)}>
                    <span>{planPeriod(plan)}</span>
                    {#if planBadge(plan)}<em>{planBadge(plan)}</em>{/if}
                    <strong>{rub(plan.price_rub)}</strong>
                    <small>{rub(planMonthly(plan))} / мес</small>
                    {#if selectedPlanId === plan.id}<i><ArcIcon name="check" size={15} weight="bold" /></i>{/if}
                  </button>
                {/each}
              </div>
            </div>
          {:else}
            <p class="purchase-empty">Тарифы загружаются…</p>
          {/if}

          <section class="purchase-config">
            <div class="config-copy"><span>Устройства</span><h2>Сколько устройств подключить?</h2><p>Включено 2 устройства.<br />Дополнительные устройства: +25₽ / месяц каждое</p></div>
            <div class="stepper" aria-label="Количество устройств">
              <button aria-label="Уменьшить количество устройств" disabled={purchaseDevices <= 2} on:click={() => changePurchaseDevices(-1)}>−</button>
              <strong>{purchaseDevices}</strong>
              <button aria-label="Увеличить количество устройств" disabled={purchaseDevices >= 10} on:click={() => changePurchaseDevices(1)}>+</button>
            </div>
          </section>

          <section class="purchase-config traffic-config">
            <div class="config-copy"><span>Обход глушения</span><h2>Дополнительный LTE-трафик</h2><p>20 ГБ включено бесплатно. Дальше — по 5 ГБ за 10 ₽ в месяц.</p></div>
            <div class="stepper wide" aria-label="Дополнительный LTE-трафик">
              <button aria-label="Уменьшить LTE-трафик" disabled={purchaseLteGb <= includedLteGb} on:click={() => changeLteTraffic(-1)}>−</button>
              <strong>{purchaseLteGb}<small>ГБ</small></strong>
              <button aria-label="Увеличить LTE-трафик" disabled={purchaseLteGb >= 500} on:click={() => changeLteTraffic(1)}>+</button>
            </div>
          </section>

          <section class="purchase-total">
            <div class="total-row"><span><ArcIcon name="calendar" size={18} weight="duotone" />{selectedPlan ? planPeriod(selectedPlan) : 'Тариф'}</span><small>{rub(purchaseBaseRub)}</small></div>
            <div class="total-row"><span><ArcIcon name="devices" size={18} weight="duotone" />{purchaseDevices} устройства</span><small>{purchaseDeviceRub ? `+${rub(purchaseDeviceRub)}` : 'включено'}</small></div>
            <div class="total-row"><span><ArcIcon name="lte" size={19} />LTE {purchaseLteGb} ГБ</span><small>{purchaseLteRub ? `+${rub(purchaseLteRub)}` : '20 ГБ включено'}</small></div>
            <button disabled={!selectedPlan || paymentBusy} on:click={() => buy(selectedPlan)}><span>{paymentBusy ? 'Подождите…' : 'Оплатить через СБП'}</span><strong>{rub(purchaseBaseRub)}</strong></button>
            {#if paymentOrderId}<button class="payment-check" disabled={paymentBusy} on:click={checkPayment}>Проверить оплату</button>{/if}
            {#if paymentMessage}<p class="payment-message">{paymentMessage}</p>{/if}
            <p>{rub(purchaseMonthlyRub)} в месяц · настройки сохранятся для выбранной подписки</p>
          </section>
        </section>
      {:else if $status.error === 'unauthorized'}
        <section class="screen login-screen" aria-label="Вход в ArcVPN">
          <div class="brand"><img src={`${asset}/arc-logo.svg`} alt="" /><span>ArcVPN</span></div>
          <div class="login-copy"><h1>Войдите<br />в свой аккаунт</h1><span>Email открывает тот же аккаунт и подписку, которые уже связаны с вашим Telegram.</span></div>
          <section class="email-form login-form">
            <label><span>Email</span><input type="email" autocomplete="email" bind:value={emailInput} placeholder="name@example.com" disabled={emailBusy || emailStep === 'code'} /></label>
            {#if emailStep === 'code'}<label><span>Код из письма</span><input inputmode="numeric" maxlength="6" autocomplete="one-time-code" bind:value={emailCode} placeholder="000000" /></label>{/if}
            {#if emailStep === 'email'}<button disabled={emailBusy || !emailInput.includes('@')} on:click={() => sendEmailCode('login')}>Получить код</button>{:else}<button disabled={emailBusy || emailCode.length !== 6} on:click={() => confirmEmailCode('login')}>Войти</button>{/if}
          </section>
          {#if emailMessage}<p class="form-message">{emailMessage}</p>{/if}
          <p class="login-help">Email должен быть заранее привязан в настройках ArcVPN внутри Telegram.</p>
        </section>
      {:else if active === 'home'}
        <section class="screen home-screen" aria-label="Главная">
          <div class="brand">
            <img src={`${asset}/arc-logo.svg`} alt="" />
            <span>ArcVPN</span>
          </div>

          <p class="eyebrow">{primary?.is_active ? 'Осталось' : 'Подписка'}</p>
          <div class="days"><strong>{primary?.is_active ? remainingDays : '—'}</strong>{#if primary?.is_active}<span>{daysWord(remainingDays)}</span>{/if}</div>
          <p class="expires">
            {#if $status.loading && !$status.data}загружаем данные…
            {:else if primary?.is_active}до {formatDate(primary.expires_at_unix)}
            {:else if primary}закончилась {formatDate(primary.expires_at_unix)}
            {:else}оформите подписку, чтобы подключиться{/if}
          </p>

          <div class="stats">
            <button class="stat" on:click={openDevices}>
              <ArcIcon name="phone" size={17} weight="duotone" />
              <span><b>{onlineDevices}</b><small>устройства</small></span>
            </button>
            <button class="stat">
              <ArcIcon name="pulse" size={18} weight="duotone" />
              <span><b>{trafficValue}</b><small>обычный</small></span>
            </button>
            <button class="stat">
              <ArcIcon name="signal" size={18} weight="duotone" />
              <span><b>∞</b><small>LTE</small></span>
            </button>
          </div>

          <div class="actions">
            <button class="primary" on:click={openPurchase}><ArcIcon name="wallet" size={20} weight="duotone" />{primary?.is_active ? 'Продлить подписку' : 'Оформить подписку'}</button>
            <button class="secondary" on:click={openConnect}><ArcIcon name="download" size={20} weight="bold" />Подключить VPN</button>
          </div>

          <div class="shortcuts">
            <button class="shortcut" on:click={() => selectTab('friends')}>
              <span class="shortcut-copy">
                <b>Пригласи друга</b><small>По {referralBonus} дней каждому</small>
                <i><ArcIcon name="arrow" size={17} weight="bold" /></i>
              </span>
              <img src={`${asset}/referral-gift-v2.png`} alt="" />
            </button>
            <button class="shortcut" on:click={() => selectTab('support')}>
              <span class="shortcut-copy">
                <b>Поддержка</b><small>FAQ и живой чат</small>
                <i><ArcIcon name="arrow" size={17} weight="bold" /></i>
              </span>
              <img src={`${asset}/support-agent-v2.png`} alt="" />
            </button>
          </div>
        </section>

      {:else if active === 'friends'}
        <section class="screen inner-screen" aria-label="Друзья">
          <header class="section-head"><h1>Приглашай.<br />Получай дни.</h1></header>

          <article class="referral-hero">
            <div class="referral-copy"><span>Реферальная программа</span><strong>+{referralBonus} дней</strong><p>тебе и другу после первой оплаты</p></div>
            <img src={`${asset}/referral-gift-v2.png`} alt="" />
          </article>

          <div class="metric-grid">
            <article><span>Приглашено</span><strong>{ref.total_invited ?? 0}</strong><small>друзей</small></article>
            <article><span>Получено</span><strong>{ref.earned_days ?? 0}</strong><small>дней</small></article>
          </div>

          <section class="content-block">
            <div class="block-title"><div><span>Ваша ссылка</span><small>Отправьте её другу</small></div><ArcIcon name="link" size={21} weight="duotone" /></div>
            <div class="link-switch" aria-label="Вид реферальной ссылки">
              <button class:active={referralLinkType === 'site'} on:click={() => (referralLinkType = 'site')}>Для сайта</button>
              <button class:active={referralLinkType === 'telegram'} on:click={() => (referralLinkType = 'telegram')}>Для Telegram</button>
            </div>
            <button class="referral-link" disabled={!currentReferralLink} on:click={() => copyText(currentReferralLink, 'Реферальная ссылка скопирована')}><span>{currentReferralLink || 'Ссылка загружается…'}</span><i><ArcIcon name="copy" size={19} weight="bold" /></i></button>
            <button class="share-referral" disabled={!currentReferralLink} on:click={shareReferral}><ArcIcon name="send" size={18} weight="bold" />Поделиться</button>
          </section>

          <section class="steps">
            <div><i>1</i><span><b>Поделитесь ссылкой</b><small>Друг переходит в ArcVPN</small></span></div>
            <div><i>2</i><span><b>Друг покупает тариф</b><small>На любой срок и любым способом</small></span></div>
            <div><i>3</i><span><b>Оба получаете +{referralBonus} дней</b><small>Начислим автоматически</small></span></div>
          </section>
          <button class="referral-stats-link" disabled={!referralStatsLink} on:click={() => openExternal(referralStatsLink)}>
            <span><b>Полная статистика</b><small>Открыть на сайте</small></span>
            <ArcIcon name="external" size={19} weight="bold" />
          </button>
        </section>

      {:else if active === 'support'}
        <section class="screen inner-screen" aria-label="Поддержка">
          {#if supportChatOpen}
            <header class="section-head subpage-head chat-head native-back-head"><div><h1>Чат с менеджером</h1></div></header>
            <section class="support-chat" aria-live="polite">
              {#if !supportMessages.length}<div class="chat-row incoming"><span class="care-avatar"><img src={`${asset}/arc-logo.svg`} alt="" /></span><div class="chat-welcome"><b>Поддержка ArcVPN</b><span>Здравствуйте 👋 Опишите вопрос. Менеджер ответит здесь, а бот пришлёт уведомление.</span></div></div>{/if}
              {#each supportTimeline as message}
                {#if message.showDay}<div class="chat-day"><span>{message.dayLabel}</span></div>{/if}
                <div class:mine={message.sender === 'user'} class:incoming={message.sender !== 'user'} class="chat-row">
                  {#if message.sender !== 'user'}<span class="care-avatar"><img src={`${asset}/arc-logo.svg`} alt="Arc Care" /></span>{/if}
                  <article class:mine={message.sender === 'user'} class="chat-message">{#if message.sender !== 'user'}<b>Поддержка ArcVPN</b>{/if}<p>{message.body}</p><small>{chatTime(message.created_at)}</small></article>
                </div>
              {/each}
              {#if supportError}<p class="chat-error">{supportError}</p>{/if}
            </section>
            <div class="chat-input-zone">
              <div class="chat-quick" aria-label="Быстрые вопросы">
                {#each quickSupportQuestions as question}<button disabled={supportBusy} on:click={() => sendQuickSupportQuestion(question)}>{question}</button>{/each}
              </div>
              <form class="chat-compose" on:submit|preventDefault={submitSupportMessage}>
                <textarea rows="1" maxlength="2000" bind:value={supportInput} placeholder="Опишите свой вопрос" aria-label="Сообщение поддержке"></textarea>
                <button aria-label="Отправить" disabled={supportBusy || !supportInput.trim()}><ArcIcon name="send" size={19} weight="bold" /></button>
              </form>
            </div>
          {:else}
            <header class="section-head"><h1>Помощь без<br />лишних кругов.</h1></header>

            <article class="support-hero">
              <div><span>Живой чат</span><h2>Мы рядом</h2><p>Напишите менеджеру — история обращения сохранится.</p><button on:click={openSupport}><ArcIcon name="chat" size={19} weight="duotone" />Перейти в чат</button></div>
              <img src={`${asset}/support-agent-v2.png`} alt="" />
            </article>

            <section class="faq-section">
              <div class="section-label"><span>Частые вопросы</span><small>{faqs.length} ответа</small></div>
              {#each faqs as faq, i}
                <button class="faq" class:open={openFaq === i} on:click={() => toggleFaq(i)}>
                  <span class="faq-number">{i + 1}</span>
                  <span class="faq-copy"><b>{faq[0]}</b>{#if openFaq === i}<small>{faq[1]}</small>{/if}</span>
                  <i><ArcIcon name="caret" size={18} weight="bold" /></i>
                </button>
              {/each}
            </section>
          {/if}
        </section>

      {:else}
        <section class="screen inner-screen settings-screen" aria-label="Настройки">
          <header class="section-head subpage-head" class:native-back-head={settingsPage !== 'main'}>
            <div><h1>{settingsPage === 'main' ? 'Настройки' : settingsPage === 'devices' ? 'Устройства' : settingsPage === 'notifications' ? 'Уведомления' : settingsPage === 'email' ? 'Email' : 'Соглашение'}</h1></div>
          </header>

          {#if settingsError}<p class="settings-error">{settingsError}</p>{/if}

          {#if settingsPage === 'main'}
            <article class="profile-card">
              {#if user?.photo_url}<img class="avatar avatar-photo" src={user.photo_url} alt="" />{:else}<div class="avatar">{displayName.charAt(0).toUpperCase()}</div>{/if}
              <div><strong>{displayName}</strong><span>{telegramId ? `Telegram ID · ${telegramId}` : username}</span></div><i><ArcIcon name="shield" size={22} weight="duotone" /></i>
            </article>

            <section class="settings-group">
              <h2>Подписка</h2>
              <button class="setting-row" on:click={() => openSettingsPage('devices')}><i><ArcIcon name="devices" size={21} weight="duotone" /></i><span><b>Устройства</b><small>{deviceOnlineTotal || onlineDevices} активно · {registeredDevices.length} импортировано</small></span><ArcIcon name="caret" size={17} weight="bold" /></button>
              <button class="setting-row" on:click={() => openSettingsPage('notifications')}><i><ArcIcon name="bell" size={21} weight="duotone" /></i><span><b>Уведомления</b><small>Срок, трафик и новые подключения</small></span><ArcIcon name="caret" size={17} weight="bold" /></button>
            </section>

            <section class="settings-group">
              <h2>Способы входа</h2>
              <button class="setting-row login-row" on:click={() => openSettingsPage('email')}><i><ArcIcon name="email" size={21} weight="duotone" /></i><span><b>Email</b><small>{account?.email || 'Вход без отдельной регистрации'}</small></span>{#if account?.email_verified}<em class="connected"><ArcIcon name="check" size={17} weight="bold" /></em>{:else}<ArcIcon name="caret" size={17} weight="bold" />{/if}</button>
              <button class="setting-row login-row"><i class="telegram"><ArcIcon name="telegram" size={21} weight="fill" /></i><span><b>Telegram</b><small>{username}</small></span><em class="connected"><ArcIcon name="check" size={17} weight="bold" /></em></button>
            </section>

            <section class="settings-group">
              <h2>Информация</h2>
              <button class="setting-row" on:click={() => openSettingsPage('agreement')}><i><ArcIcon name="file" size={21} weight="duotone" /></i><span><b>Пользовательское соглашение</b><small>Обновлено 29 июля 2026</small></span><ArcIcon name="caret" size={17} weight="bold" /></button>
            </section>
          {:else if settingsPage === 'devices'}
            <p class="subpage-intro">Устройство появляется здесь сразу после открытия страницы импорта в Happ. Точную модель показываем только когда её передаёт система.</p>
            <div class="device-summary"><strong>{deviceOnlineTotal || onlineDevices}</strong><span>активно сейчас</span><small>{registeredDevices.length} импортировано</small></div>
            <section class="device-list">
              {#if registeredDevices.length}
                {#each registeredDevices as device}
                  <article class="registered-device">
                    <i><DeviceIcon name={deviceIcon(device.platform)} size={25} /></i>
                    <span><b>{device.display_name || device.model || 'Устройство'}</b><small>{[device.model, device.browser].filter(Boolean).join(' · ') || 'Данные платформы скрыты системой'}</small></span>
                    <em>{device.last_seen_at ? 'видели недавно' : 'импортировано'}</em>
                  </article>
                {/each}
              {:else if accountLoading}<p class="empty-state">Загружаем устройства…</p>
              {:else}<p class="empty-state">Пока нет импортированных устройств.</p>{/if}
            </section>
            <button class="subpage-primary" on:click={openConnect}><ArcIcon name="download" size={19} weight="bold" />Подключить новое устройство</button>
          {:else if settingsPage === 'notifications'}
            <p class="subpage-intro">Выберите, какие служебные сообщения ArcVPN может отправлять вам в Telegram.</p>
            <section class="preference-list">
              <button on:click={() => togglePreference('expiry')}><span><b>Срок подписки</b><small>Напомним до окончания и после отключения</small></span><i class:on={preferences.expiry}><em></em></i></button>
              <button on:click={() => togglePreference('traffic')}><span><b>Остаток трафика</b><small>Предупредим при достижении порогов</small></span><i class:on={preferences.traffic}><em></em></i></button>
              <button on:click={() => togglePreference('connection')}><span><b>Новое подключение</b><small>Сообщим о первом подключении ключа</small></span><i class:on={preferences.connection}><em></em></i></button>
            </section>
          {:else if settingsPage === 'email'}
            <p class="subpage-intro">Email — дополнительный способ войти в тот же аккаунт ArcVPN вне Telegram. Новая регистрация не создаётся.</p>
            {#if account?.email_verified}
              <section class="email-connected"><i><ArcIcon name="email" size={25} weight="duotone" /></i><span><small>Подтверждённый email</small><b>{account.email}</b></span><em><ArcIcon name="check" size={17} /></em></section>
              <button class="danger-action" disabled={emailBusy} on:click={removeEmail}>Отвязать email</button>
            {:else}
              <section class="email-form">
                <label><span>Email</span><input type="email" autocomplete="email" bind:value={emailInput} placeholder="name@example.com" disabled={emailBusy || emailStep === 'code'} /></label>
                {#if emailStep === 'code'}<label><span>Код из письма</span><input inputmode="numeric" maxlength="6" autocomplete="one-time-code" bind:value={emailCode} placeholder="000000" /></label>{/if}
                {#if emailStep === 'email'}<button disabled={emailBusy || !emailInput.includes('@')} on:click={sendEmailCode}>Получить код</button>{:else}<button disabled={emailBusy || emailCode.length !== 6} on:click={confirmEmailCode}>Подтвердить</button>{/if}
              </section>
            {/if}
            {#if emailMessage}<p class="form-message">{emailMessage}</p>{/if}
          {:else}
            <article class="agreement">
              <div class="agreement-meta"><span>Пользовательское соглашение ArcVPN</span><small>Обновлено 29 июля 2026</small></div>
              <h2>Коротко и понятно</h2>
              <p>Используя ArcVPN, вы соглашаетесь применять сервис законно, не передавать доступ посторонним и не использовать его для атак, спама или нарушения прав других людей.</p>
              <h3>Подписка и оплата</h3><p>Доступ предоставляется на оплаченный срок. Условия тарифа показываются до оплаты. Вопросы по ошибочным платежам решаются через поддержку с учётом применимого законодательства.</p>
              <h3>Доступность</h3><p>Мы поддерживаем работу сервиса и устраняем сбои, но не обещаем абсолютную доступность каждого сервера, сайта или протокола в любой момент.</p>
              <h3>Данные</h3><p>Для работы аккаунта используются Telegram ID, имя пользователя, подтверждённый email, данные подписки и оплаты. При импорте мы сохраняем тип устройства и модель только если её сообщает система. Содержимое вашего интернет-трафика не сохраняется.</p>
              <h3>Изменения</h3><p>При существенном изменении условий обновится дата документа. Продолжение использования сервиса после публикации означает принятие новой версии.</p>
              <h3>Реквизиты оператора</h3><p>[УКАЖИТЕ ФИО/НАЗВАНИЕ] · ИНН [УКАЖИТЕ ИНН] · ОГРНИП/ОГРН [УКАЖИТЕ НОМЕР] · [УКАЖИТЕ EMAIL]</p>
              <button on:click={openSupport}><ArcIcon name="chat" size={18} weight="duotone" />Задать вопрос поддержке</button>
            </article>
          {/if}
        </section>
      {/if}
    </main>
  {/key}

  {#if connectOpen}
    <div class="connect-overlay" role="presentation" in:fade={{ duration: 160 }}>
      <button class="connect-backdrop" aria-label="Закрыть подключение" on:click={closeConnect}></button>
      <section class="connect-sheet" role="dialog" aria-modal="true" aria-label="Подключение VPN" in:fly={{ y: 60, duration: 260, easing: cubicOut }}>
        <header class="connect-head">
          <div>
            <span>ARC CONNECT</span>
            <h2>{connectStage === 'device' ? 'Выберите устройство' : currentDevice.label}</h2>
          </div>
          <button aria-label="Закрыть" on:click={closeConnect}><ArcIcon name="close" size={26} /></button>
        </header>

        {#if connectStage === 'device'}
          <p class="connect-note">Подберём приложение и импортируем вашу подписку.</p>
          <div class="device-grid">
            {#each devicesList as item}
              <button class:active={selectedDevice === item.id} on:click={() => chooseDevice(item.id)}>
                <i><DeviceIcon name={item.icon} size={26} /></i>
                <span>{item.label}</span>
                {#if selectedDevice === item.id}<em><ArcIcon name="check" size={16} /></em>{/if}
              </button>
            {/each}
          </div>
          <button class="sheet-primary" on:click={continueConnect}>Продолжить<ArcIcon name="arrow" size={18} /></button>
        {:else if !subKey}
          <button class="sheet-back" on:click={() => (connectStage = 'device')}><ArcIcon name="back" size={18} />Назад</button>
          <div class="empty-connect"><ArcIcon name="lock" size={28} /><h3>Нет активной подписки</h3><p>Оформите тариф, после чего здесь появится персональная ссылка импорта.</p></div>
          <button class="sheet-primary" on:click={() => buy()}>Оформить подписку</button>
        {:else}
          <button class="sheet-back" on:click={() => (connectStage = 'device')}><ArcIcon name="back" size={18} />Назад</button>
          <div class="guide-card">
            <i>1</i><div><b>Установите Happ</b><small>Официальное приложение для {currentDevice.label}</small></div>
            <button on:click={() => openExternal(stores[selectedDevice])}>Скачать<ArcIcon name="arrow" size={16} /></button>
          </div>
          <div class="guide-card">
            <i>2</i><div><b>Добавьте ArcVPN</b><small>HTTPS-страница безопасно передаст подписку в Happ</small></div>
            <button on:click={() => openExternal(subKey.import_url)}>Импорт<ArcIcon name="arrow" size={16} /></button>
          </div>
          <button class="sheet-secondary" on:click={() => copyText(subKey.sub_url, 'Ссылка подписки скопирована')}><ArcIcon name="copy" size={18} />Скопировать ссылку</button>
          <p class="connect-success"><ArcIcon name="check" size={18} />После импорта разрешите Happ добавить VPN-конфигурацию.</p>
        {/if}
      </section>
    </div>
  {/if}

  {#if $status.error !== 'unauthorized' && !purchaseOpen}<div class="dock">
    <nav aria-label="Навигация">
      {#each tabs as tab}
        <button class:active={active === tab.id} aria-label={tab.label} title={tab.label} on:click={() => selectTab(tab.id)}>
          <ArcIcon name={tab.icon} size={24} weight={active === tab.id ? 'duotone' : 'regular'} />
        </button>
      {/each}
    </nav>
  </div>{/if}
</div>

<style>
  .flow-preview {
    --text: #f7f9fd;
    --muted: #8b98aa;
    --faint: #556477;
    --border: rgba(187, 218, 249, .12);
    --surface: rgba(7, 13, 23, .78);
    --safe-top-flow: max(env(safe-area-inset-top, 0px), var(--tg-content-safe-top, 0px));
    --safe-bottom-flow: max(env(safe-area-inset-bottom, 0px), var(--tg-content-safe-bottom, 0px));
    position: relative;
    min-height: 100dvh;
    overflow-x: hidden;
    color: var(--text);
    background:
      radial-gradient(95% 48% at 50% -10%, rgba(23, 65, 116, .17), transparent 68%),
      radial-gradient(80% 42% at 15% 108%, rgba(26, 88, 145, .12), transparent 72%),
      #02050b;
    font-family: 'Manrope', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    isolation: isolate;
  }
  .grain { position: fixed; z-index: -1; inset: 0; pointer-events: none; opacity: .02; background-image: repeating-linear-gradient(111deg,rgba(255,255,255,.22) 0 1px,transparent 1px 5px),repeating-linear-gradient(27deg,rgba(255,255,255,.12) 0 1px,transparent 1px 7px); mix-blend-mode: soft-light; }
  main { position: relative; z-index: 2; min-height: 100dvh; }
  .screen { min-height: 100dvh; padding: calc(var(--safe-top-flow) + 38px) 20px calc(108px + var(--safe-bottom-flow)); }
  .home-screen { padding-top: calc(var(--safe-top-flow) + 68px); text-align: center; }
  .brand { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 27px; filter: drop-shadow(0 14px 28px rgba(69,159,225,.2)); }
  .brand img { width: 24px; height: 23px; object-fit: contain; filter: brightness(0) invert(1); }
  .brand span { font-size: 18px; font-weight: 800; letter-spacing: -.045em; }
  .eyebrow { margin: 0; color: var(--muted); font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
  .days { display: flex; align-items: baseline; justify-content: center; gap: 9px; margin-top: 3px; }
  .days strong { font-size: 60px; font-weight: 800; line-height: 1; letter-spacing: -.065em; font-variant-numeric: tabular-nums; }
  .days span { font-size: 18px; font-weight: 700; letter-spacing: -.035em; }
  .expires { margin: 7px 0 0; color: var(--muted); font-size: 12.5px; }
  .stats { display: flex; gap: 8px; width: 100%; margin-top: 23px; }
  .stat { min-width: 0; min-height: 44px; display: flex; flex: 1; align-items: center; justify-content: center; gap: 7px; padding: 8px 9px; border: 1px solid var(--border); border-radius: 18px; color: #8192a6; background: rgba(6,11,19,.55); box-shadow: inset 0 1px 0 rgba(255,255,255,.025); backdrop-filter: blur(14px); }
  .stat > span { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; line-height: 1.05; }
  .stat b { overflow: hidden; max-width: 100%; color: var(--text); font-size: 11.5px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }
  .stat small { margin-top: 3px; color: var(--faint); font-size: 9px; white-space: nowrap; }
  .actions { display: grid; gap: 11px; margin-top: 30px; }
  .actions button { min-height: 55px; display: flex; align-items: center; justify-content: center; gap: 10px; border-radius: 18px; font-size: 15px; font-weight: 800; letter-spacing: -.018em; }
  .primary { color: #03101d; background: linear-gradient(128deg,#b3e4ff 0%,#72c5f4 48%,#448fcf 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,.7),0 18px 44px -25px rgba(71,172,239,.9); }
  .secondary { color: #88cff8; border: 1px solid rgba(105,190,244,.58); background: rgba(6,15,27,.2); box-shadow: inset 0 1px 0 rgba(255,255,255,.035); backdrop-filter: blur(11px); }
  .shortcuts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 34px; }
  .shortcut { position: relative; min-width: 0; min-height: 145px; overflow: hidden; padding: 17px 15px; border: 1px solid var(--border); border-radius: 24px; color: var(--text); background: linear-gradient(150deg,rgba(255,255,255,.035),transparent 43%),rgba(7,13,23,.78); box-shadow: inset 0 1px 0 rgba(255,255,255,.04); backdrop-filter: blur(18px); text-align: left; }
  .shortcut::before { content: ''; position: absolute; right: -16px; bottom: -18px; width: 132px; height: 126px; border-radius: 50%; background: radial-gradient(circle,rgba(101,196,247,.2) 0%,rgba(46,132,198,.1) 38%,transparent 70%); filter: blur(8px); }
  .shortcut::after { content: ''; position: absolute; right: -25%; bottom: -60%; width: 145px; height: 145px; border-radius: 50%; background: radial-gradient(circle,rgba(63,154,220,.18),transparent 67%); }
  .shortcut-copy { position: relative; z-index: 3; display: flex; align-items: flex-start; flex-direction: column; }
  .shortcut-copy b { max-width: 112px; font-size: 13.5px; font-weight: 800; line-height: 1.2; letter-spacing: -.025em; }
  .shortcut-copy small { max-width: 108px; margin-top: 5px; color: var(--muted); font-size: 9.5px; line-height: 1.35; }
  .shortcut-copy i { width: 48px; height: 32px; display: grid; place-items: center; margin-top: 17px; border: 1px solid rgba(255,255,255,.1); border-radius: 14px; color: #dce9f5; background: rgba(255,255,255,.075); }
  .shortcut img { position: absolute; z-index: 2; right: -19px; bottom: -13px; width: 119px; height: 119px; object-fit: contain; pointer-events: none; filter: drop-shadow(0 0 13px rgba(95,189,244,.16)) drop-shadow(0 18px 18px rgba(0,0,0,.3)); }

  .inner-screen { text-align: left; }
  .section-head { position: relative; text-align: center; }
  .section-head h1 { margin: 0; font-size: 31px; font-weight: 800; line-height: 1.05; letter-spacing: -.055em; text-align: center; }
  .referral-hero, .support-hero { position: relative; min-height: 190px; overflow: hidden; margin-top: 28px; padding: 23px; border: 1px solid rgba(146,200,242,.16); border-radius: 28px; background: linear-gradient(135deg,rgba(42,115,179,.22),rgba(7,13,23,.82) 58%); box-shadow: inset 0 1px 0 rgba(255,255,255,.05); }
  .referral-hero::before, .support-hero::before { content: ''; position: absolute; right: -45px; bottom: -60px; width: 240px; height: 240px; border-radius: 50%; background: radial-gradient(circle,rgba(92,187,241,.22),rgba(35,105,171,.08) 48%,transparent 70%); filter: blur(10px); }
  .referral-copy { position: relative; z-index: 2; max-width: 190px; }
  .referral-copy > span, .support-hero > div > span { color: #91a5b8; font-size: 10.5px; font-weight: 700; }
  .referral-copy strong { display: block; margin-top: 10px; font-size: 35px; line-height: 1; letter-spacing: -.055em; }
  .referral-copy p { max-width: 150px; margin: 8px 0 0; color: #9eacbb; font-size: 11px; line-height: 1.45; }
  .referral-hero img { position: absolute; right: -34px; bottom: -27px; width: 190px; height: 190px; object-fit: contain; filter: drop-shadow(0 0 18px rgba(87,180,237,.15)); }
  .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
  .metric-grid article { padding: 17px 18px; border: 1px solid var(--border); border-radius: 21px; background: rgba(7,13,23,.72); }
  .metric-grid span { display: block; color: var(--muted); font-size: 10px; }
  .metric-grid strong { display: inline-block; margin-top: 7px; font-size: 25px; line-height: 1; }
  .metric-grid small { margin-left: 5px; color: var(--faint); font-size: 10px; }
  .content-block { margin-top: 24px; }
  .block-title, .section-label { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; color: #7dbce6; }
  .block-title > div { display: flex; flex-direction: column; }
  .block-title span, .section-label span { color: var(--text); font-size: 13px; font-weight: 800; }
  .block-title small, .section-label small { margin-top: 2px; color: var(--faint); font-size: 9.5px; }
  .link-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 9px; padding: 4px; border: 1px solid var(--border); border-radius: 15px; background: rgba(7,13,23,.68); }
  .link-switch button { min-height: 44px; border-radius: 12px; color: #667487; font-size: 10.5px; font-weight: 750; }
  .link-switch button.active { color: #07131f; background: linear-gradient(135deg,#b5e5ff,#70c2ef); box-shadow: inset 0 1px 0 rgba(255,255,255,.62); }
  .referral-link { width: 100%; min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 0 10px 0 16px; border: 1px solid var(--border); border-radius: 18px; background: rgba(8,15,26,.82); color: #b5c1ce; }
  .referral-link span { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
  .referral-link i { width: 40px; height: 40px; display: grid; flex: none; place-items: center; border-radius: 13px; color: #0a1a28; background: #75c6f3; }
  .share-referral { width: 100%; min-height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 9px; border: 1px solid rgba(105,190,244,.44); border-radius: 16px; color: #83cff9; background: rgba(10,26,43,.38); font-size: 11.5px; font-weight: 800; }
  .referral-stats-link { width: 100%; min-height: 58px; display: flex; align-items: center; justify-content: space-between; margin-top: 16px; padding: 0 17px; color: #dcebf6; background: var(--surface-raised); text-align: left; }
  .referral-stats-link span { display: flex; flex-direction: column; }
  .referral-stats-link b { font-size: 11.5px; }
  .referral-stats-link small { margin-top: 3px; color: var(--muted); font-size: 9.5px; }
  .steps { margin-top: 20px; padding: 4px 16px; border: 1px solid var(--border); border-radius: 22px; background: rgba(7,13,23,.62); }
  .steps > div { display: flex; align-items: center; gap: 12px; padding: 13px 0; }
  .steps > div + div { border-top: 1px solid rgba(255,255,255,.06); }
  .steps i { width: 26px; height: 26px; display: grid; flex: none; place-items: center; border-radius: 9px; color: #9edbff; background: rgba(80,174,232,.13); font-size: 10px; font-style: normal; font-weight: 800; }
  .steps span { display: flex; flex-direction: column; }
  .steps b { font-size: 11.5px; }
  .steps small { margin-top: 2px; color: var(--faint); font-size: 9.5px; }
  .support-hero { min-height: 205px; }
  .support-hero > div { position: relative; z-index: 2; max-width: 205px; }
  .support-hero h2 { margin: 7px 0 0; font-size: 27px; letter-spacing: -.04em; }
  .support-hero p { max-width: 190px; margin: 7px 0 15px; color: #9eacbb; font-size: 10.5px; line-height: 1.45; }
  .support-hero button { min-height: 44px; display: inline-flex; align-items: center; gap: 8px; padding: 0 14px; border-radius: 14px; color: #071521; background: #79caf5; font-size: 11px; font-weight: 800; }
  .support-hero img { position: absolute; right: -42px; bottom: -35px; width: 205px; height: 205px; object-fit: contain; filter: drop-shadow(0 0 20px rgba(87,180,237,.16)); }
  .faq-section { margin-top: 25px; }
  .section-label small { margin: 0; }
  .faq { width: 100%; display: flex; align-items: flex-start; gap: 12px; padding: 16px 15px; border: 1px solid var(--border); border-radius: 18px; background: rgba(7,13,23,.7); text-align: left; }
  .faq + .faq { margin-top: 9px; }
  .faq-number { width: 25px; height: 25px; display: grid; flex: none; place-items: center; border-radius: 9px; color: #80ccf7; background: rgba(80,174,232,.13); font-size: 10px; font-weight: 800; }
  .faq-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; padding-top: 3px; }
  .faq-copy b { font-size: 12px; }
  .faq-copy small { margin-top: 9px; color: #8f9dae; font-size: 10.5px; line-height: 1.5; }
  .faq > i { padding-top: 3px; color: #718094; transition: transform .2s ease; }
  .faq.open > i { transform: rotate(90deg); }

  .profile-card { display: flex; align-items: center; gap: 12px; margin-top: 27px; padding: 15px; border: 1px solid rgba(146,200,242,.16); border-radius: 22px; background: linear-gradient(135deg,rgba(42,115,179,.19),rgba(7,13,23,.78)); }
  .avatar { width: 46px; height: 46px; display: grid; flex: none; place-items: center; border-radius: 16px; color: #07131f; background: linear-gradient(135deg,#b5e6ff,#62b8ec); font-size: 17px; font-weight: 800; }
  .avatar-photo { object-fit: cover; }
  .profile-card > div:nth-child(2) { min-width: 0; display: flex; flex: 1; flex-direction: column; }
  .profile-card strong { font-size: 14px; }
  .profile-card span { margin-top: 3px; color: var(--muted); font-size: 10px; }
  .profile-card > i { color: #7bc7f3; }
  .settings-group { margin-top: 22px; overflow: hidden; border: 1px solid var(--border); border-radius: 22px; background: rgba(7,13,23,.7); }
  .settings-group h2 { padding: 14px 16px 8px; color: #647287; font-size: 9px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
  .setting-row { width: 100%; min-height: 58px; display: flex; align-items: center; gap: 11px; padding: 9px 15px; color: #7e8da0; text-align: left; }
  .setting-row + .setting-row { border-top: 1px solid rgba(255,255,255,.06); }
  .setting-row > i { width: 34px; height: 34px; display: grid; flex: none; place-items: center; border-radius: 12px; color: #83cdf7; background: rgba(80,174,232,.12); }
  .setting-row > i.telegram { color: #57b6ee; }
  .setting-row > span { min-width: 0; display: flex; flex: 1; flex-direction: column; }
  .setting-row b { color: var(--text); font-size: 11.5px; }
  .setting-row small { margin-top: 2px; color: var(--faint); font-size: 9.5px; }
  .setting-row em { color: #6fc3f2; font-size: 10px; font-style: normal; font-weight: 800; }
  .setting-row em.connected { width: 27px; height: 27px; display: grid; place-items: center; border-radius: 10px; color: #092216; background: #71d5a4; }
  button:disabled { cursor: default; opacity: .55; }

  .connect-overlay { position: fixed; z-index: 50; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding-top: var(--safe-top-flow); }
  .connect-backdrop { position: absolute; inset: 0; border-radius: 0; background: rgba(0,3,8,.66); backdrop-filter: blur(8px); }
  .connect-sheet { position: relative; width: min(100%,480px); max-height: calc(100dvh - var(--safe-top-flow) - 12px); overflow-y: auto; padding: 10px 20px calc(24px + var(--safe-bottom-flow)); border: 1px solid rgba(164,210,249,.16); border-bottom: 0; border-radius: 30px 30px 0 0; background: linear-gradient(155deg,rgba(18,35,55,.98),rgba(4,9,17,.99) 42%); box-shadow: 0 -30px 90px rgba(0,0,0,.56),inset 0 1px 0 rgba(255,255,255,.06); }
  .connect-sheet::before { content: ''; display: block; width: 40px; height: 4px; margin: 0 auto 14px; border-radius: 99px; background: rgba(177,207,233,.24); }
  .connect-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
  .connect-head span { color: #72bee9; font-size: 9px; font-weight: 800; letter-spacing: .18em; }
  .connect-head h2 { margin: 5px 0 0; font-size: 24px; line-height: 1.1; letter-spacing: -.045em; }
  .connect-head > button { width: 44px; height: 44px; display: grid; flex: none; place-items: center; border: 1px solid var(--border); border-radius: 15px; color: #8f9caf; background: rgba(255,255,255,.035); }
  .connect-note { max-width: 300px; margin: 12px 0 20px; color: #8c9bad; font-size: 11px; line-height: 1.5; }
  .device-grid { display: grid; gap: 9px; }
  .device-grid > button { position: relative; min-height: 68px; display: flex; align-items: center; gap: 12px; padding: 10px 14px; border: 1px solid var(--border); border-radius: 19px; color: #a6b3c2; background: rgba(5,11,20,.52); text-align: left; }
  .device-grid > button.active { color: #f6f9fc; border-color: rgba(108,192,241,.44); background: linear-gradient(135deg,rgba(86,171,226,.14),rgba(8,17,29,.7)); box-shadow: inset 0 1px 0 rgba(255,255,255,.04); }
  .device-grid i { width: 42px; height: 42px; display: grid; flex: none; place-items: center; border-radius: 14px; color: #8dccf2; background: rgba(76,163,218,.1); }
  .device-grid span { font-size: 12px; font-weight: 800; }
  .device-grid em { width: 26px; height: 26px; display: grid; place-items: center; margin-left: auto; border-radius: 9px; color: #07141f; background: #83cef7; }
  .sheet-primary, .sheet-secondary { width: 100%; min-height: 52px; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 18px; border-radius: 17px; font-size: 12px; font-weight: 800; }
  .sheet-primary { color: #06121e; background: linear-gradient(128deg,#b6e7ff,#69bff0); box-shadow: inset 0 1px 0 rgba(255,255,255,.68),0 18px 42px -26px rgba(74,169,230,.86); }
  .sheet-secondary { color: #8ecff5; border: 1px solid rgba(105,190,244,.36); background: rgba(10,28,46,.3); }
  .sheet-back { min-height: 44px; display: inline-flex; align-items: center; gap: 7px; margin: 10px 0 13px; color: #8e9bad; font-size: 10.5px; font-weight: 800; }
  .empty-connect { display: flex; align-items: center; flex-direction: column; padding: 25px 20px; border: 1px solid var(--border); border-radius: 22px; background: rgba(5,11,20,.5); text-align: center; }
  .empty-connect > :global(.arc-icon) { width: 48px; height: 48px; border-radius: 16px; color: #8fcff4; background: rgba(80,174,232,.11); }
  .empty-connect h3 { margin: 13px 0 6px; font-size: 15px; }
  .empty-connect p { max-width: 290px; margin: 0; color: #8291a3; font-size: 10.5px; line-height: 1.5; }
  .guide-card { display: grid; grid-template-columns: 28px minmax(0,1fr) auto; align-items: center; gap: 10px; min-height: 84px; padding: 13px; border: 1px solid var(--border); border-radius: 20px; background: rgba(5,11,20,.54); }
  .guide-card + .guide-card { margin-top: 9px; }
  .guide-card > i { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 10px; color: #91d3f8; background: rgba(80,174,232,.12); font-size: 10px; font-style: normal; font-weight: 800; }
  .guide-card > div { min-width: 0; display: flex; flex-direction: column; }
  .guide-card b { font-size: 11px; }
  .guide-card small { margin-top: 3px; color: #748397; font-size: 9px; line-height: 1.35; }
  .guide-card > button { min-height: 44px; display: flex; align-items: center; gap: 4px; padding: 0 11px; border-radius: 13px; color: #07141f; background: #7ac8f3; font-size: 9px; font-weight: 800; }
  .connect-success { display: flex; align-items: flex-start; gap: 8px; margin: 14px 2px 0; color: #738296; font-size: 9.5px; line-height: 1.45; }
  .connect-success :global(.arc-icon) { margin-top: 1px; color: #74d2a4; }

  .dock { position: fixed; z-index: 20; left: 50%; bottom: calc(var(--safe-bottom-flow) + 12px); width: min(100%,460px); padding: 0 16px; transform: translateX(-50%); }
  .dock nav { display: flex; gap: 4px; padding: 7px; border: 1px solid rgba(163,207,248,.14); border-radius: 25px; background: rgba(5,11,20,.82); box-shadow: 0 24px 70px -28px rgba(0,0,0,.92),inset 0 1px 0 rgba(255,255,255,.045); backdrop-filter: blur(24px); }
  .dock button { min-width: 0; min-height: 52px; display: grid; flex: 1; place-items: center; border-radius: 18px; color: #8090a3; transition: flex .22s ease, color .22s ease, background .22s ease, transform .12s ease; }
  .dock button.active { flex: 1.18; color: #071321; background: linear-gradient(135deg,#b4e5ff,#64bdf0); box-shadow: inset 0 1px 0 rgba(255,255,255,.66),0 9px 26px -15px rgba(82,180,240,.9); }
  button:focus-visible { outline: 2px solid #9bd9ff; outline-offset: 3px; }
  button:active { transform: scale(.985); }
  /* Arc surfaces: depth comes from tone, never from permanent outlines. */
  .flow-preview { --muted: #adb8c7; --faint: #8290a3; --surface: #0a111b; --surface-raised: #101a27; --hairline: rgba(214,233,255,.07); background: #03070e; }
  .aurora { position: fixed; z-index: -4; inset: 0; overflow: hidden; pointer-events: none; }
  .aurora::after { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse 62% 72% at 50% 48%,#03070e 0 58%,rgba(3,7,14,.98) 69%,rgba(3,7,14,.62) 83%,transparent 100%); }
  .aurora-blob { position: absolute; display: block; opacity: .2; filter: blur(76px); will-change: border-radius, transform; }
  .blob-one { top: -10%; left: -44%; width: 62vw; min-width: 230px; max-width: 360px; height: 58vh; background: #2d78bb; animation: aurora-one 25s ease-in-out infinite alternate; }
  .blob-two { top: 16%; right: -46%; width: 66vw; min-width: 250px; max-width: 390px; height: 62vh; opacity: .17; background: #6bbde9; animation: aurora-two 31s ease-in-out infinite alternate; }
  .blob-three { bottom: -24%; left: 8%; width: 84vw; max-width: 430px; height: 34vh; opacity: .13; background: #245d96; animation: aurora-three 36s ease-in-out infinite alternate; }
  @keyframes aurora-one { 0% { border-radius: 44% 56% 63% 37%/47% 38% 62% 53%; transform: translate3d(-9%,0,0) rotate(-7deg) scale(.93); } 50% { border-radius: 64% 36% 41% 59%/38% 61% 39% 62%; transform: translate3d(5%,38%,0) rotate(12deg) scale(1.05); } 100% { border-radius: 37% 63% 56% 44%/61% 42% 58% 39%; transform: translate3d(-4%,78%,0) rotate(-14deg) scale(.96); } }
  @keyframes aurora-two { 0% { border-radius: 61% 39% 36% 64%/43% 59% 41% 57%; transform: translate3d(7%,-14%,0) rotate(5deg) scale(.9); } 52% { border-radius: 39% 61% 67% 33%/63% 37% 58% 42%; transform: translate3d(-5%,22%,0) rotate(-14deg) scale(1.08); } 100% { border-radius: 55% 45% 39% 61%/35% 56% 44% 65%; transform: translate3d(4%,62%,0) rotate(10deg) scale(.98); } }
  @keyframes aurora-three { 0% { border-radius: 36% 64% 51% 49%/62% 43% 57% 38%; transform: translate3d(-32%,8%,0) rotate(-9deg); } 50% { border-radius: 58% 42% 65% 35%/42% 65% 35% 58%; transform: translate3d(2%,-8%,0) rotate(15deg) scale(1.08); } 100% { border-radius: 47% 53% 34% 66%/57% 39% 61% 43%; transform: translate3d(34%,5%,0) rotate(-5deg) scale(.95); } }

  .flow-preview button, .flow-preview article, .flow-preview section, .flow-preview nav, .flow-preview input, .flow-preview textarea,
  .link-switch, .guide-card, .empty-connect { border: 0; }
  .flow-preview .stat, .flow-preview .shortcut, .flow-preview .referral-hero,
  .flow-preview .support-hero, .flow-preview .metric-grid article, .flow-preview .link-switch,
  .flow-preview .referral-link, .flow-preview .share-referral, .flow-preview .steps,
  .flow-preview .faq, .flow-preview .profile-card,
  .flow-preview .settings-group, .flow-preview .device-summary, .flow-preview .registered-device,
  .flow-preview .preference-list > button, .flow-preview .email-connected,
  .flow-preview .email-form, .flow-preview .agreement, .flow-preview .connect-sheet,
  .flow-preview .device-grid > button, .flow-preview .empty-connect, .flow-preview .guide-card,
  .flow-preview .dock nav, .flow-preview .chat-message, .flow-preview .chat-compose,
  .flow-preview .purchase-config, .flow-preview .purchase-total,
  .flow-preview .plan-card { border: 1px solid var(--hairline); }
  .screen { padding-inline: 20px; }
  .home-screen { padding-top: calc(var(--safe-top-flow) + 120px); }
  .brand { margin-bottom: 25px; filter: none; }
  .brand img { width: 21px; height: 20px; }
  .eyebrow, .expires, .shortcut-copy small, .referral-copy p, .support-hero p, .block-title small, .section-label small, .steps small, .faq-copy small, .profile-card span, .setting-row small, .connect-note, .guide-card small, .connect-success { color: var(--muted); }
  .stat { min-height: 46px; border-radius: 15px; color: #99abc0; background: var(--surface); box-shadow: none; backdrop-filter: blur(16px); }
  .stat small { color: var(--faint); }
  .actions button { border-radius: 18px; }
  .flow-preview .secondary { color: #a8daf7; border: 1px solid rgba(105,190,244,.52); background: transparent; box-shadow: inset 0 1px 0 rgba(255,255,255,.025); backdrop-filter: none; }
  .shortcuts { margin-top: 26px; }
  .shortcut { min-height: 104px; padding: 13px 14px; border-radius: 23px; background: var(--surface); box-shadow: none; backdrop-filter: blur(18px); }
  .shortcut::after, .referral-hero::before, .support-hero::before { display: none; }
  .shortcut::before { display: block; right: -34px; bottom: -42px; width: 158px; height: 132px; border-radius: 50%; opacity: .08; background: radial-gradient(circle,rgba(118,202,247,.82) 0%,rgba(50,116,176,.38) 43%,transparent 74%); filter: blur(48px); }
  .shortcut-copy b { font-size: 13px; }
  .shortcut-copy small { margin-top: 4px; }
  .shortcut-copy i { width: 48px; height: 30px; margin-top: 8px; border: 0; border-radius: 12px; color: #e1edf6; background: rgba(255,255,255,.08); box-shadow: inset 0 1px 0 rgba(255,255,255,.025); }
  .shortcut img { right: -14px; bottom: -18px; width: 116px; height: 116px; filter: drop-shadow(0 14px 18px rgba(0,0,0,.38)); }
  .referral-hero, .support-hero { border-radius: 27px; background: linear-gradient(145deg,#132235,#09111c 62%); box-shadow: none; }
  .referral-hero img, .support-hero img { filter: drop-shadow(0 18px 22px rgba(0,0,0,.3)); }
  .metric-grid article { border-radius: 21px; background: var(--surface); }
  .link-switch { border-radius: 18px; background: var(--surface); }
  .link-switch button { border-radius: 10px; }
  .referral-link { border-radius: 20px; background: var(--surface); color: #c4ced9; }
  .referral-link i { border-radius: 10px; }
  .share-referral { border-radius: 17px; color: #acdafa; background: var(--surface-raised); }
  .referral-stats-link { border: 1px solid var(--hairline); border-radius: 19px; }
  .steps { border-radius: 22px; background: var(--surface); }
  .steps > div + div, .setting-row + .setting-row { border-top: 0; }
  .steps > div + div { margin-top: 2px; }
  .support-hero button { border-radius: 13px; }
  .faq { border-radius: 20px; background: var(--surface); }
  .profile-card { border-radius: 23px; background: linear-gradient(135deg,#132235,#0a121e); }
  .avatar { border-radius: 11px; }
  .settings-group { border-radius: 24px; background: var(--surface); }
  .settings-group h2 { color: #fff; opacity: 1; font-size: 8.5px; font-weight: 500; letter-spacing: .16em; }
  .setting-row { min-height: 62px; }
  .setting-row > i { border-radius: 11px; }
  .setting-row em.connected { border-radius: 8px; }
  .connect-sheet { border-radius: 30px 30px 0 0; background: linear-gradient(155deg,#152436,#060b13 45%); }
  .connect-head > button { border-radius: 13px; background: var(--surface-raised); }
  .device-grid > button { border-radius: 20px; background: var(--surface); }
  .device-grid > button.active { background: #15283a; box-shadow: none; }
  .device-grid i { border-radius: 10px; }
  .sheet-secondary, .empty-connect, .guide-card { background: var(--surface); }
  .empty-connect { border-radius: 22px; }
  .guide-card { border-radius: 20px; }
  .dock nav { border-radius: 27px; background: rgba(8,15,24,.9); box-shadow: 0 24px 70px -28px rgba(0,0,0,.92); }
  .dock button { border-radius: 20px; }

  .subpage-head { position: relative; display: flex; align-items: flex-start; justify-content: center; gap: 12px; }
  .subpage-head > div { width: 100%; text-align: center; }
  .settings-error, .form-message { margin: 14px 0 0; padding: 11px 13px; border-radius: 12px; color: #d8e3ed; background: #172131; font-size: 10.5px; line-height: 1.4; }
  .subpage-intro { margin: 24px 0 18px; color: var(--muted); font-size: 11px; line-height: 1.55; }
  .device-summary { display: grid; grid-template-columns: auto 1fr auto; align-items: baseline; gap: 8px; padding: 18px; border-radius: 23px; background: linear-gradient(135deg,#15273a,#0b141f); }
  .device-summary strong { font-size: 34px; letter-spacing: -.05em; }
  .device-summary span { color: #c8d2dd; font-size: 11px; font-weight: 700; }
  .device-summary small { color: var(--muted); font-size: 9.5px; }
  .device-list { display: grid; gap: 8px; margin-top: 12px; }
  .registered-device { display: flex; align-items: center; gap: 11px; min-height: 70px; padding: 12px; border-radius: 20px; background: var(--surface); }
  .registered-device > i { width: 42px; height: 42px; display: grid; flex: none; place-items: center; border-radius: 10px; color: #9dd9fb; background: #142538; }
  .registered-device > span { min-width: 0; display: flex; flex: 1; flex-direction: column; }
  .registered-device b { font-size: 12px; }
  .registered-device small { margin-top: 3px; overflow: hidden; color: var(--muted); font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
  .registered-device em { max-width: 64px; color: #7392ab; font-size: 8px; font-style: normal; line-height: 1.25; text-align: right; }
  .empty-state { padding: 28px 18px; border-radius: 20px; color: var(--muted); background: var(--surface); font-size: 11px; text-align: center; }
  .subpage-primary { width: 100%; min-height: 52px; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px; border-radius: 17px; color: #07131e; background: linear-gradient(128deg,#b4e5ff,#69bff0); font-size: 12px; font-weight: 800; }
  .preference-list { display: grid; gap: 8px; }
  .preference-list > button { min-height: 72px; display: flex; align-items: center; gap: 14px; padding: 13px 15px; border-radius: 21px; color: var(--text); background: var(--surface); text-align: left; }
  .preference-list span { display: flex; flex: 1; flex-direction: column; }
  .preference-list b { font-size: 12px; }
  .preference-list small { margin-top: 4px; color: var(--muted); font-size: 9.5px; line-height: 1.35; }
  .preference-list > button > i { width: 42px; height: 25px; padding: 3px; border-radius: 12px; background: #26313e; transition: background .2s ease; }
  .preference-list > button > i em { display: block; width: 19px; height: 19px; border-radius: 8px; background: #8996a5; transition: transform .2s ease, background .2s ease; }
  .preference-list > button > i.on { background: #488fbe; }
  .preference-list > button > i.on em { transform: translateX(17px); background: #e6f5ff; }
  .email-connected { display: flex; align-items: center; gap: 12px; padding: 16px; border-radius: 22px; background: var(--surface); }
  .email-connected > i { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 11px; color: #9bd9fc; background: #142538; }
  .email-connected span { min-width: 0; display: flex; flex: 1; flex-direction: column; }
  .email-connected small { color: var(--muted); font-size: 9px; }
  .email-connected b { margin-top: 3px; overflow: hidden; font-size: 12px; text-overflow: ellipsis; }
  .email-connected em { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 8px; color: #082116; background: #6ed39e; }
  .email-form { display: grid; gap: 12px; padding: 16px; border-radius: 23px; background: var(--surface); }
  .email-form label { display: grid; gap: 7px; }
  .email-form label span { color: #aab7c5; font-size: 9.5px; font-weight: 700; }
  .email-form input { width: 100%; min-height: 48px; padding: 0 13px; border-radius: 12px; outline: 0; color: var(--text); background: var(--surface-raised); font: inherit; font-size: 12px; }
  .email-form input:focus { box-shadow: 0 0 0 2px rgba(126,198,239,.55); }
  .email-form > button { min-height: 48px; border-radius: 12px; color: #07131e; background: #8ed3f7; font-size: 11.5px; font-weight: 800; }
  .danger-action { width: 100%; min-height: 48px; margin-top: 10px; border-radius: 15px; color: #f3a4a4; background: #211217; font-size: 11px; font-weight: 800; }
  .agreement { margin-top: 24px; padding: 19px; border-radius: 24px; background: var(--surface); }
  .agreement-meta { display: flex; flex-direction: column; gap: 3px; }
  .agreement-meta span { font-size: 10px; font-weight: 800; }
  .agreement-meta small { color: var(--muted); font-size: 9px; }
  .agreement h2 { margin: 21px 0 10px; font-size: 22px; letter-spacing: -.04em; }
  .agreement h3 { margin: 19px 0 6px; font-size: 12px; }
  .agreement p { margin: 0; color: #b7c1cc; font-size: 10.5px; line-height: 1.58; }
  .agreement button { width: 100%; min-height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 20px; border-radius: 15px; color: #b9e2fb; background: var(--surface-raised); font-size: 11px; font-weight: 800; }
  .login-screen { display: flex; justify-content: center; flex-direction: column; max-width: 460px; margin: auto; padding-bottom: calc(42px + var(--safe-bottom-flow)); }
  .login-screen .brand { justify-content: flex-start; margin-bottom: 42px; }
  .login-copy h1 { margin: 0; font-size: 38px; line-height: 1.04; letter-spacing: -.055em; }
  .login-copy > span { display: block; max-width: 340px; margin-top: 14px; color: var(--muted); font-size: 11px; line-height: 1.55; }
  .login-form { margin-top: 28px; }
  .login-help { margin: 13px 5px 0; color: var(--faint); font-size: 9.5px; line-height: 1.45; }
  .support-chat { display: flex; flex-direction: column; gap: 8px; min-height: calc(100dvh - var(--safe-top-flow) - 250px); padding: 22px 0 176px; }
  .chat-day { width: 100%; display: flex; align-items: center; gap: 10px; color: var(--faint); font-size: 8.5px; font-weight: 700; }
  .chat-day::before, .chat-day::after { content: ''; height: 1px; flex: 1; background: var(--hairline); }
  .chat-day span { padding: 5px 8px; border-radius: 8px; background: var(--surface); }
  .chat-row { width: 100%; display: flex; align-items: flex-end; gap: 8px; }
  .chat-row.mine { justify-content: flex-end; }
  .care-avatar { width: 34px; height: 34px; display: grid; flex: none; place-items: center; overflow: hidden; border: 1px solid rgba(175,220,255,.13); border-radius: 50%; background: radial-gradient(circle at 72% 78%,rgba(79,169,226,.55),transparent 54%),linear-gradient(145deg,#142640,#060b14); box-shadow: 0 10px 24px -14px rgba(54,154,218,.55); }
  .care-avatar img { width: 23px; height: 23px; object-fit: contain; filter: brightness(0) invert(1); }
  .chat-welcome { display: flex; flex-direction: column; max-width: 82%; padding: 13px 14px; border-radius: 18px 18px 18px 7px; background: var(--surface); }
  .chat-welcome b { font-size: 11.5px; }
  .chat-welcome span { margin-top: 5px; color: var(--muted); font-size: 10px; line-height: 1.45; }
  .chat-message { max-width: 82%; padding: 12px 13px 9px; border-radius: 18px 18px 18px 7px; background: #101a27; }
  .chat-message.mine { border-radius: 18px 18px 7px 18px; background: #173c59; }
  .chat-message p { margin: 0; color: #fff; font-size: 11px; font-weight: 500; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }
  .chat-message > b { display: block; margin-bottom: 4px; color: #9bd8fa; font-size: 9.5px; font-weight: 700; }
  .chat-message small { display: block; margin-top: 6px; color: rgba(224,238,249,.7); font-size: 8px; text-align: right; }
  .chat-error { margin: 4px 0; padding: 10px 12px; border-radius: 11px; color: #f0b5b5; background: #211217; font-size: 9.5px; }
  .chat-input-zone { position: fixed; z-index: 19; left: 50%; bottom: calc(var(--safe-bottom-flow) + 87px); width: min(calc(100% - 40px),420px); transform: translateX(-50%); }
  .chat-quick { display: flex; gap: 7px; overflow-x: auto; padding: 0 1px 9px; scrollbar-width: none; }
  .chat-quick::-webkit-scrollbar { display: none; }
  .chat-quick button { min-height: 34px; flex: none; padding: 0 12px; border: 1px solid rgba(177,215,246,.09); border-radius: 11px; color: #dceaf5; background: rgba(10,17,27,.92); font-size: 9px; font-weight: 700; backdrop-filter: blur(18px); }
  .chat-quick button:disabled { opacity: .55; }
  .chat-compose { width: 100%; display: flex; align-items: flex-end; gap: 8px; padding: 7px; border-radius: 20px; background: #111b28; box-shadow: 0 20px 45px rgba(0,0,0,.38); }
  .chat-compose textarea { min-height: 42px; max-height: 116px; flex: 1; resize: none; padding: 12px 10px; outline: 0; color: var(--text); background: transparent; font: inherit; font-size: 11px; line-height: 1.4; }
  .chat-compose textarea::placeholder { color: #738296; }
  .chat-compose > button { width: 42px; height: 42px; display: grid; flex: none; place-items: center; border-radius: 12px; color: #06131e; background: #8bd2f7; }
  .chat-head { position: relative; justify-content: center; text-align: center; }
  .chat-head > div { width: 100%; }
  .chat-head h1 { font-size: 25px; text-align: center; }

  .purchase-screen { max-width: 480px; margin: auto; padding-top: calc(var(--safe-top-flow) + 28px); padding-bottom: calc(var(--safe-bottom-flow) + 40px); }
  .purchase-head { position: relative; min-height: 76px; text-align: center; }
  .purchase-head > div { padding-inline: 0; }
  .purchase-head h1 { margin: 0; font-size: 29px; line-height: 1.06; letter-spacing: -.05em; text-align: center; }
  .purchase-head span { display: block; max-width: 310px; margin: 11px auto 0; color: var(--muted); font-size: 10.5px; line-height: 1.5; }
  .plan-viewport { width: auto; overflow: hidden; margin: 28px -20px 0; }
  .plan-strip { width: 100%; display: flex; gap: 10px; overflow-x: auto; padding: 0 20px 8px; scroll-padding-inline: 20px; scrollbar-width: none; scroll-snap-type: x mandatory; }
  .plan-strip::-webkit-scrollbar { display: none; }
  .plan-card { position: relative; min-width: 0; flex: 0 0 clamp(150px,42vw,188px); min-height: 154px; display: flex; align-items: flex-start; flex-direction: column; padding: 17px; border-radius: 23px; color: var(--text); background: var(--surface); scroll-snap-align: start; text-align: left; transition: background .2s ease, border-color .2s ease, transform .12s ease; }
  .plan-card.active { border-color: rgba(137,211,250,.34); background: linear-gradient(150deg,#152c42,#0b1623 68%); }
  .plan-card > span { font-size: 12px; font-weight: 800; }
  .plan-card em { margin-top: 8px; padding: 5px 7px; border-radius: 8px; color: #a6ddfb; background: rgba(107,191,239,.09); font-size: 8px; font-style: normal; font-weight: 800; }
  .plan-card strong { margin-top: auto; font-size: 25px; line-height: 1; letter-spacing: -.045em; }
  .plan-card small { margin-top: 7px; color: var(--muted); font-size: 9.5px; }
  .plan-card i { position: absolute; top: 14px; right: 14px; width: 24px; height: 24px; display: grid; place-items: center; border-radius: 8px; color: #07131f; background: #91d7fb; }
  .purchase-empty { margin-top: 28px; padding: 24px; border-radius: 22px; color: var(--muted); background: var(--surface); text-align: center; }
  .purchase-config { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 16px; align-items: end; margin-top: 16px; padding: 19px; border-radius: 24px; background: rgba(10,17,27,.9); }
  .config-copy > span { color: #7bc8f2; font-size: 8.5px; font-weight: 800; letter-spacing: .15em; text-transform: uppercase; }
  .config-copy h2 { max-width: 235px; margin: 7px 0 0; font-size: 16px; line-height: 1.25; letter-spacing: -.025em; }
  .config-copy p { max-width: 235px; margin: 10px 0 0; color: var(--muted); font-size: 9.5px; line-height: 1.5; }
  .stepper { display: grid; grid-template-columns: 38px 38px 38px; align-items: center; padding: 4px; border-radius: 16px; background: #101b29; }
  .stepper button { width: 38px; height: 38px; border-radius: 11px; color: #93d9fc; background: #172638; font-size: 20px; font-weight: 500; }
  .stepper button:disabled { color: #506073; background: transparent; opacity: .65; }
  .stepper strong { text-align: center; font-size: 15px; font-variant-numeric: tabular-nums; }
  .stepper.wide { grid-template-columns: 38px 56px 38px; }
  .stepper strong small { margin-left: 2px; color: var(--muted); font-size: 8px; }
  .purchase-total { margin-top: 16px; padding: 17px; border-radius: 25px; background: linear-gradient(150deg,#10263a,#09131e 68%); }
  .total-row { display: flex; align-items: center; justify-content: space-between; min-height: 34px; color: #d8e3ed; }
  .total-row span { display: flex; align-items: center; gap: 9px; font-size: 10.5px; font-weight: 700; }
  .total-row span :global(.arc-icon) { color: #91d4f8; }
  .total-row small { color: var(--muted); font-size: 9.5px; }
  .purchase-total > button { width: 100%; min-height: 56px; display: flex; align-items: center; justify-content: space-between; margin-top: 13px; padding: 0 18px; border-radius: 17px; color: #06131e; background: linear-gradient(128deg,#b7e8ff,#69bff0); box-shadow: inset 0 1px 0 rgba(255,255,255,.65); }
  .purchase-total > button span { font-size: 12px; font-weight: 800; }
  .purchase-total > button strong { font-size: 16px; }
  .purchase-total > p { margin: 9px 2px 0; color: #7790a6; font-size: 8.5px; text-align: center; }
  .purchase-total > button.payment-check { justify-content: center; min-height: 46px; color: #b9e2fb; background: var(--surface-raised); box-shadow: none; }
  .purchase-total > p.payment-message { color: #b7c6d6; font-size: 10px; line-height: 1.45; }
  @media (max-width: 360px) {
    .screen { padding-inline: 16px; }
    .home-screen { padding-top: calc(var(--safe-top-flow) + 96px); }
    .days strong { font-size: 54px; }
    .shortcut { padding-inline: 13px; }
    .shortcut img { width: 108px; height: 108px; }
    .stat { padding-inline: 6px; }
    .referral-hero, .support-hero { padding-inline: 19px; }
    .purchase-config { grid-template-columns: 1fr; }
    .stepper { justify-self: stretch; grid-template-columns: 44px 1fr 44px; }
    .stepper.wide { grid-template-columns: 44px 1fr 44px; }
  }
  @media (prefers-reduced-motion: reduce) {
    .aurora-blob { animation: none; }
    button:active { transform: none; }
  }
</style>
