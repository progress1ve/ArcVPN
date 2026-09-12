<script>
  import ArcIcon from '../ArcIcon.svelte'
  export let groups = []
  export let active = 'overview'
  export let roleLabel = ['Администратор', 'Ограниченный доступ']
  export let onNavigate = () => {}
</script>

<aside class="admin-sidebar">
  <a class="brand" href="/admin" on:click|preventDefault={() => onNavigate('overview')}><img src="/app/arc-logo-new.webp" alt="" /><span>ArcVPN<small>Operations</small></span></a>
  <nav aria-label="Разделы админ-панели">
    {#each groups as group}
      <section class="nav-group" aria-label={group.label}>
        <h2>{group.label}</h2>
        {#each group.items as item}
          <button class:active={active === item.id} aria-current={active === item.id ? 'page' : undefined} aria-label={item.label} on:click={() => onNavigate(item.id)} title={item.label}><ArcIcon name={item.icon} size={19} weight="duotone" /><span>{item.label}</span></button>
        {/each}
      </section>
    {/each}
  </nav>
  <div class="owner"><i>{roleLabel[0][0]}</i><span>{roleLabel[0]}<small>{roleLabel[1]}</small></span></div>
</aside>

<style>
  .admin-sidebar{position:sticky;top:0;box-sizing:border-box;height:100vh;display:flex;flex-direction:column;padding:18px 14px;border-right:1px solid rgba(255,255,255,.055);background:#0b0d12}.brand{min-height:58px;display:flex;align-items:center;gap:12px;padding:0 12px 16px;border-bottom:1px solid rgba(255,255,255,.055);color:#fff;text-decoration:none;font-size:18px;font-weight:850}.brand img{width:36px}.brand span,.owner span{display:flex;flex-direction:column}.brand small,.owner small{margin-top:2px;color:#687786;font-size:9px;letter-spacing:.1em;text-transform:uppercase}.admin-sidebar nav{min-height:0;display:grid;align-content:start;gap:17px;margin-top:18px;overflow-y:auto;scrollbar-width:none}.nav-group{display:grid;gap:3px}.nav-group h2{margin:0 12px 4px;color:#5f6c79;font-size:9px;letter-spacing:.12em;text-transform:uppercase}.nav-group button{width:100%;min-height:42px;display:flex;align-items:center;gap:12px;padding:0 12px;border:0;border-radius:11px;background:transparent;color:#8e98a6;font-size:12px;font-weight:700;text-align:left;cursor:pointer}.nav-group button:hover{background:rgba(255,255,255,.04);color:#eaf5fd}.nav-group button.active{background:linear-gradient(90deg,rgba(145,214,255,.15),rgba(145,214,255,.045));color:#bfe8ff;box-shadow:inset 3px 0 #91d6ff}.nav-group button:focus-visible{outline:3px solid #9bd9ff;outline-offset:2px}.owner{min-height:48px;display:flex;align-items:center;gap:10px;margin-top:auto;padding:10px;border:1px solid rgba(255,255,255,.05);border-radius:14px;background:#10131a;font-size:12px}.owner>i{width:34px;height:34px;display:grid;place-items:center;border-radius:50%;background:#17314a;color:#9bd9ff;font-style:normal;font-weight:800}
  @media(max-width:1100px){.admin-sidebar{padding-inline:10px}.brand span,.nav-group h2,.nav-group button span,.owner span{display:none}.brand,.nav-group button,.owner{justify-content:center;padding-inline:0}.admin-sidebar nav{gap:8px}.nav-group{gap:3px}}
  @media(max-width:560px){.admin-sidebar{position:fixed;z-index:10;top:auto;bottom:calc(10px + env(safe-area-inset-bottom,0px));left:50%;width:calc(100% - 24px);max-width:480px;height:64px;display:block;padding:7px 8px;border:1px solid rgba(162,207,244,.1);border-radius:22px;transform:translateX(-50%);box-shadow:0 18px 46px rgba(0,0,0,.48);overflow:hidden}.brand,.owner,.nav-group h2{display:none}.admin-sidebar nav{height:48px;display:flex;gap:4px;margin:0;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x proximity}.nav-group{display:contents}.nav-group button{box-sizing:border-box;flex:0 0 48px;width:48px;height:48px;min-height:48px;justify-content:center;padding:0;border-radius:16px;scroll-snap-align:start}}
</style>
