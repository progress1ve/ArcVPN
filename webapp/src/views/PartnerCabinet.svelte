<script>
  import { onMount } from 'svelte'
  let data = null, loading = true, busy = false, error = '', login = '', password = ''
  let source = '', from = '', to = '', tab = 'purchases', copied = ''
  let page = 1
  const money = (v) => new Intl.NumberFormat('ru-RU', { style:'currency', currency:'RUB' }).format(Number(v || 0) / 100)
  const date = (v) => v ? new Date(v.includes('T') ? v : v.replace(' ', 'T') + 'Z').toLocaleString('ru-RU') : '—'
  const kinds = { new:'Покупка', renew:'Продление', upgrade:'Смена тарифа', addon_device:'Устройства', addon_lte:'Трафик', addon_combined:'Устройства и трафик', accrual:'Начисление', adjustment:'Корректировка', refund:'Возврат', reversal:'Отмена', payout:'Ручная выплата' }
  const messages = { invalid_credentials:'Неверный логин или пароль либо доступ отозван.', login_rate_limited:'Слишком много попыток. Повторите через 15 минут.', unauthorized:'Сессия завершилась. Войдите снова.' }
  async function api(path, body) {
    const response = await fetch('/api/partners/' + path, { credentials:'same-origin', cache:'no-store',
      ...(body ? { method:'POST', headers:{ 'Content-Type':'application/json' }, body:JSON.stringify(body) } : {}) })
    const value = await response.json()
    if (!response.ok) { const e = new Error(messages[value.error] || 'Не удалось выполнить запрос. Повторите позже.'); e.status = response.status; throw e }
    return value
  }
  async function load() {
    loading = true; error = ''
    try { data = await api('cabinet?' + new URLSearchParams({ source, from, to, page:String(page) })) }
    catch (e) { if (e.status === 401) data = null; else error = e.message; page = data?.page || 1 }
    finally { loading = false }
  }
  async function signIn() {
    busy = true; error = ''
    try { await api('login', { login, password }); password = ''; await load() }
    catch (e) { error = e.message }
    finally { busy = false }
  }
  async function signOut() {
    busy = true
    try { await api('logout', {}); data = null; password = ''; error = '' }
    catch (e) { error = e.message }
    finally { busy = false }
  }
  async function copy(link) {
    try { await navigator.clipboard.writeText(link); copied = link }
    catch { error = 'Не удалось скопировать. Выделите ссылку вручную.' }
  }
  function applyFilters() { page = 1; load() }
  function selectTab(value) { tab = value; page = 1; load() }
  function turnPage(delta) { page += delta; load() }
  onMount(() => {
    document.documentElement.dataset.partner = 'true'
    load()
    return () => { delete document.documentElement.dataset.partner }
  })
</script>

<svelte:head><title>Партнёрский кабинет — ArcVPN</title><meta name="robots" content="noindex,nofollow" /></svelte:head>

<div class="partner">
  <header><a class="brand" href="/partner"><span>A</span> ArcVPN <small>Партнёры</small></a>{#if data}<button class="quiet" disabled={busy} on:click={signOut}>Выйти</button>{/if}</header>
  {#if !data}
    <main class="login">
      {#if loading}<p role="status">Проверяем сессию…</p>{:else}
        <form on:submit|preventDefault={signIn}>
          <p class="eyebrow">Партнёрский кабинет</p><h1>Вход в ArcVPN</h1><p class="muted">Логин и пароль предоставляет владелец сервиса.</p>
          <label>Логин<input bind:value={login} autocomplete="username" maxlength="64" required /></label>
          <label>Пароль<input type="password" bind:value={password} autocomplete="current-password" maxlength="256" required /></label>
          {#if error}<p class="error" role="alert">{error}</p>{/if}
          <button disabled={busy || !login || !password}>{busy ? 'Проверяем…' : 'Войти'}</button>
        </form>
      {/if}
    </main>
  {:else}
    <main>
      <div class="heading"><div><p class="eyebrow">Партнёрский кабинет</p><h1>{data.partner.name}</h1><p class="muted">Закреплённые клиенты и вознаграждения</p></div><button class="quiet" disabled={loading} on:click={load}>{loading ? 'Обновляем…' : 'Обновить'}</button></div>
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      <section class="totals" aria-label="Все начисления">
        {#each [['Начислено',data.balance.accrued],['Корректировки',data.balance.adjustments],['Выплачено',data.balance.paid],['Доступно к выплате',data.balance.available]] as item}
          <div class="metric"><span>{item[0]}</span><strong>{money(item[1])}</strong></div>
        {/each}
      </section>
      <p class="muted">Остаток за всё время. Выплаты переводит владелец вручную.{#if data.balance.debt > 0} Задолженность по корректировкам: {money(data.balance.debt)}.{/if}</p>
      <section class="panel">
        <h2>Назначенные ссылки</h2>
        {#each data.sources as link}
          <div class="link"><div><b>{link.name}</b><small>{link.active && link.enabled ? 'Активна' : 'Отключена · история сохранена'}</small><a href={link.url} target="_blank" rel="noreferrer">{link.url}</a></div><button class="quiet" on:click={() => copy(link.url)}>{copied === link.url ? 'Скопировано' : 'Копировать'}</button></div>
        {:else}<p class="muted">Ссылки ещё не назначены.</p>{/each}
      </section>
      <p class="muted">Период — по московскому времени. Привлечённые считаются по дате закрепления, покупки — по дате оплаты.</p>
      <form class="filters" on:submit|preventDefault={applyFilters}>
        <label>Ссылка<select bind:value={source}><option value="">Все ссылки</option>{#each data.sources as link}<option value={link.id}>{link.name}</option>{/each}</select></label>
        <label>С даты<input type="date" bind:value={from} /></label><label>По дату<input type="date" bind:value={to} /></label>
        <button disabled={loading}>Применить</button>
      </form>
      <section class="stats" aria-label="Показатели за выбранный период">
        {#each [['Привлечено',data.stats.clients],['Оплативших клиентов',data.stats.paying_clients],['Покупки',data.stats.purchases],['Продления',data.stats.renewals]] as item}<div><b>{item[1]}</b><span>{item[0]}</span></div>{/each}
      </section>
      <nav class="tabs" aria-label="Разделы кабинета">
        {#each [['purchases','Покупки'],['clients','Клиенты'],['journal','Журнал'],['payouts','Выплаты']] as item}<button disabled={loading} class:active={tab === item[0]} on:click={() => selectTab(item[0])}>{item[1]}</button>{/each}
      </nav>
      <section class="panel">
        <div class="table-wrap">
          {#if tab === 'purchases'}
            <table><thead><tr><th>Клиент</th><th>Дата</th><th>Покупка</th><th>Оплачено</th><th>Ставка</th><th>Вознаграждение</th></tr></thead><tbody>
              {#each data.purchases as row}<tr><td>{row.client}</td><td>{date(row.purchase_at)}</td><td>{kinds[row.purchase_kind] || row.purchase_kind}</td><td>{money(row.purchase_cents)}</td><td>{row.rate_bps / 100}%</td><td>{money(row.amount_cents)}</td></tr>{:else}<tr><td colspan="6">Подтверждённых покупок за этот период нет.</td></tr>{/each}
            </tbody></table>
          {:else if tab === 'clients'}
            <table><thead><tr><th>Клиент</th><th>Закреплён</th><th>Ссылка</th><th>Ставка</th><th>Покупки</th></tr></thead><tbody>
              {#each data.clients as row}<tr><td>{row.client}</td><td>{date(row.bound_at)}</td><td>{row.source_name}</td><td>{row.rate_bps / 100}%</td><td>{row.purchases}</td></tr>{:else}<tr><td colspan="5">Привлечённых клиентов за этот период нет.</td></tr>{/each}
            </tbody></table>
          {:else}
            <table><thead><tr><th>Дата</th><th>Операция</th><th>Сумма</th><th>Способ</th><th>Примечание</th></tr></thead><tbody>
              {#each tab === 'payouts' ? data.payouts : data.journal as row}<tr><td>{date(row.occurred_at)}</td><td>{kinds[row.kind]}</td><td>{money(row.amount_cents)}</td><td>{row.method || '—'}</td><td>{row.note || '—'}</td></tr>{:else}<tr><td colspan="5">Операций за этот период нет.</td></tr>{/each}
            </tbody></table>
          {/if}
        </div>
        <div class="pagination"><button class="quiet" disabled={loading || page <= 1} on:click={() => turnPage(-1)}>Назад</button><span class="muted">Страница {data.page}</span><button class="quiet" disabled={loading || !data.has_more[tab]} on:click={() => turnPage(1)}>Далее</button></div>
      </section>
      <p class="muted">Пробные периоды не участвуют в начислениях. Ставка закрепляется за клиентом и сохраняется для следующих покупок.</p>
    </main>
  {/if}
</div>

<style>
  :global(html[data-partner] #app){max-width:none}
  :global(html[data-partner] body){background:#080a10}
  .partner{min-height:100dvh;background:#080a10;color:#e9edfa;font-family:Inter,system-ui,sans-serif}
  header{padding:20px max(20px,calc((100% - 1200px)/2));display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #252b3a}
  .brand{display:flex;align-items:center;gap:10px;color:inherit;font-weight:700;text-decoration:none}.brand span{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:#6d82ff;color:white}.brand small{color:#94a1c0;font-weight:400;margin-left:8px}
  main{max-width:1200px;padding:32px 24px 60px;margin:auto}.login{min-height:75dvh;display:grid;place-items:center}.login form{width:min(100%,390px);padding:30px;background:#10131e;border:1px solid #252b3a;border-radius:16px}.login button{width:100%;margin-top:12px}
  h1{font-size:30px;margin:6px 0 12px;line-height:1.2}h2{font-size:18px;margin:0 0 20px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#9ba8ff;margin:0}.muted,small{color:#94a1c0;font-size:13px;line-height:1.6}.heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:25px}
  label{display:flex;flex-direction:column;gap:8px;font-size:12px;color:#94a1c0;margin:14px 0}input,select{width:100%;min-height:44px;box-sizing:border-box;border:1px solid #2b3650;background:#161b29;color:#e9edfa;border-radius:9px;padding:10px 12px;font:inherit}
  button{min-height:42px;padding:10px 18px;background:#6d82ff;color:white;border:1px solid transparent;border-radius:9px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;transition:background .15s}button:hover{background:#5a6ff0}button:disabled{opacity:.5;cursor:wait}button.quiet,.tabs button{background:#161b29;border-color:#2b3650;color:#e9edfa}.quiet:hover,.tabs button:hover{background:#252d42}
  :is(button,a,input,select):focus-visible{outline:2px solid #a5b2ff;outline-offset:3px}.error{color:#ffb6b6;background:#301a23;border:1px solid #603043;padding:12px;border-radius:9px}
  .totals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.metric{background:#10131e;border:1px solid #252b3a;border-radius:12px;padding:22px}.metric span{font-size:12px;color:#94a1c0}.metric strong{display:block;font-size:25px;margin-top:12px;font-variant-numeric:tabular-nums}.metric:last-child{border-color:#5261ac}
  .panel{background:#10131e;border:1px solid #252b3a;border-radius:12px;padding:22px;margin:24px 0}.link{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 0;border-top:1px solid #252b3a}.link div{min-width:0}.link small,.link a{display:block}.link a{font-size:13px;color:#a5b2ff;overflow-wrap:anywhere;margin-top:5px}
  .filters{display:flex;gap:16px;align-items:end;flex-wrap:wrap}.filters label{flex:1;min-width:150px}.filters button{margin-bottom:14px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}.stats div{display:flex;flex-direction:column;gap:7px}.stats b{font-size:24px}.stats span{font-size:12px;color:#94a1c0}
  .tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button.active{background:#6d82ff;color:white}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;text-align:left;font-size:13px}th{font-size:11px;color:#94a1c0;font-weight:500;white-space:nowrap}th,td{padding:14px 12px;border-bottom:1px solid #252b3a}td{max-width:350px;overflow-wrap:anywhere;vertical-align:top;font-variant-numeric:tabular-nums}td:first-child{white-space:nowrap}
  .pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:20px}
  @media(max-width:850px){.totals{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:480px){main{padding:24px 16px}.heading{align-items:flex-start}h1{font-size:24px}.metric{padding:15px}.metric strong{font-size:21px}.panel{padding:15px}.link{align-items:flex-start;flex-direction:column}.brand small{display:none}.filters label{min-width:125px}.login form{padding:22px}.filters button{width:100%}}
  @media(prefers-reduced-motion:reduce){button{transition:none}}
</style>
