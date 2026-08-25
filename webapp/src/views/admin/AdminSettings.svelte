<script>
  import { onMount } from 'svelte'
  import { assignAdminRole, fetchAdminRoles } from '../../lib/api.js'
  export let data
  export let effectiveAccess = null
  export let canManageRoles = false
  export let currentRole = ''
  const label={
    'overview.read':'Обзор и метрики','nodes.diagnose':'Диагностика нод','catalog.manage':'Каталог подписки','subscriptions.manage':'Управление подписками','campaigns.manage':'Рекламные кампании','promocodes.manage':'Промокоды','expenses.manage':'Расходы','support.read':'Чтение поддержки','support.reply':'Ответы поддержки','audit.read':'Журнал аудита','backups.read':'Просмотр снимков','backups.create':'Создание снимков','roles.manage':'Роли администраторов'
  }
  const roleLabel={owner:'Владелец',operator:'Оператор',support:'Поддержка',finance:'Финансы',viewer:'Наблюдатель'}
  let assignments=[];let rolesLoading=false;let rolesError='';let rolesNotice='';let telegramId='';let selectedRole='viewer';let assigning=false
  $: accessEntries=effectiveAccess&&typeof effectiveAccess==='object'?Object.entries(effectiveAccess):[]
  const state=(value,ok='Готово',bad='Недоступно')=>value===true?{text:ok,tone:'ok'}:value===false?{text:bad,tone:'bad'}:{text:'Нет данных',tone:'unknown'}
  $: remnawaveState=state(data?.remnawave?.healthy,'Подключена','Недоступна')
  $: subscriptionState=state(data?.operations?.subscription_service,'Работает','Остановлен')
  $: recurringState=state(data?.recurring?.provider_ready,'Готово','Не готово')
  $: smtpState=state(data?.integrations?.smtp_ready,'Настроен','Не настроен')
  $: databaseState=data?.system?.database_integrity==='ok'?{text:'Исправна',tone:'ok'}:data?.system?.database_integrity?{text:'Требует внимания',tone:'bad'}:{text:'Нет данных',tone:'unknown'}
  $: diskValue=Number(data?.system?.disk_used_pct)
  $: diskState=Number.isFinite(diskValue)?{text:`${diskValue}%`,tone:diskValue<80?'ok':'bad'}:{text:'Нет данных',tone:'unknown'}
  $: roleId=Number(telegramId)
  $: roleValid=Number.isInteger(roleId)&&roleId>0
  async function loadRoles(){if(!canManageRoles)return;rolesLoading=true;rolesError='';try{assignments=(await fetchAdminRoles()).assignments||[]}catch(error){rolesError=`Не удалось загрузить роли: ${error.reason||error.message}`}finally{rolesLoading=false}}
  async function assign(){if(!canManageRoles||assigning||!roleValid)return;assigning=true;rolesError='';rolesNotice='';try{assignments=(await assignAdminRole(roleId,selectedRole)).assignments||[];rolesNotice='Роль назначена и будет применена при следующей проверке доступа.';telegramId=''}catch(error){rolesError=`Не удалось назначить роль: ${error.reason||error.message}`}finally{assigning=false}}
  onMount(loadRoles)
</script>

<section class="page">
  <header><span>КОНФИГУРАЦИЯ</span><h2>Настройки сервиса</h2><p>Наблюдаемое состояние интеграций и текущие права — без переключателей, которых нет в серверном контракте.</p></header>
  {#if !data}<p class="state" role="status">Ожидаем телеметрию сервиса…</p>{/if}
  <div class="groups">
    <section><h3>Control plane</h3><article><span><b>Remnawave</b><small>{data?.remnawave?.detail||'Центральная панель и пользователи'}</small></span><em class={remnawaveState.tone}>{remnawaveState.text}</em></article><article><span><b>Subscription API</b><small>Состояние systemd-сервиса публичной выдачи</small></span><em class={subscriptionState.tone}>{subscriptionState.text}</em></article></section>
    <section><h3>Платежи и связь</h3><article><span><b>YooKassa recurring</b><small>{data?.recurring?.active??0} активных привязок по данным API</small></span><em class={recurringState.tone}>{recurringState.text}</em></article><article><span><b>SMTP</b><small>{data?.integrations?.smtp_tls?'Отправка с TLS':'Состояние TLS не подтверждено'}</small></span><em class={smtpState.tone}>{smtpState.text}</em></article></section>
    <section><h3>Хранилище</h3><article><span><b>Основная база</b><small>SQLite quick_check: {data?.system?.database_integrity||'нет данных'}</small></span><em class={databaseState.tone}>{databaseState.text}</em></article><article><span><b>Диск</b><small>{data?.system?.disk_used_gb??'—'} из {data?.system?.disk_total_gb??'—'} ГБ</small></span><em class={diskState.tone}>{diskState.text}</em></article></section>
    {#if accessEntries.length}<section><h3>Эффективный доступ</h3><p class="hint">Текущая роль: {roleLabel[currentRole]||currentRole||'не определена'}.</p>{#each accessEntries as permission}<article><span><b>{label[permission[0]]||permission[0]}</b><small>{permission[0]}</small></span><em class:ok={permission[1]} class:bad={!permission[1]}>{permission[1]?'Разрешено':'Запрещено'}</em></article>{/each}</section>{/if}
    {#if canManageRoles}<section class="accounts"><h3>Роли администраторов</h3><p class="hint">Назначение по Telegram ID. Удаление и управление сессиями сервер пока не поддерживает.</p><form on:submit|preventDefault={assign}><label><span>Telegram ID</span><input bind:value={telegramId} inputmode="numeric" pattern="[0-9]+" required aria-invalid={telegramId&&!roleValid}/></label><label><span>Роль</span><select bind:value={selectedRole}>{#each Object.entries(roleLabel) as item}<option value={item[0]}>{item[1]}</option>{/each}</select></label><button disabled={assigning||!roleValid}>{assigning?'Назначаем…':'Назначить'}</button></form>{#if rolesError}<div class="role-state error" role="alert"><span>{rolesError}</span><button on:click={loadRoles} disabled={rolesLoading}>Повторить</button></div>{/if}{#if rolesNotice}<p class="role-state" role="status">{rolesNotice}</p>{/if}{#if rolesLoading}<p class="role-state" role="status">Загружаем назначения…</p>{:else if !rolesError&&!assignments.length}<p class="role-state">Отдельных назначений пока нет.</p>{:else}{#each assignments as assignment}<article><span><b>Telegram {assignment.telegram_id}</b><small>Назначил: {assignment.assigned_by||'password-session'} · {assignment.updated_at||assignment.created_at||'—'}</small></span><em class="ok">{roleLabel[assignment.role]||assignment.role}</em></article>{/each}{/if}</section>{/if}
  </div>
</section>

<style>
.page{min-width:0}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 5px;font-size:30px}.page p{margin:0;color:#7890a5}.state{margin-top:18px!important;padding:14px;border-radius:13px;background:#14283a;color:#bde7ff!important}.groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:22px}.groups section{min-width:0;padding:22px;border:1px solid rgba(155,217,255,.1);border-radius:24px;background:linear-gradient(145deg,#101b29,#0a121d)}.groups h3{margin:0 0 12px}.groups article{display:flex;align-items:center;gap:15px;padding:15px 0;border-top:1px solid rgba(155,217,255,.07)}.groups article span{display:flex;min-width:0;flex:1;flex-direction:column;gap:4px}.groups b,.groups small{overflow-wrap:anywhere}.groups small{color:#7890a5}.groups em{padding:7px 10px;border-radius:12px;background:rgba(255,190,106,.09);color:#ffc57d;font-size:10px;font-style:normal;font-weight:900;white-space:nowrap}.groups em.ok{background:rgba(97,216,165,.09);color:#78e1b4}.groups em.bad{background:rgba(255,121,121,.1);color:#ff9c9c}.groups em.unknown{background:rgba(157,178,196,.08);color:#9db2c4}.hint{margin:-5px 0 12px!important;font-size:11px}.accounts form{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto;gap:8px;margin:14px 0}.accounts label{display:grid;gap:5px;color:#7890a5;font-size:10px}.accounts input,.accounts select,.accounts button{box-sizing:border-box;min-width:0;min-height:42px;border:1px solid rgba(155,217,255,.12);border-radius:11px;padding:0 11px;background:#0b1119;color:#eaf4fc}.accounts button{align-self:end;background:#9bd9ff;color:#07111d;font-weight:900}.role-state{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:10px 0!important;padding:12px;border-radius:11px;background:#14283a;color:#bde7ff!important}.role-state.error{background:rgba(150,54,65,.15);color:#ffb1b6!important}.role-state button{min-height:34px;border:0;border-radius:9px;padding:0 10px;background:#223d55;color:#dff3ff}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #9bd9ff;outline-offset:2px}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:900px){.groups{grid-template-columns:1fr}}@media(max-width:520px){.page h2{font-size:25px}.groups section{padding:18px}.groups article{align-items:flex-start;flex-direction:column}.groups em{white-space:normal}.accounts form{grid-template-columns:1fr}.accounts button{width:100%}}
</style>
