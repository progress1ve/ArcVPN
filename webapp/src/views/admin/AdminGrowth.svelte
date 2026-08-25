<script>
  import { onMount } from 'svelte'
  import {
    createAdminCampaign, createAdminPromocode, fetchAdminCampaigns,
    fetchAdminPromocodes, updateAdminCampaign, updateAdminPromocode,
  } from '../../lib/api.js'

  export let canManageCampaigns = false
  export let canManagePromocodes = false
  let tab = 'campaigns'
  let campaigns = []
  let promocodes = []
  let loading = true
  let error = ''
  let notice = ''
  let busy = ''
  let campaign = { name: '', code: '', entry_bonus_days: 0, payment_bonus_days: 0 }
  let promo = { code: '', discount_type: 'percent', discount_value: 10, max_uses: 100, duration_days: 30 }
  const integer = (value) => Number.isInteger(Number(value)) ? Number(value) : NaN
  const rub = (cents) => `${new Intl.NumberFormat('ru-RU').format(Number(cents || 0) / 100)} ₽`
  const number = (value) => new Intl.NumberFormat('ru-RU').format(Number(value || 0))
  const date = (value) => value ? new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)) : 'без срока'
  $: campaignValid = campaign.name.trim().length > 1 && (!campaign.code || /^[A-Za-z0-9_-]{4,40}$/.test(campaign.code)) && integer(campaign.entry_bonus_days) >= 0 && integer(campaign.entry_bonus_days) <= 365 && integer(campaign.payment_bonus_days) >= 0 && integer(campaign.payment_bonus_days) <= 365
  $: promoValid = /^[A-Za-z0-9_-]{3,32}$/.test(promo.code) && integer(promo.discount_value) > 0 && (promo.discount_type === 'fixed' || integer(promo.discount_value) <= 100) && integer(promo.max_uses) > 0 && integer(promo.duration_days) > 0

  onMount(load)
  async function load() {
    loading = true; error = ''; notice = ''
    try {
      const [campaignResult, promoResult] = await Promise.all([fetchAdminCampaigns(), fetchAdminPromocodes()])
      campaigns = campaignResult.campaigns || []
      promocodes = promoResult.promocodes || []
    } catch (e) { error = `Growth-данные недоступны: ${e.reason || e.message}` }
    finally { loading = false }
  }
  async function addCampaign() {
    if (!canManageCampaigns || !campaignValid || busy) return
    busy = 'campaign-create'; error = ''; notice = ''
    try {
      const result = await createAdminCampaign({ ...campaign, name: campaign.name.trim(), code: campaign.code.trim() || undefined, entry_bonus_days: integer(campaign.entry_bonus_days), payment_bonus_days: integer(campaign.payment_bonus_days) })
      campaigns = result.campaigns || []
      campaign = { name: '', code: '', entry_bonus_days: 0, payment_bonus_days: 0 }
      notice = 'Рекламная ссылка создана и готова к first-touch атрибуции.'
    } catch (e) { error = `Не удалось создать кампанию: ${e.reason || e.message}` }
    finally { busy = '' }
  }
  async function toggleCampaign(item) {
    if (!canManageCampaigns || busy) return
    busy = `campaign-${item.id}`; error = ''; notice = ''
    try { campaigns = (await updateAdminCampaign(item.id, { is_active: !item.is_active })).campaigns || [] }
    catch (e) { error = `Статус кампании не изменён: ${e.reason || e.message}` }
    finally { busy = '' }
  }
  async function copyLink(item) {
    if (!item.link) return
    try { await navigator.clipboard.writeText(item.link); notice = `Ссылка «${item.name}» скопирована.` }
    catch { error = 'Браузер не разрешил копирование. Выделите ссылку вручную.' }
  }
  async function addPromo() {
    if (!canManagePromocodes || !promoValid || busy) return
    busy = 'promo-create'; error = ''; notice = ''
    try {
      const result = await createAdminPromocode({ ...promo, code: promo.code.trim().toUpperCase(), discount_value: integer(promo.discount_value), max_uses: integer(promo.max_uses), duration_days: integer(promo.duration_days) })
      promocodes = result.promocodes || []
      promo = { code: '', discount_type: 'percent', discount_value: 10, max_uses: 100, duration_days: 30 }
      notice = 'Промокод создан. Он будет списан только после подтверждённой оплаты.'
    } catch (e) { error = `Не удалось создать промокод: ${e.reason || e.message}` }
    finally { busy = '' }
  }
  async function togglePromo(item) {
    if (!canManagePromocodes || busy) return
    busy = `promo-${item.id}`; error = ''; notice = ''
    try { promocodes = (await updateAdminPromocode(item.id, { is_active: !item.is_active })).promocodes || [] }
    catch (e) { error = `Статус промокода не изменён: ${e.reason || e.message}` }
    finally { busy = '' }
  }
</script>

<section class="growth" aria-labelledby="growth-title" aria-busy={loading}>
  <header><span>ПРИВЛЕЧЕНИЕ И КОНВЕРСИЯ</span><h2 id="growth-title">Growth-центр</h2><p>Сравнивайте рекламные источники и управляйте скидками без удаления истории.</p></header>
  <div class="tabs" role="tablist" aria-label="Инструменты роста">
    <button role="tab" aria-selected={tab === 'campaigns'} class:active={tab === 'campaigns'} on:click={() => tab = 'campaigns'}>Рекламные ссылки <b>{campaigns.length}</b></button>
    <button role="tab" aria-selected={tab === 'promocodes'} class:active={tab === 'promocodes'} on:click={() => tab = 'promocodes'}>Промокоды <b>{promocodes.length}</b></button>
  </div>
  {#if error}<div class="state error" role="alert"><span>{error}</span><button disabled={loading} on:click={load}>Повторить</button></div>{/if}
  {#if notice}<div class="state notice" role="status">{notice}</div>{/if}
  {#if loading}<div class="state skeleton" role="status">Загружаем воронки и скидки…</div>{/if}

  {#if !loading && tab === 'campaigns'}
    <form class="creator" on:submit|preventDefault={addCampaign} aria-label="Новая рекламная ссылка">
      <div class="form-head"><div><b>Новая рекламная ссылка</b><small>Первый источник пользователя сохраняется навсегда.</small></div><span>first-touch</span></div>
      <label class="wide"><span>Понятное название</span><input bind:value={campaign.name} maxlength="100" placeholder="Яндекс · брендовый поиск" required disabled={!canManageCampaigns || busy}/></label>
      <label><span>Код ссылки</span><input bind:value={campaign.code} maxlength="40" pattern="[A-Za-z0-9_-]{4,40}" placeholder="создастся автоматически" disabled={!canManageCampaigns || busy}/></label>
      <label><span>Бонус за вход, дней</span><input bind:value={campaign.entry_bonus_days} type="number" min="0" max="365" disabled={!canManageCampaigns || busy}/></label>
      <label><span>Бонус за оплату, дней</span><input bind:value={campaign.payment_bonus_days} type="number" min="0" max="365" disabled={!canManageCampaigns || busy}/></label>
      <button class="primary" disabled={!canManageCampaigns || !campaignValid || busy}>{busy === 'campaign-create' ? 'Создаём…' : 'Создать ссылку'}</button>
      {#if !canManageCampaigns}<p class="read-only">Ваша роль может смотреть статистику, но не менять кампании.</p>{/if}
    </form>
    <div class="cards" aria-label="Сравнение рекламных ссылок">
      {#each campaigns as item}
        <article class:inactive={!item.is_active}>
          <div class="card-head"><div><span class="status"><i></i>{item.is_active ? 'активна' : 'остановлена'}</span><h3>{item.name}</h3><code>{item.code}</code></div><button class="toggle" disabled={!canManageCampaigns || busy} on:click={() => toggleCampaign(item)}>{busy === `campaign-${item.id}` ? 'Сохраняем…' : item.is_active ? 'Остановить' : 'Запустить'}</button></div>
          <div class="metrics"><span><small>ПРИШЛИ</small><b>{number(item.arrivals)}</b></span><span><small>ОПЛАТИЛИ</small><b>{number(item.paying_users)}</b></span><span class="accent"><small>КОНВЕРСИЯ</small><b>{Number(item.conversion_percent || 0).toLocaleString('ru-RU')}%</b></span><span><small>ВЫРУЧКА</small><b>{rub(item.revenue_cents)}</b></span></div>
          <div class="link-row"><input readonly value={item.link || 'Ссылка недоступна'} aria-label={`Рекламная ссылка ${item.name}`}/><button disabled={!item.link} on:click={() => copyLink(item)}>Копировать</button></div>
          <footer><span>Оплат: {number(item.paid_orders)}</span><span>Повторных: {number(item.repeat_paid_orders)}</span><span>Бонус: +{number(item.entry_bonus_days)} / +{number(item.payment_bonus_days)} дн.</span></footer>
        </article>
      {/each}
      {#if !campaigns.length}<div class="empty"><b>Рекламных ссылок пока нет</b><p>Создайте первую кампанию, чтобы сравнивать приходы и оплаты.</p></div>{/if}
    </div>
  {:else if !loading}
    <form class="creator promo-form" on:submit|preventDefault={addPromo} aria-label="Новый промокод">
      <div class="form-head"><div><b>Новый промокод</b><small>Использование фиксируется только после успешной оплаты.</small></div><span>paid-only</span></div>
      <label><span>Код</span><input bind:value={promo.code} maxlength="32" pattern="[A-Za-z0-9_-]{3,32}" placeholder="START20" required disabled={!canManagePromocodes || busy}/></label>
      <label><span>Тип скидки</span><select bind:value={promo.discount_type} disabled={!canManagePromocodes || busy}><option value="percent">Процент</option><option value="fixed">Рубли</option></select></label>
      <label><span>{promo.discount_type === 'percent' ? 'Скидка, %' : 'Скидка, ₽'}</span><input bind:value={promo.discount_value} type="number" min="1" max={promo.discount_type === 'percent' ? 100 : 1000000} disabled={!canManagePromocodes || busy}/></label>
      <label><span>Всего использований</span><input bind:value={promo.max_uses} type="number" min="1" disabled={!canManagePromocodes || busy}/></label>
      <label><span>Срок, дней</span><input bind:value={promo.duration_days} type="number" min="1" max="3650" disabled={!canManagePromocodes || busy}/></label>
      <button class="primary" disabled={!canManagePromocodes || !promoValid || busy}>{busy === 'promo-create' ? 'Создаём…' : 'Создать промокод'}</button>
      {#if !canManagePromocodes}<p class="read-only">Ваша роль может смотреть промокоды, но не менять их.</p>{/if}
    </form>
    <div class="promo-list">
      {#each promocodes as item}
        <article class:inactive={!item.is_active}>
          <div><span class="status"><i></i>{item.is_active ? 'активен' : 'отключён'}</span><h3>{item.code}</h3><p>{item.discount_type === 'percent' ? `${item.discount_percent}%` : `${item.discount_rub} ₽`} · до {date(item.expires_at)}</p></div>
          <div class="usage"><b>{number(item.used_count)} <small>/ {number(item.max_uses)}</small></b><span>использовано</span><progress max={Math.max(1, item.max_uses)} value={item.used_count || 0}>{item.used_count}/{item.max_uses}</progress></div>
          <button class="toggle" disabled={!canManagePromocodes || busy} on:click={() => togglePromo(item)}>{busy === `promo-${item.id}` ? 'Сохраняем…' : item.is_active ? 'Отключить' : 'Включить'}</button>
        </article>
      {/each}
      {#if !promocodes.length}<div class="empty"><b>Промокодов пока нет</b><p>Создайте скидку для рекламной кампании или возврата клиентов.</p></div>{/if}
    </div>
  {/if}
</section>

<style>
  .growth{display:grid;gap:18px;max-width:1180px;min-width:0}.growth>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.growth h2{margin:8px 0 6px;font-size:30px}.growth p{margin:0;color:#7890a5}.tabs{display:flex;gap:6px;width:max-content;max-width:100%;padding:4px;border:1px solid rgba(155,217,255,.1);border-radius:14px;background:#0d1219}.tabs button{min-height:40px;border:0;border-radius:10px;padding:0 14px;background:transparent;color:#7890a5;font-weight:800}.tabs button.active{background:#182330;color:#dff3ff}.tabs b{margin-left:6px;color:#80c9f4}.state{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-radius:13px;background:#14283a;color:#bde7ff}.state.error{background:rgba(150,54,65,.15);color:#ffb1b6}.state button{min-height:36px;border:0;border-radius:9px;padding:0 12px;background:#24394c;color:#eaf4fc}.creator{display:grid;grid-template-columns:minmax(170px,1.4fr) repeat(2,minmax(130px,.7fr)) auto;gap:10px;padding:16px;border:1px solid rgba(155,217,255,.1);border-radius:20px;background:linear-gradient(135deg,#111821,#0e131a)}.form-head{grid-column:1/-1;display:flex;align-items:start;justify-content:space-between;gap:12px}.form-head div{display:grid;gap:4px}.form-head b{font-size:16px}.form-head small,label span{color:#7890a5;font-size:10px}.form-head>span{padding:5px 8px;border-radius:8px;background:#142d34;color:#7de1c2;font-size:9px;font-weight:900;letter-spacing:.08em}.creator label{display:grid;gap:6px;min-width:0}.creator label span{font-weight:800}.creator input,.creator select,.creator button{box-sizing:border-box;width:100%;min-width:0;min-height:43px;border:1px solid rgba(155,217,255,.08);border-radius:11px;padding:0 11px;background:#0a1017;color:#eaf4fc}.creator .primary{align-self:end;border-color:transparent;background:#9bd9ff;color:#07111d;font-weight:900}.read-only{grid-column:1/-1;font-size:11px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.cards article,.promo-list article{min-width:0;padding:17px;border:1px solid rgba(155,217,255,.08);border-radius:18px;background:#10151d}.cards article.inactive,.promo-list article.inactive{opacity:.65}.card-head{display:flex;align-items:start;justify-content:space-between;gap:12px}.card-head h3,.promo-list h3{margin:8px 0 3px;font-size:18px}.card-head code{color:#7890a5;font-size:10px}.status{display:inline-flex;align-items:center;gap:6px;color:#7de1c2;font-size:9px;font-weight:900;text-transform:uppercase}.status i{width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 0 4px rgba(89,205,164,.1)}.inactive .status{color:#8996a3}.toggle{min-height:36px;border:1px solid rgba(155,217,255,.12);border-radius:10px;padding:0 11px;background:#111d28;color:#bde7ff}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:16px 0}.metrics span{min-width:0;padding:11px;border-radius:12px;background:#0b1118}.metrics small{display:block;overflow:hidden;color:#657c8f;font-size:8px;text-overflow:ellipsis}.metrics b{display:block;margin-top:7px;overflow-wrap:anywhere;font-size:17px}.metrics .accent{background:linear-gradient(145deg,rgba(83,182,147,.18),#0b1118)}.link-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px}.link-row input{min-width:0;min-height:38px;border:0;border-radius:10px;padding:0 10px;background:#090e14;color:#6f879b}.link-row button{border:0;border-radius:10px;padding:0 12px;background:#1b2d3d;color:#bde7ff}.cards footer{display:flex;flex-wrap:wrap;gap:6px 12px;margin-top:12px;color:#6f879b;font-size:10px}.promo-form{grid-template-columns:repeat(5,minmax(110px,1fr)) auto}.promo-list{display:grid;gap:7px}.promo-list article{display:grid;grid-template-columns:minmax(0,1fr) minmax(130px,220px) auto;align-items:center;gap:16px}.promo-list p{font-size:11px}.usage{display:grid;gap:5px}.usage b{font-size:19px}.usage b small,.usage span{color:#7890a5;font-size:10px}.usage progress{width:100%;height:5px;border:0;border-radius:5px;overflow:hidden;background:#25313d}.usage progress::-webkit-progress-bar{background:#25313d}.usage progress::-webkit-progress-value{background:#78c8f7}.empty{grid-column:1/-1;padding:38px 20px;border:1px dashed rgba(155,217,255,.16);border-radius:18px;text-align:center}.empty b{display:block;margin-bottom:7px}.empty p{font-size:12px}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #9bd9ff;outline-offset:2px}button:disabled,input:disabled,select:disabled{cursor:not-allowed;opacity:.48}@media(max-width:1000px){.creator,.promo-form{grid-template-columns:repeat(2,minmax(0,1fr))}.creator .form-head,.creator .read-only{grid-column:1/-1}.creator .primary{grid-column:2}.cards{grid-template-columns:1fr}}@media(max-width:620px){.growth h2{font-size:25px}.tabs{width:100%}.tabs button{flex:1;min-width:0;padding:0 8px}.creator,.promo-form{grid-template-columns:minmax(0,1fr)}.creator label,.creator .form-head,.creator .primary,.creator .read-only{grid-column:1}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.promo-list article{grid-template-columns:minmax(0,1fr)}.promo-list .toggle{justify-self:start}.link-row{grid-template-columns:minmax(0,1fr)}.link-row button{min-height:38px}.cards article,.promo-list article{padding:14px}}@media(max-width:370px){.tabs{display:grid}.metrics{grid-template-columns:1fr 1fr}.card-head{display:grid}.toggle{justify-self:start}}
</style>
