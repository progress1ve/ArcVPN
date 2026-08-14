<script>
  import ArcIcon from '../../components/ArcIcon.svelte'
  export let data
  export let onRefresh
  $: nodes = data?.remnawave?.nodes || []
  $: incidents = [
    ...nodes.filter((node) => !node.connected).map((node) => ({ level: 'critical', title: `Нода «${node.name}» недоступна`, detail: node.last_status_message || 'Нет соединения с RemnaNode', object: node.address })),
    ...(data?.system?.database_integrity !== 'ok' ? [{ level: 'critical', title: 'Нарушена целостность базы ArcVPN', detail: String(data?.system?.database_integrity || 'unknown'), object: 'database' }] : []),
    ...(Number(data?.system?.disk_used_pct || 0) > 80 ? [{ level: 'warning', title: 'Заканчивается место на диске', detail: `Использовано ${data.system.disk_used_pct}%`, object: 'storage' }] : []),
  ]
</script>

<section class="page">
  <div class="titlebar"><div><span>НАБЛЮДАЕМОСТЬ</span><h2>Здоровье системы</h2><p>Один экран для аварий, деградаций и состояния всей инфраструктуры.</p></div><button on:click={onRefresh}><ArcIcon name="pulse" size={18}/>Проверить сейчас</button></div>
  <div class:danger={incidents.length} class="score"><div class="ring"><b>{incidents.length ? Math.max(25, 100-incidents.length*18) : 100}</b><small>из 100</small></div><div><span>{incidents.length ? 'ТРЕБУЕТСЯ ВНИМАНИЕ' : 'СИСТЕМА В НОРМЕ'}</span><h3>{incidents.length ? `${incidents.length} активных события` : 'Критических событий нет'}</h3><p>{nodes.filter(n=>n.connected).length}/{nodes.length} нод подключены · база {data?.system?.database_integrity === 'ok' ? 'исправна' : 'требует проверки'}</p></div><div class="summary"><article><b>{nodes.filter(n=>n.connected).length}</b><small>нод онлайн</small></article><article><b>{data?.remnawave?.online_users?.length || 0}</b><small>пользователей</small></article><article><b>{data?.system?.disk_used_pct || 0}%</b><small>диск</small></article></div></div>
  <div class="tabs"><button class="active">События <i>{incidents.length}</i></button><button>Ноды</button><button>Сервисы</button><button>История</button></div>
  <div class="events">
    {#if incidents.length}
      {#each incidents as incident}<article class={incident.level}><i></i><div><b>{incident.title}</b><p>{incident.detail}</p><small>{incident.object}</small></div><button>Разобрать <ArcIcon name="arrow" size={15}/></button></article>{/each}
    {:else}
      <article class="ok"><i></i><div><b>Все проверки пройдены</b><p>Remnawave, Subscription API, база данных и активные ноды отвечают штатно.</p><small>обновлено только что</small></div></article>
    {/if}
  </div>
  <div class="services">
    <article class:good={data?.remnawave?.healthy}><span>Remnawave</span><b>{data?.remnawave?.healthy ? 'Работает' : 'Ошибка'}</b></article>
    <article class:good={data?.operations?.subscription_service}><span>Subscription API</span><b>{data?.operations?.subscription_service ? 'Работает' : 'Ошибка'}</b></article>
    <article class:good={data?.system?.database_integrity === 'ok'}><span>База ArcVPN</span><b>{data?.system?.database_integrity === 'ok' ? 'Исправна' : 'Ошибка'}</b></article>
    <article class:good={Number(data?.system?.disk_used_pct || 0) < 80}><span>Хранилище</span><b>{data?.system?.disk_used_pct || 0}%</b></article>
  </div>
</section>

<style>
  .page{display:grid;gap:18px}.titlebar{display:flex;align-items:flex-end;justify-content:space-between}.titlebar span,.score span{color:#e99772;font-size:10px;font-weight:800;letter-spacing:.14em}.titlebar h2{margin:8px 0 5px;font-size:30px}.titlebar p,.score p{margin:0;color:#8d8687}.titlebar button,.events button{display:flex;align-items:center;gap:8px;border:1px solid #332b2c;border-radius:14px;background:#171315;color:#eee6e5;padding:12px 16px}.score{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:24px;padding:26px;border:1px solid #302729;border-radius:26px;background:linear-gradient(110deg,#20191b,#151214 62%)}.score.danger{background:linear-gradient(110deg,#2a1d1d,#151214 62%)}.ring{display:grid;place-items:center;width:92px;height:92px;border-radius:50%;border:8px solid #75d9ad;box-shadow:inset 0 0 0 1px #2d2929}.danger .ring{border-color:#f09a78}.ring b{font-size:28px}.ring small{margin-top:-23px;color:#8d8687}.score h3{margin:7px 0;font-size:23px}.summary{display:flex;gap:10px}.summary article{min-width:94px;padding:15px;border-radius:18px;background:#2a2325}.summary b,.summary small{display:block}.summary b{font-size:22px}.summary small{color:#938a8b}.tabs{display:flex;gap:8px;border-bottom:1px solid #2b2426}.tabs button{padding:13px 16px;border:0;border-bottom:2px solid transparent;background:none;color:#817a7c}.tabs button.active{border-color:#eca080;color:#fff}.tabs i{padding:3px 7px;border-radius:10px;background:#39282a;color:#f2a185;font-style:normal}.events{display:grid;gap:10px}.events article{display:flex;align-items:center;gap:14px;padding:18px;border:1px solid #302729;border-radius:19px;background:#171315}.events article>i{width:9px;height:9px;border-radius:50%;background:#f09a78}.events article.ok>i{background:#70d5a7}.events div{flex:1}.events p{margin:5px 0;color:#aaa0a1}.events small{color:#726b6c}.services{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.services article{padding:17px;border:1px solid #302729;border-radius:18px;background:#171315}.services span,.services b{display:block}.services span{color:#8f8789;font-size:12px}.services b{margin-top:10px;color:#ef8e82}.services article.good b{color:#72d5aa}@media(max-width:900px){.score{grid-template-columns:1fr}.summary,.services{grid-template-columns:1fr 1fr;display:grid}.titlebar{align-items:flex-start;gap:12px}.titlebar p{display:none}}
</style>
