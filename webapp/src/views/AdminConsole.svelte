<script>
  import { onMount } from 'svelte'
  import ArcIcon from '../components/ArcIcon.svelte'
  import { fetchAdminOverview } from '../lib/api.js'

  let data = null
  let loading = true
  let error = ''
  let active = 'overview'
  const nav = [
    ['overview', 'home', 'Обзор'], ['users', 'users', 'Пользователи'],
    ['payments', 'wallet', 'Платежи'], ['network', 'signal', 'Инфраструктура'],
    ['support', 'headset', 'Поддержка'], ['settings', 'settings', 'Настройки'],
  ]
  const rub = (v) => `${new Intl.NumberFormat('ru-RU').format(Number(v || 0))} ₽`
  const num = (v) => new Intl.NumberFormat('ru-RU').format(Number(v || 0))

  async function load() {
    loading = true; error = ''
    try { data = await fetchAdminOverview() }
    catch (e) { error = e.code === 403 ? 'Откройте панель из админского аккаунта Telegram' : 'Данные временно недоступны' }
    finally { loading = false }
  }
  onMount(load)
</script>

<svelte:head><title>ArcVPN Business Console</title></svelte:head>

<div class="console">
  <aside>
    <a class="brand" href="/admin"><img src="/app/assets/arc-flow/arc-logo.svg" alt="" /><span>ArcVPN<small>Business console</small></span></a>
    <nav>{#each nav as item}<button class:active={active === item[0]} on:click={() => active = item[0]} title={item[2]}><ArcIcon name={item[1]} size={20} weight="duotone" /><span>{item[2]}</span></button>{/each}</nav>
    <div class="owner"><i>К</i><span>Владелец<small>Полный доступ</small></span></div>
  </aside>

  <main>
    <header><div><span class="eyebrow">Бизнес в реальном времени</span><h1>Всё под контролем.</h1></div><button class="refresh" on:click={load}><ArcIcon name="pulse" size={18} />Обновить</button></header>
    {#if loading}
      <section class="state"><i class="loader"></i><p>Собираем показатели ArcVPN…</p></section>
    {:else if error}
      <section class="state"><ArcIcon name="shield" size={30} /><h2>Доступ закрыт</h2><p>{error}</p></section>
    {:else if active !== 'overview'}
      <section class="state"><ArcIcon name="gift" size={30} /><h2>{nav.find(i => i[0] === active)?.[2]}</h2><p>Раздел входит в следующий этап Business Console.</p></section>
    {:else}
      <section class:alert={!data.local_panel.healthy} class="health"><i></i><div><b>{data.local_panel.healthy ? 'Сеть ArcVPN работает штатно' : 'Требуется внимание к сети'}</b><span>{data.local_panel.inbounds} из 8 inbound · проверено только что</span></div><strong>{data.local_panel.healthy ? 'Стабильно' : data.local_panel.detail}</strong></section>
      <section class="metrics">
        <article><span>Выручка за месяц</span><strong>{rub(data.revenue.month.total_rub)}</strong><small>{num(data.revenue.month.count)} платежей</small></article>
        <article><span>Активные подписки</span><strong>{num(data.subscriptions.active)}</strong><small>+{num(data.subscriptions.month)} за 30 дней</small></article>
        <article><span>Trial → оплата</span><strong>{Number(data.conversion.conversion_rate).toFixed(1)}%</strong><small>{num(data.conversion.converted)} конверсий</small></article>
        <article><span>Сейчас онлайн</span><strong>{num(data.activity.online_now)}</strong><small>{num(data.activity.week)} за неделю</small></article>
      </section>
      <div class="grid">
        <section class="panel">
          <div class="panel-head"><div><span>Инфраструктура</span><h2>Узлы сети</h2></div><button on:click={() => active = 'network'}>Все узлы <ArcIcon name="arrow" size={16} /></button></div>
          <div class="nodes">{#each data.servers as server}<article><div class="node-name"><i class:offline={!server.is_active}></i><div><b>{server.name}</b><span>{server.is_active ? 'Доступен' : 'Отключён'}</span></div></div><strong>{num(server.active_clients)}</strong><small>активных клиентов</small><div class="bar"><i style={`width:${Math.min(100,(server.active_clients/Math.max(1,server.clients_count))*100)}%`}></i></div></article>{/each}</div>
        </section>
        <section class="panel queue">
          <div class="panel-head"><div><span>Рабочая очередь</span><h2>Требует внимания</h2></div></div>
          <button><i><ArcIcon name="wallet" size={18} /></i><span><b>Незавершённые платежи</b><small>Проверить YooKassa</small></span><strong>{data.operations.pending_payments}</strong></button>
          <button><i class="violet"><ArcIcon name="headset" size={18} /></i><span><b>Открытые обращения</b><small>Пользователи ждут ответа</small></span><strong>{data.operations.open_support_threads}</strong></button>
          <button><i class="green"><ArcIcon name="users" size={18} /></i><span><b>Новые пользователи</b><small>За последние 24 часа</small></span><strong>{data.users.day}</strong></button>
        </section>
      </div>
    {/if}
  </main>
</div>

<style>
  :global(body){margin:0;background:#050a12;color:#f4f8fc}.console{--card:#0c1522;--line:rgba(162,207,244,.1);min-height:100vh;display:grid;grid-template-columns:250px 1fr;font-family:Inter,system-ui,sans-serif;background:radial-gradient(900px 600px at 95% -10%,rgba(65,146,214,.16),transparent 65%),#050a12}
  aside{position:sticky;top:0;height:100vh;box-sizing:border-box;display:flex;flex-direction:column;padding:28px 20px;border-right:1px solid var(--line);background:rgba(5,10,18,.76);backdrop-filter:blur(20px)}.brand{display:flex;align-items:center;gap:12px;padding:0 10px 28px;color:#fff;text-decoration:none;font-weight:800}.brand img{width:34px}.brand span,.owner span{display:flex;flex-direction:column}.brand small,.owner small{margin-top:2px;color:#70859a;font-size:10px;text-transform:uppercase;letter-spacing:.08em}
  nav{display:grid;gap:8px}nav button{display:flex;align-items:center;gap:13px;min-height:48px;padding:0 15px;border:0;border-radius:16px;color:#8499ad;background:transparent;font-weight:700;cursor:pointer;transition:.2s}nav button:hover{color:#dceeff;background:rgba(126,194,241,.06);transform:translateX(2px)}nav button.active{color:#08111d;background:#9bd9ff;box-shadow:0 10px 30px rgba(89,174,230,.18)}.owner{margin-top:auto;display:flex;align-items:center;gap:11px;padding:13px;border-radius:18px;background:#0b1420}.owner>i{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#17314a;color:#9bd9ff;font-style:normal;font-weight:800}
  main{width:min(1320px,calc(100% - 64px));margin:0 auto;padding:48px 0 72px}header{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:32px}h1{margin:8px 0 0;font-size:clamp(34px,4vw,60px);line-height:.98;letter-spacing:-.055em}.eyebrow,.panel-head span{color:#6f879d;font-size:11px;font-weight:800;letter-spacing:.11em;text-transform:uppercase}.refresh{display:flex;align-items:center;gap:8px;min-height:44px;padding:0 18px;border:1px solid var(--line);border-radius:22px;background:#0b1420;color:#bcd0e2;font-weight:700;cursor:pointer}
  .health{display:flex;align-items:center;gap:14px;padding:18px 22px;border:1px solid rgba(109,213,170,.12);border-radius:22px;background:linear-gradient(90deg,rgba(49,140,108,.13),rgba(12,21,34,.88))}.health>i{width:10px;height:10px;border-radius:50%;background:#61d8a5;box-shadow:0 0 0 7px rgba(97,216,165,.08)}.health div{display:flex;flex:1;flex-direction:column;gap:3px}.health span{color:#8096aa;font-size:12px}.health>strong{padding:8px 12px;border-radius:14px;background:rgba(97,216,165,.09);color:#78e1b4;font-size:12px}.health.alert>i{background:#ff7979}
  .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.metrics article,.panel{border:1px solid var(--line);background:linear-gradient(145deg,rgba(14,26,41,.96),rgba(8,15,25,.96))}.metrics article{min-height:120px;padding:22px;border-radius:24px;display:flex;flex-direction:column}.metrics span,.metrics small{color:#7890a5;font-size:12px}.metrics strong{margin:auto 0 5px;font-size:30px;letter-spacing:-.045em}.metrics small{color:#9bd9ff}
  .grid{display:grid;grid-template-columns:1.35fr 1fr;gap:16px}.panel{padding:24px;border-radius:28px}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}h2{margin:6px 0 0;font-size:21px}.panel-head button{display:flex;align-items:center;gap:6px;border:0;background:transparent;color:#8fcdf5;cursor:pointer}.nodes{display:grid;grid-template-columns:1fr 1fr;gap:12px}.nodes article{padding:18px;border-radius:20px;background:rgba(4,10,18,.56)}.node-name{display:flex;align-items:center;gap:9px}.node-name>i{width:8px;height:8px;border-radius:50%;background:#60d7a4}.node-name>i.offline{background:#ff7474}.node-name div{display:flex;flex-direction:column}.node-name span,.nodes small{color:#6f8497;font-size:11px}.nodes article>strong{display:block;margin-top:24px;font-size:27px}.bar{height:4px;margin-top:14px;border-radius:2px;background:#162534;overflow:hidden}.bar i{display:block;height:100%;background:#91d6ff}
  .queue>button{width:100%;display:flex;align-items:center;gap:12px;padding:13px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:#dbe8f3;text-align:left}.queue>button:last-child{border-bottom:0}.queue button>i{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;color:#9bd9ff;background:#102942}.queue button>i.violet{color:#c2afff;background:#211b3b}.queue button>i.green{color:#79deb2;background:#102d27}.queue button span{display:flex;flex:1;flex-direction:column;gap:3px}.queue button small{color:#70879b}.queue button>strong{display:grid;place-items:center;min-width:32px;height:32px;border-radius:50%;background:#122131}
  .state{min-height:55vh;display:grid;place-content:center;justify-items:center;text-align:center;color:#8196a9}.state h2{color:#fff}.loader{width:34px;height:34px;border:3px solid #183047;border-top-color:#9bd9ff;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
  @media(max-width:900px){.console{grid-template-columns:76px 1fr}aside{padding:20px 10px}.brand span,nav span,.owner span{display:none}.brand{justify-content:center;padding-inline:0}nav button{justify-content:center;padding:0}.owner{justify-content:center;background:transparent}.metrics{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}main{width:calc(100% - 32px);padding-top:28px}}
  @media(max-width:560px){.console{display:block}aside{position:fixed;z-index:10;top:auto;bottom:12px;left:12px;right:12px;height:64px;flex-direction:row;padding:8px;border:1px solid var(--line);border-radius:24px}.brand,.owner{display:none}nav{display:flex;width:100%;justify-content:space-around}nav button{width:48px;min-height:48px;border-radius:18px}nav button:nth-child(n+5){display:none}main{padding:26px 0 100px}header{align-items:flex-start}.refresh{width:44px;padding:0;justify-content:center;font-size:0}.health>strong{display:none}.metrics{gap:10px}.metrics article{min-height:105px;padding:17px}.metrics strong{font-size:24px}.nodes{grid-template-columns:1fr}.panel{padding:19px;border-radius:24px}}
</style>
