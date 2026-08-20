<script>
  import { onMount } from 'svelte'
  import { fetchAdminAudit } from '../../lib/api.js'
  export let data
  $: security = data?.device_security || {}
  $: risks = Number(security.users_over_limit || 0) + Number(security.awaiting_reimport || 0)
  let events = []
  let auditError = ''
  onMount(async () => {
    try { events = (await fetchAdminAudit(50)).events || [] }
    catch (error) { auditError = error.code === 403 ? 'Недостаточно прав для просмотра аудита' : 'Аудит временно недоступен' }
  })
</script>

<section class="page">
  <header><div><span>КОНТРОЛЬ ДОСТУПА</span><h2>Безопасность</h2><p>Реальные привязки устройств и нарушения лимитов подписок.</p></div><strong class:danger={risks}>{risks ? `${risks} требуют внимания` : 'Нарушений нет'}</strong></header>
  <div class="metrics">
    <article><small>АКТИВНЫЕ УСТРОЙСТВА</small><b>{security.active_devices || 0}</b><p>Сейчас имеют доступ к подпискам</p></article>
    <article><small>ОТОЗВАННЫЕ</small><b>{security.revoked_devices || 0}</b><p>Больше не получают рабочие подключения</p></article>
    <article><small>ЖЁСТКАЯ ПРИВЯЗКА</small><b>{security.protected_users || 0}</b><p>Пользователи с контролем device token</p></article>
    <article class:danger={security.users_over_limit}><small>СВЕРХ ЛИМИТА</small><b>{security.users_over_limit || 0}</b><p>Аккаунты с лишними устройствами</p></article>
  </div>
  <section class="policy"><h3>Политика выдачи подписки</h3><div><i>1</i><span><b>Идентификация Happ</b><small>HWID проверяется при каждом обновлении.</small></span></div><div><i>2</i><span><b>Отозванные устройства блокируются</b><small>API отдаёт три понятные служебные строки вместо рабочего каталога.</small></span></div><div><i>3</i><span><b>Единый authority</b><small>Все публичные origin обслуживаются одной базой на польском control-plane.</small></span></div></section>
  <section class="audit"><h3>Журнал административных действий</h3>{#if auditError}<p>{auditError}</p>{:else if !events.length}<p>Событий пока нет.</p>{:else}<div>{#each events as event}<article><span><b>{event.action}</b><small>{event.actor_id || event.actor_type} · {event.target_type || 'system'}{event.target_id ? `/${event.target_id}` : ''}</small></span><em class:denied={event.outcome==='denied' || event.outcome==='failed'}>{event.outcome}</em><time>{new Date(event.created_at).toLocaleString('ru-RU')}</time></article>{/each}</div>{/if}</section>
</section>

<style>
  .page{display:grid;gap:18px}.page>header{display:flex;align-items:flex-end;justify-content:space-between}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 5px;font-size:30px}.page p{margin:0;color:#7890a5}.page>header>strong{padding:10px 14px;border-radius:15px;background:rgba(97,216,165,.1);color:#78e1b4;font-size:11px}.page>header>strong.danger{background:rgba(255,121,121,.1);color:#ff9c9c}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metrics article,.policy{border:1px solid rgba(155,217,255,.1);background:linear-gradient(145deg,#101b29,#0a121d)}.metrics article{padding:21px;border-radius:22px}.metrics small{color:#7890a5;font-size:9px;letter-spacing:.1em}.metrics b{display:block;margin:14px 0 8px;font-size:34px}.metrics p{font-size:11px;line-height:1.45}.metrics article.danger b{color:#ff9c9c}.policy{padding:24px;border-radius:24px}.policy h3{margin:0 0 18px}.policy>div{display:flex;align-items:center;gap:13px;padding:13px 0;border-top:1px solid rgba(155,217,255,.07)}.policy i{display:grid;width:36px;height:36px;place-items:center;border-radius:50%;background:#15314a;color:#9bd9ff;font-style:normal;font-weight:900}.policy span{display:flex;flex-direction:column;gap:4px}.policy small{color:#7890a5}@media(max-width:900px){.metrics{grid-template-columns:1fr 1fr}}
  .audit{padding:24px;border:1px solid rgba(155,217,255,.1);border-radius:24px;background:linear-gradient(145deg,#101b29,#0a121d)}.audit h3{margin:0 0 18px}.audit p,.audit small{color:#7890a5}.audit>div{display:grid}.audit article{display:grid;grid-template-columns:1fr auto 160px;align-items:center;gap:14px;padding:12px 0;border-top:1px solid rgba(155,217,255,.07)}.audit span{display:flex;flex-direction:column;gap:4px}.audit em{color:#78e1b4;font-size:11px;font-style:normal}.audit em.denied{color:#ff9c9c}.audit time{color:#7890a5;font-size:11px;text-align:right}@media(max-width:900px){.audit article{grid-template-columns:1fr auto}.audit time{display:none}}
</style>
