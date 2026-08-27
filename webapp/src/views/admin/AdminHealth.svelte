<script>
  import ArcIcon from '../../components/ArcIcon.svelte'
  export let data
  export let onRefresh
  let view = 'events'
  let refreshing = false
  const tabs = [['events', 'События'], ['nodes', 'Ноды'], ['services', 'Сервисы']]
  $: nodes = data?.remnawave?.nodes || []
  $: diskPct = Number(data?.system?.disk_used_pct || 0)
  $: memoryPct = data?.system?.memory?.used_pct == null ? null : Number(data.system.memory.used_pct)
  $: load1m = data?.system?.load_1m == null ? null : Number(data.system.load_1m)
  $: cpuCount = Number(data?.system?.cpu_count || 0)
  $: activeNodes = nodes.filter((node) => !node.disabled)
  $: incidents = [
    ...(!data?.remnawave?.healthy ? [{ severity: 'critical', title: 'Remnawave недоступна', detail: data?.remnawave?.detail || 'Панель не подтвердила работоспособность', object: 'remnawave' }] : []),
    ...(data?.operations?.subscription_service === false ? [{ severity: 'critical', title: 'Subscription API остановлен', detail: 'Публичная выдача подписок требует проверки', object: 'arcvpn-subscription.service' }] : []),
    ...activeNodes.filter((node) => !node.connected).map((node) => ({ severity: 'critical', title: `Нода «${node.name}» недоступна`, detail: node.last_status_message || 'Нет соединения с RemnaNode', object: node.address })),
    ...(data?.system?.database_integrity !== 'ok' ? [{ severity: 'critical', title: 'Нарушена целостность базы', detail: String(data?.system?.database_integrity || 'unknown'), object: 'database' }] : []),
    ...(diskPct >= 85 ? [{ severity: diskPct >= 90 ? 'critical' : 'warning', title: diskPct >= 90 ? 'Критически мало места на диске' : 'Заканчивается место на диске', detail: `Использовано ${diskPct}%`, object: 'storage' }] : []),
    ...(memoryPct != null && memoryPct >= 80 ? [{ severity: memoryPct >= 90 ? 'critical' : 'warning', title: 'Высокое использование памяти', detail: `Использовано ${memoryPct}% RAM`, object: 'poland-control-plane' }] : []),
    ...(load1m != null && cpuCount > 0 && load1m >= cpuCount ? [{ severity: load1m >= cpuCount * 1.5 ? 'critical' : 'warning', title: 'Высокая системная нагрузка', detail: `Load 1m ${load1m} при ${cpuCount} CPU`, object: 'poland-control-plane' }] : []),
    ...(data?.operations?.bot_service === false ? [{ severity: 'critical', title: 'Telegram-бот остановлен', detail: 'arcvpn-bot.service не активен', object: 'arcvpn-bot.service' }] : []),
    ...(data?.operations?.hysteria_service === false ? [{ severity: 'warning', title: 'Hysteria-сервис не подтверждён', detail: 'Проверьте актуальные Hysteria2 апстримы', object: 'arcvpn-hysteria.service' }] : []),
    ...activeNodes.filter((node) => node.connected && Number(node.memory_used_pct || 0) >= 85).map((node) => ({ severity: Number(node.memory_used_pct) >= 92 ? 'critical' : 'warning', title: `Высокая память на «${node.name}»`, detail: `Использовано ${node.memory_used_pct}%`, object: node.address })),
  ]
  $: criticalCount = incidents.filter((item) => item.severity === 'critical').length
  $: services = [
    { name: 'Remnawave', ok: Boolean(data?.remnawave?.healthy), detail: data?.remnawave?.healthy ? 'Работает штатно' : data?.remnawave?.detail || 'Нет подтверждения' },
    { name: 'Subscription API', ok: Boolean(data?.operations?.subscription_service), detail: data?.operations?.subscription_service ? 'Сервис активен' : 'Сервис остановлен' },
    { name: 'База ArcVPN', ok: data?.system?.database_integrity === 'ok', detail: data?.system?.database_integrity === 'ok' ? 'Целостность подтверждена' : String(data?.system?.database_integrity || 'Нет данных') },
    { name: 'Telegram-бот', ok: Boolean(data?.operations?.bot_service), detail: data?.operations?.bot_service ? 'Сервис активен' : 'Сервис остановлен' },
    { name: 'Hysteria2', ok: Boolean(data?.operations?.hysteria_service), detail: data?.operations?.hysteria_service ? 'Сервис активен' : 'Нет подтверждения' },
    { name: 'Диск Poland', ok: diskPct > 0 && diskPct < 85, detail: diskPct ? `${diskPct}% занято` : 'Нет данных' },
    { name: 'Память Poland', ok: memoryPct != null && memoryPct < 80, detail: memoryPct == null ? 'Нет данных' : `${memoryPct}% занято` },
  ]
  async function refresh() { if (refreshing) return; refreshing = true; try { await onRefresh?.() } finally { refreshing = false } }
</script>

<section class="page" aria-labelledby="health-title">
  <header><div><span>НАБЛЮДАЕМОСТЬ</span><h2 id="health-title">Здоровье системы</h2><p>Аварии, деградации и состояние инфраструктуры.</p></div><button on:click={refresh} disabled={refreshing} aria-busy={refreshing}><ArcIcon name="pulse" size={18}/>{refreshing ? 'Проверяем…' : 'Проверить сейчас'}</button></header>
  <div class:danger={criticalCount > 0} class:warning={!criticalCount && incidents.length} class="score" role="status" aria-live="polite"><b aria-hidden="true">{incidents.length ? '!' : '✓'}</b><span><em>{criticalCount ? 'КРИТИЧЕСКОЕ СОСТОЯНИЕ' : incidents.length ? 'ТРЕБУЕТСЯ ВНИМАНИЕ' : 'СИСТЕМА В НОРМЕ'}</em><h3>{incidents.length ? `${incidents.length} активных условий` : 'Активных предупреждений нет'}</h3><p>{activeNodes.length ? `${activeNodes.filter((node) => node.connected).length}/${activeNodes.length} рабочих нод подключены` : 'Ноды не обнаружены'} · неизвестные значения не считаются здоровыми.</p></span><div><b>{data?.remnawave?.online_users?.length || 0}</b><small>пользователей онлайн</small></div></div>
  <nav aria-label="Состояние системы">{#each tabs as tab}<button aria-pressed={view === tab[0]} class:active={view === tab[0]} on:click={() => view = tab[0]}>{tab[1]}{#if tab[0] === 'events'} <i>{incidents.length}</i>{/if}</button>{/each}</nav>
  <div class="rows">
    {#if view === 'events'}
      {#if incidents.length}{#each incidents as item}<article class:warning={item.severity === 'warning'}><i></i><span><b>{item.title}</b><p>{item.detail}</p><small>{item.object}</small></span></article>{/each}{:else}<article class="ok"><i></i><span><b>Все проверки пройдены</b><p>Remnawave, Subscription API, база и хранилище не сообщают об авариях.</p></span></article>{/if}
    {:else if view === 'nodes'}
      {#if activeNodes.length}{#each activeNodes as node}<article class:ok={node.connected}><i></i><span><b>{node.name}</b><p>{node.connected ? `${node.users_online ?? '—'} онлайн · RAM ${node.memory_used_pct == null ? '—' : `${node.memory_used_pct}%`} · load ${node.load_1m ?? '—'} · ↓ ${Math.round(Number(node.rx_bps||0)/1024)} / ↑ ${Math.round(Number(node.tx_bps||0)/1024)} Кбит/с` : node.last_status_message || 'RemnaNode недоступна'}</p><small>{node.address} · Xray uptime {node.xray_uptime_seconds ? `${Math.floor(node.xray_uptime_seconds/3600)} ч` : 'нет данных'} · inbounds {node.inbounds?.length ?? '—'}</small></span></article>{/each}{:else}<div class="empty"><b>Ноды не обнаружены</b><p>Проверьте подключение Remnawave и повторите сбор данных.</p></div>{/if}
    {:else}{#each services as service}<article class:ok={service.ok}><i></i><span><b>{service.name}</b><p>{service.detail}</p></span></article>{/each}{/if}
  </div>
</section>

<style>
.page{display:grid;min-width:0;gap:18px}.page>header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px}.page>header span,.score em{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 5px;font-size:clamp(25px,3vw,30px)}.page p{margin:0;color:#7890a5}.page>header button{display:flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border:1px solid rgba(155,217,255,.14);border-radius:14px;background:#14202e;color:#ccecff;cursor:pointer}.page>header button:disabled{cursor:wait;opacity:.55}.score{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:24px;padding:26px;border:1px solid rgba(155,217,255,.1);border-radius:26px;background:linear-gradient(110deg,#102438,#0a121d 65%)}.score.warning{background:linear-gradient(110deg,#2e291b,#0a121d 65%)}.score.danger{background:linear-gradient(110deg,#2b1c27,#0a121d 65%)}.score>b{display:grid;width:88px;height:88px;place-content:center;border:7px solid #61d8a5;border-radius:50%;font-size:28px}.score.warning>b{border-color:#e8b957}.score.danger>b{border-color:#ff8f8f}.score>b small{font-size:10px;color:#7890a5}.score h3{margin:7px 0;font-size:22px}.score>div{padding:15px;border-radius:17px;background:#0d1b29}.score>div b,.score>div small{display:block}.score>div b{font-size:25px}.score>div small{color:#7890a5}.page>nav{display:flex;gap:8px;overflow-x:auto;border-bottom:1px solid rgba(155,217,255,.08)}.page>nav button{min-height:44px;padding:0 16px;border:0;border-bottom:2px solid transparent;background:none;color:#7890a5;white-space:nowrap;cursor:pointer}.page>nav button.active{border-color:#9bd9ff;color:#fff}.page>nav i{padding:3px 7px;border-radius:10px;background:#15314a;color:#9bd9ff;font-style:normal}.rows{display:grid;gap:10px}.rows article{display:flex;align-items:center;gap:14px;min-width:0;padding:18px;border:1px solid rgba(155,217,255,.1);border-radius:19px;background:#0e1926}.rows article>i{flex:0 0 auto;width:9px;height:9px;border-radius:50%;background:#ff7979}.rows article.warning>i{background:#e8b957}.rows article.ok>i{background:#61d8a5}.rows span{display:flex;min-width:0;flex-direction:column;gap:5px}.rows small{overflow-wrap:anywhere;color:#6f879b}.empty{padding:30px;border:1px dashed #26394a;border-radius:19px;text-align:center}.empty b{display:block;margin-bottom:6px}:global(button:focus-visible){outline:2px solid #9bd9ff;outline-offset:3px}@media(max-width:850px){.score{grid-template-columns:1fr}.score>b{width:72px;height:72px}.page>header{align-items:flex-start}}@media(max-width:560px){.page>header{align-items:stretch;flex-direction:column}.page>header button{justify-content:center}.score{gap:16px;padding:20px}.score>div{width:fit-content}.rows article{align-items:flex-start;padding:15px}}
</style>
