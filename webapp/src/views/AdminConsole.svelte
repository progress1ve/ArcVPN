<script>
  import { onDestroy, onMount } from 'svelte'
  import ArcIcon from '../components/ArcIcon.svelte'
  import AdminHealth from './admin/AdminHealth.svelte'
  import AdminSchemes from './admin/AdminSchemes.svelte'
  import AdminNodes from './admin/AdminNodes.svelte'
  import AdminSecurity from './admin/AdminSecurity.svelte'
  import AdminBackups from './admin/AdminBackups.svelte'
  import AdminSettings from './admin/AdminSettings.svelte'
  import AdminCatalog from './admin/AdminCatalog.svelte'
  import AdminFinance from './admin/AdminFinance.svelte'
  import AdminUsers from './admin/AdminUsers.svelte'
  import { fetchAdminOverview, loginAdmin, logoutAdmin, runAdminNodeDiagnostic, fetchAdminSupportThreads, fetchAdminSupportThread, sendAdminSupportReply } from '../lib/api.js'

  let data = null
  let loading = true
  let error = ''
  let active = 'overview'
  let password = ''
  let signingIn = false
  let userFilter = 'new'
  let paymentFilter = 'paid'
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
  const nav = [
    ['overview', 'home', 'Главная'], ['health', 'pulse', 'Здоровье'],
    ['schemes', 'signal', 'Схемы подключений'], ['nodes', 'devices', 'Ноды'],
    ['catalog', 'route', 'Каталог подписки'], ['users', 'users', 'Пользователи'], ['payments', 'wallet', 'Финансы'],
    ['support', 'headset', 'Поддержка'], ['security', 'shield', 'Безопасность'],
    ['backups', 'file', 'Резервные копии'], ['settings', 'settings', 'Настройки'],
  ]
  const rub = (v) => `${new Intl.NumberFormat('ru-RU').format(Number(v || 0))} ₽`
  const num = (v) => new Intl.NumberFormat('ru-RU').format(Number(v || 0))
  const mbps = (v) => `${(Number(v || 0) / 1_000_000).toFixed(Number(v || 0) >= 10_000_000 ? 0 : 2)} Мбит/с`
  const supportName = (thread) => thread?.first_name || (thread?.username ? `@${thread.username}` : `ID ${thread?.telegram_id || thread?.id || '—'}`)
  $: visibleUsers = (data?.recent_users || []).filter((u) => userFilter === 'all' || (userFilter === 'online' ? Number(u.online_devices) > 0 : userFilter === 'inactive' ? !u.active : userFilter === 'referral' ? Number(u.invited_count) > 0 : true)).sort((a,b) => userFilter === 'top' ? Number(b.paid_rub)-Number(a.paid_rub) : userFilter === 'referral' ? Number(b.invited_count)-Number(a.invited_count) : new Date(b.created_at)-new Date(a.created_at))
  $: visiblePayments = (data?.recent_payments || []).filter((p) => paymentFilter === 'all' || (paymentFilter === 'paid' ? ['paid','succeeded'].includes(p.status) : !['paid','succeeded'].includes(p.status)))
  $: filteredSupportThreads = supportThreads.filter((thread) => `${supportName(thread)} ${thread.last_message || ''}`.toLocaleLowerCase('ru-RU').includes(supportQuery.trim().toLocaleLowerCase('ru-RU')))

  async function load(silent = false) {
    if (!silent) loading = true
    error = ''
    try { data = await fetchAdminOverview() }
    catch (e) { error = e.code === 403 ? 'auth' : 'Данные временно недоступны' }
    finally { loading = false; if (data) lastUpdated = new Date() }
  }
  async function signIn() {
    if (!password || signingIn) return
    signingIn = true; error = ''
    try { await loginAdmin(password); password = ''; await load() }
    catch (e) { error = e.code === 429 ? 'Слишком много попыток. Подождите 15 минут.' : 'Неверный пароль' }
    finally { signingIn = false }
  }
  async function signOut() { await logoutAdmin(); data = null; error = 'auth' }
  async function runDiagnostic(node) {
    if (diagnosticNode) return
    diagnosticNode = node.uuid
    try { diagnostics = { ...diagnostics, [node.uuid]: (await runAdminNodeDiagnostic(node.uuid)).diagnostic } }
    catch (e) { diagnostics = { ...diagnostics, [node.uuid]: { ok: false, error: e.reason || 'Ошибка диагностики' } } }
    finally { diagnosticNode = '' }
  }
  async function openSupport() {
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
    if (!threadId || !body || sendingReply) return
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
    load()
    refreshTimer = setInterval(() => load(true), 30000)
  })
  onDestroy(() => {
    document.body.classList.remove('admin-console-open')
    if (refreshTimer) clearInterval(refreshTimer)
  })
</script>

<svelte:head><title>ArcVPN Admin</title></svelte:head>

<div class="console">
  <aside>
    <a class="brand" href="/admin"><img src="/app/assets/arc-flow/arc-logo.svg" alt="" /><span>ArcVPN</span></a>
    <nav aria-label="Разделы админ-панели">{#each nav as item}<button class:active={active === item[0]} aria-current={active === item[0] ? 'page' : undefined} aria-label={item[2]} on:click={() => item[0] === 'support' ? openSupport() : active = item[0]} title={item[2]}><ArcIcon name={item[1]} size={20} weight="duotone" /><span>{item[2]}</span></button>{/each}</nav>
    <div class="owner"><i>К</i><span>Владелец<small>Полный доступ</small></span></div>
  </aside>

  <main class={`section-${active}`}>
    <header><div><h1>{active === 'overview' ? 'Главная' : nav.find(item => item[0] === active)?.[2] || 'ArcVPN'}</h1></div><div class="live-tools"><span class="telemetry-fresh"><i></i>{lastUpdated ? `Обновлено ${lastUpdated.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'})}` : 'Подключаем данные'}</span><button class="refresh" aria-label={active === 'support' ? 'Обновить обращения' : 'Проверить данные'} on:click={() => active === 'support' ? openSupport() : load(true)}><ArcIcon name="pulse" size={18} />{active === 'support' ? 'Обновить' : 'Проверить'}</button></div></header>
    {#if loading}
      <section class="state"><i class="loader"></i><p>Собираем показатели ArcVPN…</p></section>
    {:else if error}
      <section class="state login-card">
        <img src="/app/assets/arc-flow/arc-logo.svg" alt="" />
        <h2>Вход в ArcVPN Admin</h2>
        <p>{error === 'auth' ? 'Введите пароль владельца или откройте панель из Telegram.' : error}</p>
        <form on:submit|preventDefault={signIn}>
          <input bind:value={password} type="password" autocomplete="current-password" placeholder="Пароль" aria-label="Пароль" />
          <button disabled={signingIn || !password}>{signingIn ? 'Проверяем…' : 'Войти'}</button>
        </form>
      </section>
    {:else if active === 'users'}
      <AdminUsers users={data?.recent_users || []} onRefresh={() => load(true)} />
    {:else if active === 'payments'}
      <AdminFinance {data} />
    {:else if active === 'catalog'}
      <AdminCatalog />
    {:else if active === 'health'}
      <AdminHealth {data} onRefresh={() => load(true)} />
    {:else if active === 'schemes'}
      <AdminSchemes {data} />
    {:else if active === 'nodes'}
      <AdminNodes {data} {diagnostics} {diagnosticNode} onDiagnostic={runDiagnostic} />
    {:else if active === 'security'}
      <AdminSecurity {data} />
    {:else if active === 'backups'}
      <AdminBackups />
    {:else if active === 'settings'}
      <AdminSettings {data} />
    {:else if active === 'network'}
      <section class="workspace-section">
        <div class="section-title"><div><span class="eyebrow">{active === 'schemes' ? 'Маршрутизация' : active === 'nodes' ? 'Инфраструктура' : 'Операционный центр'}</span><h2>{active === 'schemes' ? 'Схемы подключений' : active === 'nodes' ? 'Ноды ArcVPN' : 'Здоровье системы'}</h2><p>{active === 'schemes' ? 'Автовыбор, резервные маршруты и LTE fallback.' : active === 'nodes' ? 'Состояние, нагрузка и диагностика каждого сетевого узла.' : 'Remnawave, Subscription API, база и внешние сетевые пробы.'}</p></div><button class="refresh" on:click={load}><ArcIcon name="pulse" size={18}/>Проверить</button></div>
        <div class="service-strip">
          <article class:ok={data.remnawave?.healthy}><i></i><span><b>Remnawave</b><small>{data.remnawave?.healthy ? `${data.remnawave.users} пользователей` : `Ошибка: ${data.remnawave?.detail}`}</small></span></article>
          <article class:ok={data.operations.subscription_service}><i></i><span><b>Subscription API</b><small>{data.operations.subscription_service ? 'Отвечает' : 'Недоступен'}</small></span></article>
          <article class:ok={data.system.database_integrity==='ok'}><i></i><span><b>База ArcVPN</b><small>{data.system.database_integrity==='ok' ? 'Проверка целостности пройдена' : `Состояние: ${data.system.database_integrity}`}</small></span></article>
          <article class:ok={Number(data.system.disk_used_pct)<85}><i></i><span><b>Диск</b><small>{data.system.disk_used_gb} из {data.system.disk_total_gb} ГБ · {data.system.disk_used_pct}%</small></span></article>
        </div>
        <div class="network-grid">{#each data.remnawave?.nodes || [] as node}<article class:offline={!node.connected}><div class="node-name"><i class:offline={!node.connected}></i><div><b>{node.name}</b><span>{node.address} · {node.inbounds?.length || 0} inbound</span></div><em class:bad={!node.connected}>{node.connected ? 'ONLINE' : 'OFFLINE'}</em></div><p>{node.inbounds?.map(i=>`${String(i.network||i.type||'').toUpperCase()}:${i.port}`).join(' · ') || 'Нет активных inbound'}</p><strong>{num(node.users_online)}</strong><small>пользователей онлайн · передано {node.traffic_used_gb} ГБ</small><div class="node-day"><span>RAM {node.memory_used_pct}%</span><span>load {node.load_1m ?? '—'}</span><span>↓ {mbps(node.rx_bps)}</span><span>↑ {mbps(node.tx_bps)}</span><span>uptime {Math.floor(Number(node.xray_uptime_seconds||0)/3600)} ч</span></div>{#if node.diagnostic}<p class:good={node.diagnostic.ok} class="diagnostic-result">Автотест: {node.diagnostic.ok ? 'норма' : 'ошибка'} · {node.diagnostic.created_at}</p>{/if}<button class="deep-test" disabled={Boolean(diagnosticNode)} on:click={() => runDiagnostic(node)}>{diagnosticNode===node.uuid?'Проверяем…':'Глубокий тест портов'}</button>{#if diagnostics[node.uuid]}<p class:good={diagnostics[node.uuid].ok} class="diagnostic-result">{diagnostics[node.uuid].ok ? `Доступно ${diagnostics[node.uuid].ports?.filter(p=>p.ok).length || 0} портов · ${diagnostics[node.uuid].duration_ms} мс` : `Проблема: ${diagnostics[node.uuid].error || diagnostics[node.uuid].ports?.filter(p=>!p.ok).map(p=>p.port).join(', ')}`}</p>{/if}<div class="bar"><i style={`width:${Math.min(100,Number(node.memory_used_pct||0))}%`}></i></div></article>{/each}</div>
        <section class="scheme-board">
          <header><div><span class="eyebrow">Схемы подключения</span><h3>Автовыбор и резервные маршруты</h3></div><strong>клиентская балансировка</strong></header>
          <div class="scheme-grid">{#each data.remnawave?.connection_schemes || [] as scheme}<article class:auto={scheme.id==='auto'}><div class="scheme-title"><i></i><div><b>{scheme.name}</b><small>{scheme.kind === 'client_balancer' ? `2 пробы каждые ${scheme.probe_interval_seconds} сек · LTE только fallback` : `${scheme.public_host} → ${scheme.origin}`}</small></div><em>{scheme.standby ? 'STANDBY' : scheme.active_only_as_fallback ? 'FALLBACK' : 'ACTIVE'}</em></div>{#if scheme.id==='auto'}<div class="route-flow">{#each Object.entries(scheme.online_distribution || {}) as [nodeName,count]}<span><b>{count}</b>{nodeName}</span>{/each}{#if !Object.keys(scheme.online_distribution || {}).length}<small>Сейчас нет активных сессий</small>{/if}</div><p>Точный выбор профиля Happ не передаёт серверу. Ниже показано, на каких RemnaNode фактически находятся онлайн-пользователи.</p>{:else}<div class="route-meta"><span>Трафик ×{scheme.traffic_factor}</span><span>{scheme.active_only_as_fallback ? 'Включается только при недоступности main' : 'Резервный CDN-маршрут'}</span></div>{/if}</article>{/each}</div>
        </section>
        <section class="inbound-board remna-board"><header><div><span class="eyebrow">Новая платформа</span><h3>RemnaNode-контур</h3></div><strong>{data.remnawave?.nodes?.filter(node=>node.connected).length || 0}/{data.remnawave?.nodes?.length || 0} онлайн</strong></header><div>{#each data.remnawave?.nodes || [] as node}<article><i class:off={!node.connected}></i><span><b>{node.country_code ? `${node.country_code} · ` : ''}{node.name}</b><small>{node.address} · {node.inbounds?.length || 0} inbound · {node.traffic_used_gb} ГБ</small></span><em>{node.users_online} онлайн · RAM {node.memory_used_pct}%</em></article>{/each}</div></section>
      </section>
        <section class="inbound-board"><header><div><span class="eyebrow">Качество провайдеров</span><h3>Независимые сетевые пробы</h3></div><strong>каждые 10 минут</strong></header><div>{#each data.servers || [] as server}<article><i class:off={!server.agent_online}></i><span><b>{server.name}</b><small>loss {server.packet_loss_pct ?? '—'}% · jitter {server.jitter_ms ?? '—'} мс · DNS {server.dns_ms ?? '—'} мс · HTTPS {server.https_ms ?? '—'} мс</small></span><em>↓ {server.download_mbps ?? '—'} Мбит/с</em></article>{/each}</div></section>
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
              <textarea id="support-reply" bind:value={replyBody} placeholder="Введите сообщение…" maxlength="4000" aria-describedby="reply-help reply-status"></textarea>
              <div class="reply-meta"><small id="reply-help">{replyBody.length}/4000 · Enter переносит строку</small><button disabled={sendingReply || !replyBody.trim()}>{sendingReply ? 'Отправляем…' : 'Отправить'}</button></div>
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
      <button class="logout" on:click={signOut}>Выйти</button>
      <section class:alert={!data.remnawave?.healthy || data.remnawave?.nodes?.some(node=>!node.connected && !node.disabled)} class="health"><i></i><div><b>{data.remnawave?.healthy ? 'Сеть ArcVPN работает штатно' : 'Требуется внимание к сети'}</b><span>{data.remnawave?.nodes?.filter(node=>node.connected).length || 0} из {data.remnawave?.nodes?.length || 0} RemnaNode подключены · проверено только что</span></div><strong>{data.remnawave?.healthy ? 'Remnawave online' : data.remnawave?.detail}</strong></section>
      <section class="metrics">
        <article><span>Выручка за 30 дней</span><strong>{rub(data.financials?.month_rub)}</strong><small>{num(data.financials?.successful_orders)} успешных оплат за всё время</small></article>
        <article><span>Активные подписки</span><strong>{num(data.subscriptions.active)}</strong><small>+{num(data.subscriptions.month)} за 30 дней</small></article>
        <article><span>Trial → оплата</span><strong>{Number(data.conversion.conversion_rate).toFixed(1)}%</strong><small>{num(data.conversion.converted)} конверсий</small></article>
        <article><span>Сейчас онлайн</span><strong>{num(data.remnawave?.online_users?.length || 0)}</strong><small>уникальные пользователи Remnawave за 3 минуты</small></article>
      </section>
      <section class="panel referral-ops">
        <div class="panel-head"><div><span>Органический рост</span><h2>Реферальная программа</h2></div><strong>{data.referrals?.conversion_rate || 0}% в оплату</strong></div>
        <div class="referral-metrics"><article><b>{num(data.referrals?.day_invited)}</b><span>пришли сегодня</span></article><article><b>{num(data.referrals?.month_invited)}</b><span>за 30 дней</span></article><article><b>{num(data.referrals?.total_invited)}</b><span>всего приглашено</span></article><article><b>{num(data.referrals?.converted)}</b><span>оплатили тариф</span></article></div>
        <div class="referral-leaders">{#each (data.referrals?.leaders || []).slice(0,5) as leader}<article><i>{(leader.first_name || leader.username || '?')[0]}</i><span><b>{leader.first_name || `@${leader.username}` || leader.telegram_id}</b><small>{leader.invited_count} приглашено · {leader.converted_count} оплатили · +{leader.earned_days} дней</small></span></article>{/each}</div>
      </section>
      <div class="grid">
        <section class="panel">
          <div class="panel-head"><div><span>Инфраструктура</span><h2>Узлы сети</h2></div><button on:click={() => active = 'nodes'}>Все узлы <ArcIcon name="arrow" size={16} /></button></div>
          <div class="nodes">{#each data.servers as server}<article><div class="node-name"><i class:offline={!server.is_active}></i><div><b>{server.name}</b><span>{server.is_active ? `Доступен${server.latency_ms ? ` · ${server.latency_ms} мс` : ''}` : server.telemetry_available===false ? 'Нет телеметрии' : 'Отключён'}</span></div></div><strong>{server.telemetry_available===false ? '—' : num(server.active_clients)}</strong><small>{server.telemetry_available===false ? 'данные недоступны' : 'онлайн сейчас'}</small>{#if server.telemetry_available!==false}<div class="bar"><i style={`width:${Math.min(100,(Number(server.active_clients||0)/Math.max(1,Number(server.clients_count||0)))*100)}%`}></i></div>{/if}</article>{/each}</div>
        </section>
        <section class="panel queue">
          <div class="panel-head"><div><span>Рабочая очередь</span><h2>Требует внимания</h2></div></div>
          <button on:click={() => { paymentFilter='failed'; active='payments' }}><i><ArcIcon name="wallet" size={18} /></i><span><b>Незавершённые платежи</b><small>Открыть список операций</small></span><strong>{data.operations.pending_payments}</strong></button>
          <button on:click={() => active='settings'}><i class="green"><ArcIcon name="pulse" size={18} /></i><span><b>Автопродления</b><small>{data.recurring.provider_ready ? 'Активные способы оплаты' : 'YooKassa ещё не согласовала опцию'}</small></span><strong>{data.recurring.active}</strong></button>
          <button on:click={openSupport}><i class="violet"><ArcIcon name="headset" size={18} /></i><span><b>Открытые обращения</b><small>Пользователи ждут ответа</small></span><strong>{data.operations.open_support_threads}</strong></button>
          <button on:click={() => { userFilter='new'; active='users' }}><i class="green"><ArcIcon name="users" size={18} /></i><span><b>Новые пользователи</b><small>За последние 24 часа</small></span><strong>{data.users.day}</strong></button>
        </section>
      </div>
      <section class="panel device-control">
        <div class="panel-head"><div><span>Контроль доступа</span><h2>Устройства и лимиты</h2></div><strong>{data.device_security?.users_over_limit ? 'Есть нарушения' : 'Штатно'}</strong></div>
        <div>
          <article><b>{num(data.device_security?.active_devices)}</b><span>активных устройств</span></article>
          <article><b>{num(data.device_security?.revoked_devices)}</b><span>освобождено и заблокировано</span></article>
          <article><b>{num(data.device_security?.protected_users)}</b><span>аккаунтов с жёсткой привязкой</span></article>
          <article class:warn={data.device_security?.users_over_limit}><b>{num(data.device_security?.users_over_limit)}</b><span>аккаунтов сверх лимита</span></article>
          <article class:warn={data.device_security?.awaiting_reimport}><b>{num(data.device_security?.awaiting_reimport)}</b><span>ожидают повторного импорта</span></article>
        </div>
      </section>
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
  .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.metrics article,.panel{border:1px solid var(--line);background:linear-gradient(145deg,rgba(14,26,41,.96),rgba(8,15,25,.96))}.metrics article{min-height:120px;padding:22px;border-radius:24px;display:flex;flex-direction:column}.metrics span,.metrics small{color:#7890a5;font-size:12px}.metrics strong{margin:auto 0 5px;font-size:30px;letter-spacing:-.045em}.metrics small{color:#9bd9ff}
  .grid{display:grid;grid-template-columns:1.35fr 1fr;gap:16px}.panel{padding:24px;border-radius:28px}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}h2{margin:6px 0 0;font-size:21px}.panel-head button{display:flex;align-items:center;gap:6px;border:0;background:transparent;color:#8fcdf5;cursor:pointer}.nodes{display:grid;grid-template-columns:1fr 1fr;gap:12px}.nodes article{padding:18px;border-radius:20px;background:rgba(4,10,18,.56)}.node-name{display:flex;align-items:center;gap:9px}.node-name>i{width:8px;height:8px;border-radius:50%;background:#60d7a4}.node-name>i.offline{background:#ff7474}.node-name div{display:flex;flex-direction:column}.node-name span,.nodes small{color:#6f8497;font-size:11px}.nodes article>strong{display:block;margin-top:24px;font-size:27px}.bar{height:4px;margin-top:14px;border-radius:2px;background:#162534;overflow:hidden}.bar i{display:block;height:100%;background:#91d6ff}
  .queue>button{width:100%;display:flex;align-items:center;gap:12px;padding:13px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:#dbe8f3;text-align:left}.queue>button:last-child{border-bottom:0}.queue button>i{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;color:#9bd9ff;background:#102942}.queue button>i.violet{color:#c2afff;background:#211b3b}.queue button>i.green{color:#79deb2;background:#102d27}.queue button span{display:flex;flex:1;flex-direction:column;gap:3px}.queue button small{color:#70879b}.queue button>strong{display:grid;place-items:center;min-width:32px;height:32px;border-radius:50%;background:#122131}
  .device-control{margin-top:16px}.device-control>.panel-head>strong{padding:8px 12px;border-radius:14px;background:rgba(97,216,165,.09);color:#78e1b4;font-size:11px}.device-control>div:last-child{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.device-control article{display:flex;min-height:82px;flex-direction:column;justify-content:center;padding:16px;border-radius:20px;background:rgba(3,9,16,.48)}.device-control article b{font-size:25px}.device-control article span{margin-top:5px;color:#7890a5;font-size:11px;line-height:1.35}.device-control article.warn b{color:#ff9c9c}
  .referral-ops{margin-top:16px}.referral-ops>.panel-head>strong{padding:8px 12px;border-radius:14px;background:rgba(155,217,255,.09);color:#9bd9ff;font-size:11px}.referral-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.referral-metrics article{display:flex;min-height:78px;flex-direction:column;justify-content:center;padding:16px;border-radius:20px;background:rgba(3,9,16,.5)}.referral-metrics b{font-size:26px}.referral-metrics span,.referral-leaders small{margin-top:4px;color:#7890a5;font-size:11px}.referral-leaders{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:10px}.referral-leaders article{display:flex;align-items:center;gap:10px;padding:12px;border-radius:18px;background:#0b1724}.referral-leaders i{display:grid;flex:0 0 34px;height:34px;place-items:center;border-radius:50%;background:#17314a;color:#9bd9ff;font-style:normal;font-weight:800}.referral-leaders span{display:flex;min-width:0;flex-direction:column}.referral-leaders b,.referral-leaders small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .scheme-board{margin:18px 0;padding:24px;border:1px solid var(--line);border-radius:28px;background:linear-gradient(145deg,rgba(14,26,41,.96),rgba(8,15,25,.96))}.scheme-board>header{align-items:center;margin-bottom:18px}.scheme-board h3{margin:5px 0 0;font-size:21px}.scheme-board>header>strong{padding:8px 12px;border-radius:14px;background:rgba(155,217,255,.08);color:#9bd9ff;font-size:11px}.scheme-grid{display:grid;grid-template-columns:1.35fr 1fr 1fr;gap:12px}.scheme-grid>article{min-width:0;padding:18px;border-radius:20px;background:rgba(3,9,16,.52)}.scheme-grid>article.auto{background:linear-gradient(135deg,rgba(31,79,113,.28),rgba(3,9,16,.6))}.scheme-title{display:flex;align-items:center;gap:10px}.scheme-title>i{width:9px;height:9px;border-radius:50%;background:#61d8a5;box-shadow:0 0 0 6px rgba(97,216,165,.07)}.scheme-title>div{display:flex;min-width:0;flex:1;flex-direction:column;gap:3px}.scheme-title small,.scheme-grid p,.route-flow small{color:#7890a5;font-size:11px}.scheme-title em{padding:6px 9px;border-radius:12px;background:rgba(155,217,255,.07);color:#9bd9ff;font-size:9px;font-style:normal;font-weight:800}.route-flow{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.route-flow span{display:flex;align-items:center;gap:6px;padding:7px 9px;border-radius:13px;background:#101f2d;color:#9eb3c5;font-size:10px}.route-flow b{color:#9bd9ff;font-size:14px}.scheme-grid p{margin:14px 0 0;line-height:1.45}.route-meta{display:grid;gap:8px;margin-top:16px}.route-meta span{padding:8px 10px;border-radius:13px;background:#0d1b28;color:#91a9bc;font-size:10px}
  .state{min-height:55vh;display:grid;place-content:center;justify-items:center;text-align:center;color:#8196a9}.state h2{color:#fff}.loader{width:34px;height:34px;border:3px solid #183047;border-top-color:#9bd9ff;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
  .login-card{min-height:0;width:min(440px,calc(100% - 48px));margin:12vh auto 0;padding:40px 32px;border:1px solid var(--line);border-radius:30px;background:linear-gradient(145deg,rgba(14,26,41,.98),rgba(8,15,25,.98));box-shadow:0 32px 90px rgba(0,0,0,.35)}.login-card>img{width:48px}.login-card p{max-width:340px;line-height:1.5}.login-card form{width:100%;display:grid;gap:12px;margin-top:14px}.login-card input,.login-card button{box-sizing:border-box;width:100%;min-height:52px;border-radius:18px;font:inherit}.login-card input{border:1px solid var(--line);padding:0 17px;background:#07101b;color:#fff;outline:none}.login-card input:focus{border-color:rgba(155,217,255,.55);box-shadow:0 0 0 4px rgba(155,217,255,.07)}.login-card button{border:0;background:#9bd9ff;color:#07111d;font-weight:800;cursor:pointer}.login-card button:disabled{opacity:.55}.logout{float:right;margin:-54px 118px 0 0;border:0;background:transparent;color:#7890a5;cursor:pointer}
  @media(max-width:900px){.console{grid-template-columns:76px 1fr}aside{padding:20px 10px}.brand span,nav span,.owner span{display:none}.brand{justify-content:center;padding-inline:0}nav button{justify-content:center;padding:0}.owner{justify-content:center;background:transparent}.metrics,.referral-metrics{grid-template-columns:1fr 1fr}.referral-leaders{grid-template-columns:1fr 1fr}.grid,.scheme-grid{grid-template-columns:1fr}main{width:calc(100% - 32px);padding-top:28px}}
  @media(max-width:560px){.console{display:block}aside{position:fixed;z-index:10;top:auto;bottom:12px;left:12px;right:12px;height:64px;flex-direction:row;padding:8px;border:1px solid var(--line);border-radius:24px}.brand,.owner{display:none}nav{display:flex;width:100%;justify-content:space-around}nav button{width:48px;min-height:48px;border-radius:18px}nav button:nth-child(n+5){display:none}main{padding:26px 0 100px}header{align-items:flex-start}.refresh{width:44px;padding:0;justify-content:center;font-size:0}.health>strong{display:none}.metrics{gap:10px}.metrics article{min-height:105px;padding:17px}.metrics strong{font-size:24px}.nodes{grid-template-columns:1fr}.panel{padding:19px;border-radius:24px}}
  main{box-sizing:border-box;height:100vh;overflow-y:auto;scrollbar-width:none}main::-webkit-scrollbar{display:none}
  .workspace-section{max-width:1120px}.section-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}.section-title h2{font-size:30px}.section-title p{margin:7px 0 0;color:#7890a5;font-size:13px}.service-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:16px}.service-strip article{display:flex;align-items:center;gap:11px;padding:15px 16px;border:1px solid var(--line);border-radius:20px;background:#0b1623}.service-strip article>i{width:9px;height:9px;border-radius:50%;background:#ff7474;box-shadow:0 0 0 6px rgba(255,116,116,.07)}.service-strip article.ok>i{background:#61d8a5;box-shadow:0 0 0 6px rgba(97,216,165,.07)}.service-strip span{display:flex;min-width:0;flex-direction:column;gap:3px}.service-strip small{overflow:hidden;color:#7890a5;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.network-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.network-grid article,.inbound-board,.check-grid article{border:1px solid var(--line);background:linear-gradient(145deg,rgba(14,26,41,.96),rgba(8,15,25,.96))}.network-grid article{padding:24px;border-radius:28px}.network-grid article>strong{display:block;margin-top:36px;font-size:38px}.network-grid article>small{color:#7890a5}.network-grid article.offline{opacity:.64}.inbound-board{margin-top:16px;padding:22px;border-radius:28px}.inbound-board>header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.inbound-board h3{margin:5px 0 0;font-size:20px}.inbound-board>header>strong{padding:8px 12px;border-radius:14px;background:rgba(97,216,165,.08);color:#78e1b4;font-size:11px}.inbound-board>div{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.inbound-board article{display:grid;grid-template-columns:9px minmax(0,1fr) auto;align-items:center;gap:12px;padding:13px 14px;border-radius:18px;background:rgba(3,9,16,.48)}.inbound-board article>i{width:8px;height:8px;border-radius:50%;background:#61d8a5}.inbound-board article>i.off{background:#ff7474}.inbound-board article>span{display:flex;min-width:0;flex-direction:column;gap:3px}.inbound-board article b,.inbound-board article small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.inbound-board article small{color:#71879a;font-size:10px}.inbound-board article em{color:#9bd9ff;font-size:10px;font-style:normal;font-weight:800}.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.check-grid article{display:flex;align-items:center;gap:14px;padding:20px;border-radius:24px}.check-grid article>i{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;background:#172433;color:#8ca1b4;font-style:normal;font-weight:900}.check-grid article div{display:flex;flex-direction:column;gap:4px}.check-grid span{color:#7890a5;font-size:12px}@media(max-width:900px){.service-strip{grid-template-columns:1fr 1fr}}@media(max-width:720px){.network-grid,.check-grid,.inbound-board>div{grid-template-columns:1fr}.service-strip{grid-template-columns:1fr 1fr}}
  .network-grid article>p{margin:9px 0 0;color:#71879a;font-size:11px}.node-name>em{margin-left:auto;padding:6px 9px;border-radius:12px;background:rgba(97,216,165,.09);color:#78e1b4;font-size:9px;font-style:normal;font-weight:900;text-transform:uppercase}.node-name>em.bad{background:rgba(255,116,116,.09);color:#ff9c9c}.node-day{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}.node-day>span{padding:6px 9px;border-radius:11px;background:rgba(155,217,255,.06);color:#8da7bc;font-size:9px;font-weight:800}
  .deep-test{width:100%;min-height:38px;margin-top:14px;border:0;border-radius:15px;background:#14283a;color:#a9dfff;font-weight:800;cursor:pointer}.deep-test:hover{background:#1b354b}.deep-test:disabled{opacity:.55}.diagnostic-result{padding:9px 11px!important;border-radius:12px;background:rgba(255,116,116,.07);color:#ff9c9c!important}.diagnostic-result.good{background:rgba(97,216,165,.07);color:#78e1b4!important}
  .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.support-workspace{height:min(760px,calc(100vh - 132px));min-height:500px;display:grid;grid-template-columns:minmax(280px,360px) minmax(0,1fr);gap:14px}.thread-list,.admin-chat{min-width:0;min-height:0;border:1px solid var(--line);border-radius:22px;background:#10141c;overflow:hidden}.thread-list{position:static;height:auto;display:grid;grid-template-rows:auto auto auto minmax(0,1fr);padding:18px}.support-list-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.support-list-head h2{display:flex;align-items:center;gap:8px;margin-top:5px}.support-list-head h2 small{display:grid;min-width:22px;height:22px;place-items:center;border-radius:8px;background:rgba(145,214,255,.1);color:#9bd9ff;font-size:11px}.support-icon-button{width:42px;height:42px;border:1px solid rgba(145,214,255,.16);border-radius:13px;background:#151c26;color:#bfe8ff;font-size:20px;cursor:pointer}.support-search{display:block;margin-top:15px}.support-search input{box-sizing:border-box;width:100%;height:44px;border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:0 14px;background:#0b1017;color:#eef7ff;font:inherit;font-size:13px}.support-search input::placeholder{color:#667383}.support-list-status{min-height:28px;display:flex;align-items:center;gap:8px;color:#8799aa;font-size:11px}.support-spinner{display:inline-block;width:15px;height:15px;border:2px solid rgba(145,214,255,.2);border-top-color:#9bd9ff;border-radius:50%;animation:spin .75s linear infinite}.thread-items{min-height:0;margin:0 -6px;padding-right:3px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#253442 transparent}.thread-items>button{box-sizing:border-box;width:100%;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:11px;min-height:68px;padding:10px;border:1px solid transparent;border-radius:16px;background:transparent;color:#eaf4fc;text-align:left;cursor:pointer;transition:background .16s,border-color .16s,transform .16s}.thread-items>button:hover{background:#141b25;border-color:rgba(145,214,255,.08);transform:translateY(-1px)}.thread-items>button.active{border-color:rgba(145,214,255,.16);background:linear-gradient(90deg,rgba(145,214,255,.13),rgba(145,214,255,.035))}.thread-items>button>i{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:#172b3c;color:#aeddff;font-style:normal;font-weight:900}.thread-items span{min-width:0;display:flex;flex-direction:column;gap:5px}.thread-items b,.thread-items small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.thread-items small{color:#7f91a2;font-size:11px}.thread-items em{display:grid;place-items:center;min-width:22px;height:22px;padding:0 4px;border-radius:8px;background:#9bd9ff;color:#07111d;font-size:10px;font-style:normal;font-weight:900}.admin-chat{display:grid;grid-template-rows:auto minmax(0,1fr) auto}.conversation-head{min-height:70px;align-items:center;margin:0!important;padding:0 22px;border-bottom:1px solid rgba(255,255,255,.06)}.conversation-head>div{display:flex;min-width:0;flex:1;flex-direction:column;gap:4px}.conversation-head b,.conversation-head small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.conversation-head small{color:#77899a;font-size:11px}.conversation-badge{padding:6px 9px;border-radius:9px;background:rgba(97,216,165,.08);color:#78e1b4;font-size:9px;font-weight:800;text-transform:uppercase}.support-back{display:none;border:0;background:transparent;color:#9bd9ff;font:inherit;font-weight:800;cursor:pointer}.chat-messages{min-width:0;min-height:0;padding:22px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#253442 transparent}.chat-messages article{box-sizing:border-box;width:fit-content;max-width:min(72%,680px);display:flex;flex-direction:column;gap:6px;margin:0 auto 12px 0;padding:12px 15px;border:1px solid rgba(255,255,255,.045);border-radius:17px 17px 17px 5px;background:#151d28;color:#eaf2f9;overflow-wrap:anywhere;line-height:1.5}.chat-messages article.admin{margin-left:auto;margin-right:0;border-color:rgba(145,214,255,.12);border-radius:17px 17px 5px 17px;background:#18354a}.chat-messages small{color:#879aaa;font-size:10px}.reply-box{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;gap:8px 12px!important;padding:14px 16px!important;border-top:1px solid rgba(255,255,255,.06)!important}.reply-box>label{grid-column:1/-1;color:#aabac8;font-size:11px;font-weight:800}.reply-box textarea{box-sizing:border-box;grid-column:1/-1;width:100%;min-height:72px;max-height:150px;resize:vertical;border:1px solid rgba(255,255,255,.075)!important;border-radius:14px!important;padding:12px 14px!important;background:#0b1118!important;color:#fff;font:inherit;line-height:1.45;outline:0}.reply-meta{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;gap:12px}.reply-meta small{color:#697c8d;font-size:10px}.reply-meta button{min-width:116px;min-height:42px;border:0;border-radius:12px!important;padding:0 18px!important;background:#9bd9ff;color:#07111d;font-weight:900;cursor:pointer}.reply-status{grid-column:1/-1;min-height:15px;margin:0;color:#78e1b4;font-size:11px}.reply-status.error-text{color:#ffaaaa}.support-state{display:grid;place-content:center;justify-items:center;min-height:170px;padding:24px;text-align:center;color:#8092a3}.support-state b{color:#eaf4fc}.support-state p{max-width:340px;margin:7px 0 13px;font-size:12px;line-height:1.5}.support-state button{min-height:38px;border:1px solid rgba(145,214,255,.16);border-radius:11px;padding:0 14px;background:#172433;color:#bfe8ff;font-weight:800;cursor:pointer}.support-state.error{color:#d59a9a}.support-state.error b{color:#ffb5b5}.support-state .quiet{margin-top:7px;border-color:transparent;background:transparent;color:#8ba1b4}.conversation-state{grid-row:1/-1;min-height:100%}.conversation-empty{min-height:100%}.mobile-list-action{display:none}.support-workspace button:focus-visible,.support-workspace input:focus-visible,.support-workspace textarea:focus-visible,nav button:focus-visible{outline:3px solid #9bd9ff;outline-offset:2px}.support-workspace button:disabled{cursor:not-allowed;opacity:.42;filter:saturate(.45)}
  @media(max-width:900px){.support-workspace{height:calc(100vh - 126px);min-height:460px;grid-template-columns:1fr}.support-workspace>.thread-list,.support-workspace>.admin-chat{grid-area:1/1}.support-workspace>.admin-chat{display:none}.support-workspace.detail-open>.thread-list{display:none}.support-workspace.detail-open>.admin-chat{display:grid}.support-back{display:flex;align-items:center;gap:7px}.conversation-head{padding:0 16px}.conversation-badge{display:none}.mobile-list-action{display:block}}
  @media(max-width:560px){nav{justify-content:space-between}nav button{display:none!important}nav button:nth-child(1),nav button:nth-child(2),nav button:nth-child(4),nav button:nth-child(8),nav button:nth-child(11){display:flex!important}.support-workspace{height:calc(100dvh - 180px);min-height:420px;gap:0}.thread-list,.admin-chat{border-radius:18px}.thread-list{padding:14px}.support-list-head h2{font-size:19px}.chat-messages{padding:15px}.chat-messages article{max-width:88%}.reply-box{padding:12px!important}.reply-meta{align-items:flex-end}.reply-meta small{max-width:50%}.reply-meta button{min-width:108px}.conversation-head{min-height:62px;gap:12px}.support-back span{display:none}}
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
  .panel,.metrics article,.network-grid article,.inbound-board,.check-grid article,.scheme-board,.thread-list,.admin-chat{border-color:rgba(255,255,255,.065);background:#10141c;box-shadow:0 18px 50px rgba(0,0,0,.16)}
  .panel,.scheme-board,.inbound-board,.network-grid article{border-radius:22px}.metrics article{border-radius:18px}
  .health{border-radius:18px;background:linear-gradient(90deg,rgba(62,149,118,.12),rgba(16,20,28,.98));border-color:rgba(109,213,170,.11)}
  .metrics{grid-template-columns:1.2fr repeat(3,1fr)}.metrics article:first-child{background:linear-gradient(145deg,rgba(50,113,151,.22),#10141c 72%)}
  .service-strip article{border-radius:14px;background:#0c1118}.service-strip article>i{box-shadow:none}
  .network-grid article{background:linear-gradient(150deg,#121923,#0d1118)}
  .scheme-grid>article,.inbound-board article,.device-control article,.referral-metrics article{border:1px solid rgba(255,255,255,.045);border-radius:15px;background:#0c1118}
  .scheme-grid>article.auto{background:linear-gradient(135deg,rgba(56,126,167,.19),#0c1118)}
  .deep-test,.filters button{border-radius:12px!important}.deep-test{background:#172535}.refresh{border-radius:13px;background:#111720}
  .section-health .scheme-board,.section-health .remna-board{display:none}
  .section-schemes .service-strip,.section-schemes .network-grid,.section-schemes .remna-board{display:none}
  .section-nodes .scheme-board{display:none}
  @media(max-width:1100px){.console{grid-template-columns:82px minmax(0,1fr)}aside{padding-inline:10px}.brand span,nav span,.owner span{display:none}.brand,nav button,.owner{justify-content:center;padding-inline:0}.metrics{grid-template-columns:1fr 1fr}}
  /* Compact ArcVPN shell: original cold palette, Axottle-like information density. */
  .console{grid-template-columns:272px minmax(0,1fr)}
  .brand{background:transparent;border-bottom:1px solid rgba(255,255,255,.055);border-radius:0}.brand img{width:38px}.brand span{font-size:20px}
  main{width:min(1560px,calc(100% - 64px));padding-top:26px}main>header{margin-bottom:22px;padding-bottom:18px}h1{font-size:32px;letter-spacing:-.035em}.live-tools{gap:10px}
  :global(body.admin-console-open #app){max-width:none}
  @media(max-width:1100px){.console{grid-template-columns:82px minmax(0,1fr)}main{width:calc(100% - 32px)}}
  @media(max-width:560px){.console{display:block}.console>aside>nav{height:48px;margin-top:0;overflow:visible}}
</style>
