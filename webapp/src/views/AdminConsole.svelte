<script>
  import { onDestroy, onMount } from 'svelte'
  import ArcIcon from '../components/ArcIcon.svelte'
  import AdminHealth from './admin/AdminHealth.svelte'
  import AdminNodes from './admin/AdminNodes.svelte'
  import AdminSecurity from './admin/AdminSecurity.svelte'
  import AdminBackups from './admin/AdminBackups.svelte'
  import AdminSettings from './admin/AdminSettings.svelte'
  import AdminCatalog from './admin/AdminCatalog.svelte'
  import AdminFinance from './admin/AdminFinance.svelte'
  import AdminUsers from './admin/AdminUsers.svelte'
  import AdminGrowth from './admin/AdminGrowth.svelte'
  import { fetchAdminAccess, fetchAdminOverview, loginAdmin, runAdminNodeDiagnostic, fetchAdminSupportThreads, fetchAdminSupportThread, sendAdminSupportReply } from '../lib/api.js'

  let data = null
  let access = null
  let loading = true
  let error = ''
  let refreshError = ''
  let active = 'overview'
  let password = ''
  let signingIn = false
  let supportThreads = []
  let selectedThread = null
  let supportMessages = []
  let replyBody = ''
  let sendingReply = false
  let supportLoading = false
  let supportError = ''
  let threadLoading = false
  let threadError = ''
  let replyError = ''
  let replyStatus = ''
  let supportQuery = ''
  let supportView = 'list'
  let pendingThreadId = null
  let threadRequest = 0
  let refreshTimer = null
  let lastUpdated = null
  let diagnosticNode = ''
  let diagnostics = {}
  let overviewPeriod = 'day'
  const nav = [
    ['overview', 'home', 'Главная', 'overview.read'], ['health', 'pulse', 'Здоровье', 'overview.read'],
    ['nodes', 'devices', 'Ноды', 'overview.read'],
    ['catalog', 'route', 'Каталог подписки', 'overview.read'], ['users', 'users', 'Пользователи', 'overview.read'], ['growth', 'signal', 'Growth', 'overview.read'], ['payments', 'wallet', 'Финансы', 'overview.read'],
    ['support', 'headset', 'Поддержка', 'support.read'], ['security', 'shield', 'Безопасность', 'audit.read'],
    ['backups', 'file', 'Резервные копии', 'backups.read'], ['settings', 'settings', 'Настройки', 'overview.read'],
  ]
  const exposedPermissions = ['overview.read', 'nodes.diagnose', 'catalog.manage', 'subscriptions.manage', 'campaigns.manage', 'promocodes.manage', 'expenses.manage', 'support.read', 'support.reply', 'audit.read', 'backups.read', 'backups.create', 'roles.manage']
  const roleLabels = { owner: ['Владелец', 'Полный доступ'], operator: ['Оператор', 'Операционный доступ'], support: ['Поддержка', 'Обращения пользователей'], finance: ['Финансы', 'Финансовый доступ'], viewer: ['Наблюдатель', 'Только чтение'] }
  const allows = (permission, source = access) => Boolean(source && (source.permissions?.includes('*') || source.permissions?.includes(permission)))
  $: visibleNav = nav.filter((item) => allows(item[3], access))
  $: effectiveAccess = Object.fromEntries(exposedPermissions.map((permission) => [permission, allows(permission, access)]))
  $: roleLabel = roleLabels[access?.role] || ['Администратор', 'Ограниченный доступ']
  const rub = (v) => `${new Intl.NumberFormat('ru-RU').format(Number(v || 0))} ₽`
  const num = (v) => new Intl.NumberFormat('ru-RU').format(Number(v || 0))
  const bytes = (value) => {
    const amount = Math.max(0, Number(value || 0))
    if (amount >= 1024 ** 4) return `${(amount / 1024 ** 4).toFixed(2)} ТБ`
    if (amount >= 1024 ** 3) return `${(amount / 1024 ** 3).toFixed(1)} ГБ`
    return `${(amount / 1024 ** 2).toFixed(0)} МБ`
  }
  const periodLabel = { day: '24 часа', week: '7 дней', month: '30 дней' }
  const feedbackLabels = { great:'Всё отлично', connection:'Подключение', speed:'Скорость', service:'Нужный сервис', setup:'Настройка', other:'Другое', legacy:'Старые оценки' }
  const feedbackLabel = (answer='') => feedbackLabels[String(answer).split(':',1)[0]] || ({'1':'Старая оценка 1/5','3':'Старая оценка 3/5','5':'Старая оценка 5/5'})[answer] || answer
  const productLabel = (item) => ({ economy: 'Эконом', standard: 'Стандарт', family: 'Семейный' })[item?.product_code] || item?.product_name || 'Другой тариф'
  const supportName = (thread) => thread?.first_name || (thread?.username ? `@${thread.username}` : `ID ${thread?.telegram_id || thread?.id || '—'}`)
  $: filteredSupportThreads = supportThreads.filter((thread) => `${supportName(thread)} ${thread.last_message || ''}`.toLocaleLowerCase('ru-RU').includes(supportQuery.trim().toLocaleLowerCase('ru-RU')))

  async function load(silent = false) {
    if (!allows('overview.read')) return
    if (!silent) loading = true
    if (!silent) error = ''
    try {
      data = await fetchAdminOverview()
      lastUpdated = new Date()
      refreshError = ''
    } catch (e) {
      if (silent && data) refreshError = 'Не удалось обновить сводку. Показываем последние полученные данные.'
      else error = e.code === 403 ? 'auth' : 'Данные временно недоступны'
    } finally { loading = false }
  }
  async function bootstrap() {
    loading = true
    error = ''
    refreshError = ''
    try {
      access = await fetchAdminAccess()
      if (allows('overview.read', access)) {
        active = 'overview'
        await load()
      } else if (allows('support.read', access)) {
        active = 'support'
        loading = false
        await openSupport()
      } else {
        loading = false
        error = 'forbidden'
      }
    } catch (e) {
      access = null
      loading = false
      error = e.code === 401 || e.code === 403 ? 'auth' : 'Не удалось проверить права доступа'
    }
  }
  function openSection(section) {
    if (!visibleNav.some((item) => item[0] === section)) return
    if (section === 'support') openSupport()
    else active = section
  }
  async function signIn() {
    if (!password || signingIn) return
    signingIn = true; error = ''
    try {
      const session = await loginAdmin(password)
      password = ''
      access = { ok: true, role: session.role || 'owner', permissions: session.permissions || ['*'] }
      active = 'overview'
      loading = true
      await load()
    }
    catch (e) { error = e.code === 429 ? 'Слишком много попыток. Подождите 15 минут.' : 'Неверный пароль' }
    finally { signingIn = false }
  }
  async function runDiagnostic(node) {
    if (diagnosticNode || !allows('nodes.diagnose')) return
    diagnosticNode = node.uuid
    try { diagnostics = { ...diagnostics, [node.uuid]: (await runAdminNodeDiagnostic(node.uuid)).diagnostic } }
    catch (e) { diagnostics = { ...diagnostics, [node.uuid]: { ok: false, error: e.reason || 'Ошибка диагностики' } } }
    finally { diagnosticNode = '' }
  }
  async function openSupport() {
    if (!allows('support.read')) return
    active = 'support'
    supportView = 'list'
    supportLoading = true
    supportError = ''
    replyStatus = ''
    try {
      const result = await fetchAdminSupportThreads()
      supportThreads = result.threads || []
      const preserved = supportThreads.find((thread) => thread.id === selectedThread?.id)
      if (!supportThreads.length) {
        selectedThread = null
        supportMessages = []
      } else if (preserved) {
        await selectThread(preserved.id, false)
      } else {
        await selectThread(supportThreads[0].id, false)
      }
    } catch (e) {
      supportError = 'Не удалось загрузить обращения. Проверьте соединение и повторите попытку.'
    } finally {
      supportLoading = false
    }
  }
  async function selectThread(id, showDetail = true) {
    if (!id) return
    const request = ++threadRequest
    pendingThreadId = id
    threadLoading = true
    threadError = ''
    replyError = ''
    replyStatus = ''
    if (showDetail) supportView = 'detail'
    try {
      const result = await fetchAdminSupportThread(id)
      if (request !== threadRequest) return
      selectedThread = result.thread
      supportMessages = result.messages || []
      supportThreads = supportThreads.map((thread) => thread.id === id ? { ...thread, unread: 0 } : thread)
    } catch (e) {
      if (request !== threadRequest) return
      selectedThread = null
      supportMessages = []
      threadError = 'Диалог не открылся. Повторите загрузку.'
    } finally {
      if (request === threadRequest) {
        threadLoading = false
        if (!threadError) pendingThreadId = null
      }
    }
  }
  async function sendReply() {
    const body = replyBody.trim()
    const threadId = selectedThread?.id
    if (!threadId || !body || sendingReply || !allows('support.reply')) return
    sendingReply = true
    replyError = ''
    replyStatus = 'Отправляем ответ…'
    try {
      await sendAdminSupportReply(threadId, body)
      replyBody = ''
      replyStatus = 'Ответ отправлен и добавлен в диалог.'
      supportThreads = supportThreads.map((thread) => thread.id === threadId ? { ...thread, last_message: body } : thread)
      await selectThread(threadId, false)
      replyStatus = 'Ответ отправлен и добавлен в диалог.'
    } catch (e) {
      replyError = 'Ответ не отправлен. Текст сохранён — попробуйте ещё раз.'
      replyStatus = ''
    } finally {
      sendingReply = false
    }
  }
  onMount(() => {
    document.body.classList.add('admin-console-open')
    bootstrap()
    refreshTimer = setInterval(() => { if (allows('overview.read')) load(true) }, 30000)
  })
  onDestroy(() => {
    document.body.classList.remove('admin-console-open')
    if (refreshTimer) clearInterval(refreshTimer)
  })
</script>

<svelte:head><title>ArcVPN Admin</title></svelte:head>

<div class="console">
  <aside>
    <a class="brand" href="/admin"><img src="/app/arc-logo-new.webp" alt="" /><span>ArcVPN</span></a>
    <nav aria-label="Разделы админ-панели">{#each visibleNav as item}<button class:active={active === item[0]} aria-current={active === item[0] ? 'page' : undefined} aria-label={item[2]} on:click={() => openSection(item[0])} title={item[2]}><ArcIcon name={item[1]} size={20} weight="duotone" /><span>{item[2]}</span></button>{/each}</nav>
    {#if access}<div class="owner"><i>{roleLabel[0][0]}</i><span>{roleLabel[0]}<small>{roleLabel[1]}</small></span></div>{/if}
  </aside>

  <main class={`section-${active}`}>
    <header><div><h1>{active === 'overview' ? 'Главная' : visibleNav.find(item => item[0] === active)?.[2] || 'ArcVPN'}</h1></div><div class="live-tools"><span class="telemetry-fresh" class:stale={refreshError} aria-live="polite"><i></i>{refreshError || (lastUpdated ? `Обновлено ${lastUpdated.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'})}` : allows('overview.read', access) ? 'Подключаем данные' : 'Доступ к сводке ограничен')}</span><button class="refresh" disabled={active === 'support' ? supportLoading : !allows('overview.read', access)} aria-label={active === 'support' ? 'Обновить обращения' : 'Проверить данные'} on:click={() => active === 'support' ? openSupport() : load(true)}><ArcIcon name="pulse" size={18} />{active === 'support' ? 'Обновить' : 'Проверить'}</button></div></header>
    {#if loading}
      <section class="state"><i class="loader"></i><p>Собираем показатели ArcVPN…</p></section>
    {:else if error}
      <section class="state login-card">
        <img src="/app/arc-logo-new.webp" alt="" />
        <h2>Вход в ArcVPN Admin</h2>
        <p>{error === 'auth' ? 'Введите пароль владельца или откройте панель из Telegram.' : error === 'forbidden' ? 'Для вашей роли пока нет доступных разделов.' : error}</p>
        <form on:submit|preventDefault={signIn}>
          <input bind:value={password} type="password" autocomplete="current-password" placeholder="Пароль" aria-label="Пароль" />
          <button disabled={signingIn || !password}>{signingIn ? 'Проверяем…' : 'Войти'}</button>
        </form>
      </section>
    {:else if active === 'users'}
      <AdminUsers users={data?.recent_users || []} canManage={allows('subscriptions.manage', access)} onRefresh={() => load(true)} />
    {:else if active === 'payments'}
      <AdminFinance {data} canManage={allows('expenses.manage', access)} />
    {:else if active === 'growth'}
      <AdminGrowth canManageCampaigns={allows('campaigns.manage', access)} canManagePromocodes={allows('promocodes.manage', access)} />
    {:else if active === 'catalog'}
      <AdminCatalog canManage={allows('catalog.manage', access)} />
    {:else if active === 'health'}
      <AdminHealth {data} onRefresh={() => load(true)} />
    {:else if active === 'nodes'}
      <AdminNodes {data} {diagnostics} {diagnosticNode} onDiagnostic={runDiagnostic} />
    {:else if active === 'security'}
      <AdminSecurity {data} canViewAudit={allows('audit.read', access)} />
    {:else if active === 'backups'}
      <AdminBackups canCreate={allows('backups.create', access)} />
    {:else if active === 'settings'}
      <AdminSettings {data} {effectiveAccess} canManageRoles={allows('roles.manage', access)} currentRole={access?.role} />
    {:else if active === 'support'}
      <section class:detail-open={supportView === 'detail'} class="support-workspace" aria-label="Рабочее пространство поддержки">
        <aside class="thread-list" aria-label="Обращения пользователей">
          <div class="support-list-head">
            <div><span class="eyebrow">Очередь обращений</span><h2>Диалоги <small>{supportThreads.length}</small></h2></div>
            <button class="support-icon-button" on:click={openSupport} disabled={supportLoading} aria-label="Обновить список обращений" title="Обновить список"><span aria-hidden="true">↻</span></button>
          </div>
          <label class="support-search"><span class="sr-only">Поиск по обращениям</span><input bind:value={supportQuery} type="search" placeholder="Имя или текст сообщения" autocomplete="off" /></label>
          <div class="support-list-status" aria-live="polite">{#if supportLoading}<i class="support-spinner" aria-hidden="true"></i><span>Загружаем обращения…</span>{/if}</div>
          {#if supportError}
            <div class="support-state error" role="alert"><b>Очередь недоступна</b><p>{supportError}</p><button on:click={openSupport}>Повторить</button></div>
          {:else if !supportLoading && !supportThreads.length}
            <div class="support-state"><ArcIcon name="headset" size={24} /><b>Новых обращений нет</b><p>Здесь появятся диалоги пользователей.</p></div>
          {:else if !supportLoading && supportQuery && !filteredSupportThreads.length}
            <div class="support-state"><b>Ничего не найдено</b><p>Измените запрос или очистите поиск.</p><button on:click={() => supportQuery = ''}>Очистить поиск</button></div>
          {:else}
            <div class="thread-items" aria-label="Список диалогов">
              {#each filteredSupportThreads as thread}
                <button disabled={sendingReply} class:active={(pendingThreadId || selectedThread?.id) === thread.id} aria-current={(pendingThreadId || selectedThread?.id) === thread.id ? 'true' : undefined} on:click={() => selectThread(thread.id)}>
                  <i aria-hidden="true">{supportName(thread)[0]}</i><span><b>{supportName(thread)}</b><small>{thread.last_message || 'Сообщений пока нет'}</small></span>{#if thread.unread}<em aria-label={`Непрочитанных: ${thread.unread}`}>{thread.unread}</em>{/if}
                </button>
              {/each}
            </div>
          {/if}
        </aside>
        <section class="admin-chat" aria-label="Выбранный диалог">
          {#if threadLoading}
            <div class="support-state conversation-state" aria-live="polite"><i class="support-spinner" aria-hidden="true"></i><b>Открываем диалог…</b><p>Загружаем актуальную историю сообщений.</p></div>
          {:else if threadError}
            <div class="support-state conversation-state error" role="alert"><b>Диалог недоступен</b><p>{threadError}</p><button on:click={() => selectThread(pendingThreadId || selectedThread?.id || supportThreads[0]?.id)}>Повторить</button><button class="quiet" on:click={() => supportView = 'list'}>К списку</button></div>
          {:else if selectedThread}
            <header class="conversation-head"><button class="support-back" on:click={() => supportView = 'list'} aria-label="Вернуться к списку обращений">← <span>Обращения</span></button><div><b>{supportName(selectedThread)}</b><small>{selectedThread.username ? `@${selectedThread.username}` : `Telegram ID ${selectedThread.telegram_id}`}</small></div><span class="conversation-badge">Диалог</span></header>
            <div class="chat-messages" aria-label="История сообщений">
              {#if supportMessages.length}
                {#each supportMessages as message}<article class:admin={message.sender==='admin'}><span>{message.body}</span><small>{message.sender === 'admin' ? 'ArcVPN · ' : ''}{message.created_at}</small></article>{/each}
              {:else}
                <div class="support-state conversation-empty"><b>История пуста</b><p>Начните диалог первым ответом.</p></div>
              {/if}
            </div>
            <form class="reply-box" on:submit|preventDefault={sendReply} aria-busy={sendingReply}>
              <label for="support-reply">Ответ пользователю</label>
              <textarea id="support-reply" bind:value={replyBody} placeholder={allows('support.reply', access) ? 'Введите сообщение…' : 'Ответы недоступны для вашей роли'} maxlength="4000" aria-describedby="reply-help reply-status" disabled={!allows('support.reply', access)}></textarea>
              <div class="reply-meta"><small id="reply-help">{allows('support.reply', access) ? `${replyBody.length}/4000 · Enter переносит строку` : 'Доступ только для чтения'}</small><button disabled={sendingReply || !replyBody.trim() || !allows('support.reply', access)}>{sendingReply ? 'Отправляем…' : 'Отправить'}</button></div>
              <p id="reply-status" class:error-text={replyError} class="reply-status" aria-live="polite">{replyError || replyStatus}</p>
            </form>
          {:else}
            <div class="support-state conversation-state"><ArcIcon name="headset" size={28} /><b>Выберите обращение</b><p>Откройте диалог из очереди слева.</p><button class="mobile-list-action" on:click={() => supportView = 'list'}>Показать обращения</button></div>
          {/if}
        </section>
      </section>
    {:else if active !== 'overview'}
      <section class="state"><ArcIcon name="gift" size={30} /><h2>{nav.find(i => i[0] === active)?.[2]}</h2><p>Раздел готовится к следующему обновлению.</p></section>
    {:else}
      <section class:alert={!data.remnawave?.healthy || data.remnawave?.nodes?.some(node=>!node.connected && !node.disabled)} class="health"><i></i><div><b>{data.remnawave?.healthy ? 'Сеть ArcVPN работает штатно' : 'Требуется внимание к сети'}</b><span>{data.remnawave?.nodes?.filter(node=>node.connected).length || 0} из {data.remnawave?.nodes?.filter(node=>!node.disabled).length || 0} RemnaNode подключены · данные {lastUpdated ? lastUpdated.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}) : 'загружаются'}</span></div><strong>{data.remnawave?.healthy ? 'Remnawave online' : data.remnawave?.detail || 'Нет подтверждения'}</strong></section>
      <nav class="periods" aria-label="Период показателей">{#each [['day','24 часа'],['week','7 дней'],['month','30 дней']] as period}<button class:active={overviewPeriod===period[0]} aria-pressed={overviewPeriod===period[0]} on:click={()=>overviewPeriod=period[0]}>{period[1]}</button>{/each}</nav>
      <section class="metrics">
        <article><span>Новые пользователи</span><strong>{num(data.users?.[overviewPeriod])}</strong><small>за {periodLabel[overviewPeriod]}</small></article>
        <article><span>Успешные оплаты</span><strong>{num(data.business?.payments?.[overviewPeriod]?.orders)}</strong><small>{num(data.business?.payments?.[overviewPeriod]?.paying_users)} покупателей</small></article>
        <article><span>Выручка</span><strong>{rub(data.business?.payments?.[overviewPeriod]?.revenue_rub)}</strong><small>подтверждённые оплаты · {periodLabel[overviewPeriod]}</small></article>
        <article><span>Сейчас онлайн</span><strong>{num(data.remnawave?.online_users?.length || 0)}</strong><small>уникальные пользователи Remnawave за 3 минуты</small></article>
      </section>
      <div class="overview-grid">
        <section class="panel acquisition-panel">
          <div class="panel-head"><div><span>Привлечение</span><h2>Откуда приходят люди</h2></div><button on:click={() => openSection('growth')}>Подробнее <ArcIcon name="arrow" size={16} /></button></div>
          <div class="source-grid"><article><b>{num(data.business?.acquisition?.[overviewPeriod]?.referral_arrivals)}</b><span>по рефералам</span></article><article><b>{num(data.business?.acquisition?.[overviewPeriod]?.campaign_arrivals)}</b><span>по рекламным ссылкам</span></article><article><b>{num(data.business?.acquisition?.[overviewPeriod]?.direct_arrivals)}</b><span>напрямую</span></article></div>
        </section>
        <section class="panel product-panel">
          <div class="panel-head"><div><span>Продажи · 30 дней</span><h2>Что покупают</h2></div></div>
          <div class="product-list">{#if data.business?.popular_products?.length}{#each data.business.popular_products.slice(0,4) as product}<article><span><b>{productLabel(product)}</b><small>{num(product.buyers)} покупателей · {rub(product.revenue_rub)}</small></span><strong>{num(product.orders)}</strong></article>{/each}{:else}<p class="empty-copy">Успешных оплат за период пока нет.</p>{/if}</div>
        </section>
        <section class="panel traffic-panel">
          <div class="panel-head"><div><span>Текущие циклы активных подписок</span><h2>Потребление трафика</h2></div></div>
          <div class="traffic-grid"><article><span>Основные профили</span><b>{bytes(data.business?.traffic?.main_used_bytes)}</b><small>кэш Remnawave по активным ключам</small></article><article><span>Обход глушилок LTE</span><b>{bytes(data.business?.traffic?.lte_used_bytes)}</b><small>отдельные LTE-идентичности</small></article></div>
        </section>
        <section class="panel rating-panel">
          <div class="panel-head"><div><span>Через день после пробника</span><h2>Что нужно улучшить</h2></div><strong>{num(data.trial_rating_feedback?.answered)}</strong></div>
          <div class="rating-summary"><article><b>{num(data.trial_rating_feedback?.sent)}</b><span>отправлено</span></article><article><b>{num(data.trial_rating_feedback?.answered)}</b><span>ответили</span></article><article><b>{Number(data.trial_rating_feedback?.response_rate || 0).toLocaleString('ru-RU')}%</b><span>доля ответов</span></article></div>
          <div class="rating-distribution" aria-label="Причины обратной связи">{#each Object.entries(data.trial_rating_feedback?.distribution || {}) as [reason,count]}{#if count}<span>{feedbackLabels[reason] || reason} — {num(count)}</span>{/if}{/each}</div>
          <div class="rating-responses">{#if data.trial_rating_feedback?.recent?.length}{#each data.trial_rating_feedback.recent.slice(0,5) as response}<article><span><b>{response.first_name || (response.username ? `@${response.username}` : `ID ${response.telegram_id}`)}</b><small>{response.answered_at}</small></span><strong>{feedbackLabel(response.answer)}</strong></article>{/each}{:else}<p class="empty-copy">Ответов пока нет.</p>{/if}</div>
        </section>
        <section class="panel node-panel">
          <div class="panel-head"><div><span>Remnawave · реальные апстримы</span><h2>Ноды сети</h2></div><button on:click={() => openSection('nodes')}>Все ноды <ArcIcon name="arrow" size={16} /></button></div>
          <div class="nodes">{#if data.remnawave?.nodes?.length}{#each data.remnawave.nodes.filter(node=>!node.disabled) as node}<article><div class="node-name"><i class:offline={!node.connected}></i><div><b>{node.name}</b><span>{node.connected ? `${node.country || node.address || 'Подключена'}${node.uptime_seconds ? ` · uptime ${Math.floor(node.uptime_seconds/3600)} ч` : ''}` : node.last_status_message || 'Нет связи с RemnaNode'}</span></div></div><strong>{node.users_online == null ? '—' : num(node.users_online)}</strong><small>{node.users_online == null ? 'нет данных online' : 'пользователей онлайн'}</small></article>{/each}{:else}<p class="empty-copy">Remnawave не вернула список нод.</p>{/if}</div>
        </section>
        <section class="panel queue">
          <div class="panel-head"><div><span>Рабочая очередь</span><h2>Требует внимания</h2></div></div>
          {#if allows('overview.read', access)}<button on:click={() => openSection('payments')}><i><ArcIcon name="wallet" size={18} /></i><span><b>Незавершённые платежи</b><small>Открыть список операций</small></span><strong>{data.operations.pending_payments}</strong></button>{/if}
          <button on:click={() => openSection('settings')}><i class="green"><ArcIcon name="pulse" size={18} /></i><span><b>Автопродления</b><small>{data.recurring.provider_ready ? 'Активные способы оплаты' : 'YooKassa ещё не согласовала опцию'}</small></span><strong>{data.recurring.active}</strong></button>
          {#if allows('support.read', access)}<button on:click={openSupport}><i class="violet"><ArcIcon name="headset" size={18} /></i><span><b>Открытые обращения</b><small>Пользователи ждут ответа</small></span><strong>{data.operations.open_support_threads}</strong></button>{/if}
          <button on:click={() => openSection('users')}><i class="green"><ArcIcon name="users" size={18} /></i><span><b>Новые пользователи</b><small>За последние 24 часа</small></span><strong>{data.users.day}</strong></button>
        </section>
      </div>
    {/if}
  </main>
</div>

<style>
  :global(html:has(body.admin-console-open)),:global(body.admin-console-open){height:100%;overflow:hidden}:global(body.admin-console-open){margin:0;background:#050a12;color:#f4f8fc}.console{--card:#0c1522;--line:rgba(162,207,244,.1);height:100vh;overflow:hidden;display:grid;grid-template-columns:250px 1fr;font-family:Inter,system-ui,sans-serif;background:radial-gradient(900px 600px at 95% -10%,rgba(65,146,214,.16),transparent 65%),#050a12}
  aside{position:sticky;top:0;height:100vh;box-sizing:border-box;display:flex;flex-direction:column;padding:28px 20px;border-right:1px solid var(--line);background:rgba(5,10,18,.76);backdrop-filter:blur(20px)}.brand{display:flex;align-items:center;gap:12px;padding:0 10px 28px;color:#fff;text-decoration:none;font-weight:800}.brand img{width:34px}.brand span,.owner span{display:flex;flex-direction:column}.brand small,.owner small{margin-top:2px;color:#70859a;font-size:10px;text-transform:uppercase;letter-spacing:.08em}
  nav{display:grid;gap:8px}nav button{display:flex;align-items:center;gap:13px;min-height:48px;padding:0 15px;border:0;border-radius:16px;color:#8499ad;background:transparent;font-weight:700;cursor:pointer;transition:.2s}nav button:hover{color:#dceeff;background:rgba(126,194,241,.06);transform:translateX(2px)}nav button.active{color:#08111d;background:#9bd9ff;box-shadow:0 10px 30px rgba(89,174,230,.18)}.owner{margin-top:auto;display:flex;align-items:center;gap:11px;padding:13px;border-radius:18px;background:#0b1420}.owner>i{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#17314a;color:#9bd9ff;font-style:normal;font-weight:800}
  main{width:min(1320px,calc(100% - 64px));margin:0 auto;padding:48px 0 72px}header{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:32px}h1{margin:8px 0 0;font-size:clamp(34px,4vw,60px);line-height:.98;letter-spacing:-.055em}.eyebrow,.panel-head span{color:#6f879d;font-size:11px;font-weight:800;letter-spacing:.11em;text-transform:uppercase}.refresh{display:flex;align-items:center;gap:8px;min-height:44px;padding:0 18px;border:1px solid var(--line);border-radius:22px;background:#0b1420;color:#bcd0e2;font-weight:700;cursor:pointer}
  .live-tools{display:flex;align-items:center;gap:12px}.telemetry-fresh{display:flex;align-items:center;gap:8px;color:#7890a5;font-size:11px;font-weight:700}.telemetry-fresh i{width:7px;height:7px;border-radius:50%;background:#61d8a5;box-shadow:0 0 0 6px rgba(97,216,165,.07)}
  .health{display:flex;align-items:center;gap:14px;padding:18px 22px;border:1px solid rgba(109,213,170,.12);border-radius:22px;background:linear-gradient(90deg,rgba(49,140,108,.13),rgba(12,21,34,.88))}.health>i{width:10px;height:10px;border-radius:50%;background:#61d8a5;box-shadow:0 0 0 7px rgba(97,216,165,.08)}.health div{display:flex;flex:1;flex-direction:column;gap:3px}.health span{color:#8096aa;font-size:12px}.health>strong{padding:8px 12px;border-radius:14px;background:rgba(97,216,165,.09);color:#78e1b4;font-size:12px}.health.alert>i{background:#ff7979}
  .periods{display:flex;width:max-content;gap:4px;margin:16px 0 0;padding:4px;border:1px solid var(--line);border-radius:14px;background:#0b1119}.periods button{min-height:36px;border:0;border-radius:10px;padding:0 14px;background:transparent;color:#7890a5;font-weight:800;cursor:pointer}.periods button.active{background:#17314a;color:#dff3ff}
  .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.metrics article,.panel{border:1px solid var(--line);background:linear-gradient(145deg,rgba(14,26,41,.96),rgba(8,15,25,.96))}.metrics article{min-height:120px;padding:22px;border-radius:24px;display:flex;flex-direction:column}.metrics span,.metrics small{color:#7890a5;font-size:12px}.metrics strong{margin:auto 0 5px;font-size:30px;letter-spacing:-.045em}.metrics small{color:#9bd9ff}
  .overview-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));align-items:start;gap:16px}.acquisition-panel,.product-panel{grid-column:span 6}.traffic-panel{grid-column:1/-1}.rating-panel{grid-column:1/-1}.node-panel{grid-column:span 7}.queue{grid-column:span 5}.panel{padding:24px;border-radius:28px}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}h2{margin:6px 0 0;font-size:21px}.panel-head button{display:flex;align-items:center;gap:6px;border:0;background:transparent;color:#8fcdf5;cursor:pointer}.nodes{display:grid;grid-template-columns:1fr 1fr;gap:12px}.nodes article{padding:18px;border-radius:20px;background:rgba(4,10,18,.56)}.node-name{display:flex;align-items:center;gap:9px}.node-name>i{width:8px;height:8px;border-radius:50%;background:#60d7a4}.node-name>i.offline{background:#ff7474}.node-name div{display:flex;flex-direction:column}.node-name span,.nodes small{color:#6f8497;font-size:11px}.nodes article>strong{display:block;margin-top:24px;font-size:27px}.bar{height:4px;margin-top:14px;border-radius:2px;background:#162534;overflow:hidden}.bar i{display:block;height:100%;background:#91d6ff}
  .source-grid,.traffic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.traffic-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.source-grid article,.traffic-grid article{display:grid;gap:6px;padding:17px;border-radius:16px;background:#0b1119}.source-grid b,.traffic-grid b{font-size:25px}.source-grid span,.traffic-grid span,.traffic-grid small{color:#7890a5;font-size:11px}.product-list{display:grid}.product-list article{display:flex;align-items:center;gap:12px;padding:11px 0;border-top:1px solid var(--line)}.product-list article span{display:grid;flex:1;gap:4px}.product-list small,.empty-copy{color:#7890a5;font-size:11px}.product-list strong{display:grid;min-width:34px;height:34px;place-items:center;border-radius:11px;background:#17314a;color:#bfe8ff}
  .rating-panel>.panel-head>strong{color:#9bd9ff;font-size:24px}.rating-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.rating-summary article{display:grid;gap:5px;padding:14px;border-radius:15px;background:#0b1119}.rating-summary b{font-size:23px}.rating-summary span,.rating-distribution,.rating-responses small{color:#7890a5;font-size:11px}.rating-distribution{display:flex;gap:16px;padding:14px 2px;border-bottom:1px solid var(--line)}.rating-responses article{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)}.rating-responses article:last-child{border-bottom:0}.rating-responses article span{display:grid;flex:1;gap:3px}.rating-responses article>strong{color:#9bd9ff}
  .queue>button{width:100%;display:flex;align-items:center;gap:12px;padding:13px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:#dbe8f3;text-align:left}.queue>button:last-child{border-bottom:0}.queue button>i{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;color:#9bd9ff;background:#102942}.queue button>i.violet{color:#c2afff;background:#211b3b}.queue button>i.green{color:#79deb2;background:#102d27}.queue button span{display:flex;flex:1;flex-direction:column;gap:3px}.queue button small{color:#70879b}.queue button>strong{display:grid;place-items:center;min-width:32px;height:32px;border-radius:50%;background:#122131}
  .state{min-height:55vh;display:grid;place-content:center;justify-items:center;text-align:center;color:#8196a9}.state h2{color:#fff}.loader{width:34px;height:34px;border:3px solid #183047;border-top-color:#9bd9ff;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
  .login-card{min-height:0;width:min(440px,calc(100% - 48px));margin:12vh auto 0;padding:40px 32px;border:1px solid var(--line);border-radius:30px;background:linear-gradient(145deg,rgba(14,26,41,.98),rgba(8,15,25,.98));box-shadow:0 32px 90px rgba(0,0,0,.35)}.login-card>img{width:48px}.login-card p{max-width:340px;line-height:1.5}.login-card form{width:100%;display:grid;gap:12px;margin-top:14px}.login-card input,.login-card button{box-sizing:border-box;width:100%;min-height:52px;border-radius:18px;font:inherit}.login-card input{border:1px solid var(--line);padding:0 17px;background:#07101b;color:#fff;outline:none}.login-card input:focus{border-color:rgba(155,217,255,.55);box-shadow:0 0 0 4px rgba(155,217,255,.07)}.login-card button{border:0;background:#9bd9ff;color:#07111d;font-weight:800;cursor:pointer}.login-card button:disabled{opacity:.55}
  @media(max-width:900px){.console{grid-template-columns:76px 1fr}aside{padding:20px 10px}.brand span,nav span,.owner span{display:none}.brand{justify-content:center;padding-inline:0}nav button{justify-content:center;padding:0}.owner{justify-content:center;background:transparent}.metrics{grid-template-columns:1fr 1fr}.acquisition-panel,.product-panel,.traffic-panel,.node-panel,.queue{grid-column:1/-1}main{width:calc(100% - 32px);padding-top:28px}}
  @media(max-width:560px){.console{display:block}aside{position:fixed;z-index:10;top:auto;bottom:12px;left:12px;right:12px;height:64px;flex-direction:row;padding:8px;border:1px solid var(--line);border-radius:24px}.brand,.owner{display:none}nav{display:flex;width:100%;justify-content:flex-start;gap:4px;overflow-x:auto;overflow-y:hidden;overscroll-behavior-x:contain;scrollbar-width:none}nav button{flex:0 0 48px;width:48px;min-height:48px;border-radius:18px}main{padding:26px 0 100px}header{align-items:flex-start}.refresh{width:44px;padding:0;justify-content:center;font-size:0}.health>strong{display:none}.metrics{gap:10px}.metrics article{min-height:105px;padding:17px}.metrics strong{font-size:24px}.nodes{grid-template-columns:1fr}.panel{padding:19px;border-radius:24px}}
  main{box-sizing:border-box;height:100vh;overflow-y:auto;scrollbar-width:none}main::-webkit-scrollbar{display:none}
  .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.support-workspace{height:min(760px,calc(100vh - 132px));min-height:500px;display:grid;grid-template-columns:minmax(280px,360px) minmax(0,1fr);gap:14px}.thread-list,.admin-chat{min-width:0;min-height:0;border:1px solid var(--line);border-radius:22px;background:#10141c;overflow:hidden}.thread-list{position:static;height:auto;display:grid;grid-template-rows:auto auto auto minmax(0,1fr);padding:18px}.support-list-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.support-list-head h2{display:flex;align-items:center;gap:8px;margin-top:5px}.support-list-head h2 small{display:grid;min-width:22px;height:22px;place-items:center;border-radius:8px;background:rgba(145,214,255,.1);color:#9bd9ff;font-size:11px}.support-icon-button{width:42px;height:42px;border:1px solid rgba(145,214,255,.16);border-radius:13px;background:#151c26;color:#bfe8ff;font-size:20px;cursor:pointer}.support-search{display:block;margin-top:15px}.support-search input{box-sizing:border-box;width:100%;height:44px;border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:0 14px;background:#0b1017;color:#eef7ff;font:inherit;font-size:13px}.support-search input::placeholder{color:#667383}.support-list-status{min-height:28px;display:flex;align-items:center;gap:8px;color:#8799aa;font-size:11px}.support-spinner{display:inline-block;width:15px;height:15px;border:2px solid rgba(145,214,255,.2);border-top-color:#9bd9ff;border-radius:50%;animation:spin .75s linear infinite}.thread-items{min-height:0;margin:0 -6px;padding-right:3px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#253442 transparent}.thread-items>button{box-sizing:border-box;width:100%;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:11px;min-height:68px;padding:10px;border:1px solid transparent;border-radius:16px;background:transparent;color:#eaf4fc;text-align:left;cursor:pointer;transition:background .16s,border-color .16s,transform .16s}.thread-items>button:hover{background:#141b25;border-color:rgba(145,214,255,.08);transform:translateY(-1px)}.thread-items>button.active{border-color:rgba(145,214,255,.16);background:linear-gradient(90deg,rgba(145,214,255,.13),rgba(145,214,255,.035))}.thread-items>button>i{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:#172b3c;color:#aeddff;font-style:normal;font-weight:900}.thread-items span{min-width:0;display:flex;flex-direction:column;gap:5px}.thread-items b,.thread-items small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.thread-items small{color:#7f91a2;font-size:11px}.thread-items em{display:grid;place-items:center;min-width:22px;height:22px;padding:0 4px;border-radius:8px;background:#9bd9ff;color:#07111d;font-size:10px;font-style:normal;font-weight:900}.admin-chat{display:grid;grid-template-rows:auto minmax(0,1fr) auto}.conversation-head{min-height:70px;align-items:center;margin:0!important;padding:0 22px;border-bottom:1px solid rgba(255,255,255,.06)}.conversation-head>div{display:flex;min-width:0;flex:1;flex-direction:column;gap:4px}.conversation-head b,.conversation-head small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.conversation-head small{color:#77899a;font-size:11px}.conversation-badge{padding:6px 9px;border-radius:9px;background:rgba(97,216,165,.08);color:#78e1b4;font-size:9px;font-weight:800;text-transform:uppercase}.support-back{display:none;border:0;background:transparent;color:#9bd9ff;font:inherit;font-weight:800;cursor:pointer}.chat-messages{min-width:0;min-height:0;padding:22px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#253442 transparent}.chat-messages article{box-sizing:border-box;width:fit-content;max-width:min(72%,680px);display:flex;flex-direction:column;gap:6px;margin:0 auto 12px 0;padding:12px 15px;border:1px solid rgba(255,255,255,.045);border-radius:17px 17px 17px 5px;background:#151d28;color:#eaf2f9;overflow-wrap:anywhere;line-height:1.5}.chat-messages article.admin{margin-left:auto;margin-right:0;border-color:rgba(145,214,255,.12);border-radius:17px 17px 5px 17px;background:#18354a}.chat-messages small{color:#879aaa;font-size:10px}.reply-box{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;gap:8px 12px!important;padding:14px 16px!important;border-top:1px solid rgba(255,255,255,.06)!important}.reply-box>label{grid-column:1/-1;color:#aabac8;font-size:11px;font-weight:800}.reply-box textarea{box-sizing:border-box;grid-column:1/-1;width:100%;min-height:72px;max-height:150px;resize:vertical;border:1px solid rgba(255,255,255,.075)!important;border-radius:14px!important;padding:12px 14px!important;background:#0b1118!important;color:#fff;font:inherit;line-height:1.45;outline:0}.reply-meta{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;gap:12px}.reply-meta small{color:#697c8d;font-size:10px}.reply-meta button{min-width:116px;min-height:42px;border:0;border-radius:12px!important;padding:0 18px!important;background:#9bd9ff;color:#07111d;font-weight:900;cursor:pointer}.reply-status{grid-column:1/-1;min-height:15px;margin:0;color:#78e1b4;font-size:11px}.reply-status.error-text{color:#ffaaaa}.support-state{display:grid;place-content:center;justify-items:center;min-height:170px;padding:24px;text-align:center;color:#8092a3}.support-state b{color:#eaf4fc}.support-state p{max-width:340px;margin:7px 0 13px;font-size:12px;line-height:1.5}.support-state button{min-height:38px;border:1px solid rgba(145,214,255,.16);border-radius:11px;padding:0 14px;background:#172433;color:#bfe8ff;font-weight:800;cursor:pointer}.support-state.error{color:#d59a9a}.support-state.error b{color:#ffb5b5}.support-state .quiet{margin-top:7px;border-color:transparent;background:transparent;color:#8ba1b4}.conversation-state{grid-row:1/-1;min-height:100%}.conversation-empty{min-height:100%}.mobile-list-action{display:none}.support-workspace button:focus-visible,.support-workspace input:focus-visible,.support-workspace textarea:focus-visible,nav button:focus-visible{outline:3px solid #9bd9ff;outline-offset:2px}.support-workspace button:disabled{cursor:not-allowed;opacity:.42;filter:saturate(.45)}
  @media(max-width:900px){.support-workspace{height:calc(100vh - 126px);min-height:460px;grid-template-columns:1fr}.support-workspace>.thread-list,.support-workspace>.admin-chat{grid-area:1/1}.support-workspace>.admin-chat{display:none}.support-workspace.detail-open>.thread-list{display:none}.support-workspace.detail-open>.admin-chat{display:grid}.support-back{display:flex;align-items:center;gap:7px}.conversation-head{padding:0 16px}.conversation-badge{display:none}.mobile-list-action{display:block}}
  @media(max-width:560px){.support-workspace{height:calc(100dvh - 180px);min-height:420px;gap:0}.thread-list,.admin-chat{border-radius:18px}.thread-list{padding:14px}.support-list-head h2{font-size:19px}.chat-messages{padding:15px}.chat-messages article{max-width:88%}.reply-box{padding:12px!important}.reply-meta{align-items:flex-end}.reply-meta small{max-width:50%}.reply-meta button{min-width:108px}.conversation-head{min-height:62px;gap:12px}.support-back span{display:none}}
  /* Arc Operations 2.0 — dense, calm and operational rather than decorative. */
  :global(body.admin-console-open){background:#07090d}
  .console{grid-template-columns:286px minmax(0,1fr);background:radial-gradient(900px 600px at 78% -15%,rgba(81,155,205,.12),transparent 58%),#07090d}
  aside{padding:22px 16px;border-right:1px solid rgba(255,255,255,.055);background:#0b0d12}
  .brand{min-height:66px;padding:0 14px;border-radius:20px;background:rgba(255,255,255,.025)}
  .brand img{width:34px}.brand span{font-size:16px}.brand small{margin-top:4px;color:#68717e;font-size:9px;letter-spacing:.12em;text-transform:uppercase}
  nav{gap:3px;margin-top:24px;overflow-y:auto;scrollbar-width:none}nav::-webkit-scrollbar{display:none}
  nav button{min-height:47px;padding:0 14px;border-radius:14px;color:#8e98a6;font-size:12px;font-weight:700;letter-spacing:-.01em;transition:background .18s,color .18s,transform .18s}
  nav button:hover{background:rgba(255,255,255,.04);color:#eaf5fd;transform:translateX(2px)}
  nav button.active{background:linear-gradient(90deg,rgba(145,214,255,.15),rgba(145,214,255,.045));color:#bfe8ff;box-shadow:inset 3px 0 #91d6ff}
  nav button.active:after{display:none}.owner{border:1px solid rgba(255,255,255,.05);background:#10131a}
  main{width:min(1460px,calc(100% - 72px));padding:34px 0 80px}
  main>header{align-items:center;margin-bottom:26px;padding-bottom:22px;border-bottom:1px solid rgba(255,255,255,.055)}
  h1{font-size:clamp(34px,3.3vw,52px);letter-spacing:-.05em}.eyebrow{color:#80bfe7}
  .panel,.metrics article,.thread-list,.admin-chat{border-color:rgba(255,255,255,.065);background:#10141c;box-shadow:0 18px 50px rgba(0,0,0,.16)}
  .panel{border-radius:22px}.metrics article{border-radius:18px}
  .health{border-radius:18px;background:linear-gradient(90deg,rgba(62,149,118,.12),rgba(16,20,28,.98));border-color:rgba(109,213,170,.11)}
  .metrics{grid-template-columns:repeat(4,minmax(0,1fr))}.metrics article:first-child{background:linear-gradient(145deg,rgba(50,113,151,.22),#10141c 72%)}
  .refresh{border-radius:13px;background:#111720}.refresh:disabled{cursor:not-allowed;opacity:.48}.telemetry-fresh.stale{max-width:420px;color:#ffc57d}.telemetry-fresh.stale i{background:#ffc57d}
  @media(max-width:1100px){.console{grid-template-columns:82px minmax(0,1fr)}aside{padding-inline:10px}.brand span,nav span,.owner span{display:none}.brand,nav button,.owner{justify-content:center;padding-inline:0}.metrics{grid-template-columns:1fr 1fr}}
  /* Compact ArcVPN shell: original cold palette, Axottle-like information density. */
  .console{grid-template-columns:272px minmax(0,1fr)}
  .brand{background:transparent;border-bottom:1px solid rgba(255,255,255,.055);border-radius:0}.brand img{width:38px}.brand span{font-size:20px}
  main{width:min(1560px,calc(100% - 64px));padding-top:26px}main>header{margin-bottom:22px;padding-bottom:18px}h1{font-size:32px;letter-spacing:-.035em}.live-tools{gap:10px}
  :global(body.admin-console-open #app){max-width:none}
  @media(max-width:1100px){.console{grid-template-columns:82px minmax(0,1fr)}main{width:calc(100% - 32px)}}
  @media(max-width:560px){
    .console{display:block;height:100dvh}
    .console>aside{box-sizing:border-box;top:auto;bottom:calc(10px + env(safe-area-inset-bottom,0px));left:50%;right:auto;width:calc(100% - 24px);max-width:480px;height:64px;padding:7px 8px;border-radius:22px;transform:translateX(-50%);box-shadow:0 18px 46px rgba(0,0,0,.48);overflow:hidden}
    .console>aside>nav{box-sizing:border-box;display:flex;width:100%;height:48px;margin-top:0;padding:0;gap:4px;overflow-x:auto;overflow-y:hidden;scroll-padding-inline:0;scroll-snap-type:x proximity;scrollbar-width:none}
    .console>aside>nav::-webkit-scrollbar{display:none}
    .console>aside>nav button{box-sizing:border-box;flex:0 0 48px;width:48px;height:48px;min-height:48px;padding:0;border-radius:16px;scroll-snap-align:start;transform:none}
    .console>aside>nav button.active{box-shadow:inset 3px 0 #91d6ff}
    .console>main{height:100dvh;padding-bottom:calc(104px + env(safe-area-inset-bottom,0px));scroll-padding-bottom:calc(104px + env(safe-area-inset-bottom,0px))}
  }
  @media(max-width:480px){.metrics,.source-grid,.traffic-grid{grid-template-columns:1fr}.periods{box-sizing:border-box;width:100%}.periods button{flex:1;padding-inline:8px}}
</style>
