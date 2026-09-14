<script>
  import ArcIcon from '../ArcIcon.svelte'
  export let groups = []
  export let active = 'overview'
  export let roleLabel = ['Администратор', 'Ограниченный доступ']
  export let onNavigate = () => {}
</script>

<aside class="admin-sidebar">
  <a class="brand" href="/admin" on:click|preventDefault={() => onNavigate('overview')}>
    <span class="brand-icon"><img src="/app/arc-logo-new.webp" alt="" /></span>
    <span>ArcVPN<small>Admin panel</small></span>
  </a>
  <nav aria-label="Разделы админ-панели">
    {#each groups as group}
      <section class="nav-group" aria-label={group.label}>
        <h2>{group.label}</h2>
        {#each group.items as item}
          <button class:active={active === item.id} aria-current={active === item.id ? 'page' : undefined} aria-label={item.label} on:click={() => onNavigate(item.id)} title={item.label}>
            <ArcIcon name={item.icon} size={18} weight="duotone" /><span>{item.label}</span>
          </button>
        {/each}
      </section>
    {/each}
  </nav>
  <div class="owner"><i>{roleLabel[0][0]}</i><span>{roleLabel[0]}<small>{roleLabel[1]}</small></span></div>
</aside>

<style>
  .admin-sidebar{position:sticky;top:0;box-sizing:border-box;height:100vh;display:flex;flex-direction:column;padding:16px 12px;border-right:1px solid #2b384b;background:#101827;color:#eef2f6;font-family:Inter,system-ui,sans-serif}
  .brand{min-height:52px;display:flex;align-items:center;gap:11px;padding:0 10px 14px;border-bottom:1px solid #202630;color:#f5f7fa;text-decoration:none;font-size:19px;font-weight:600;letter-spacing:-.02em}.brand-icon{width:32px;height:32px;display:grid;place-items:center;border:1px solid #252d38;border-radius:10px;background:#151b23}.brand img{width:22px}.brand>span:last-child,.owner span{display:flex;flex-direction:column}.brand small,.owner small{margin-top:2px;color:#9aaac0;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:none}
  nav{min-height:0;display:grid;align-content:start;gap:16px;margin-top:20px;overflow-y:auto;scrollbar-width:none}.nav-group{display:grid;gap:2px}.nav-group h2{margin:0 10px 4px;color:#9aaac0;font-size:12px;font-weight:700;letter-spacing:.09em;text-transform:uppercase}.nav-group button{box-sizing:border-box;width:100%;min-height:44px;display:flex;align-items:center;gap:11px;padding:0 10px;border:1px solid transparent;border-radius:9px;background:transparent;color:#b0bed1;font-size:14px;font-weight:500;text-align:left;cursor:pointer;transition:background .15s,color .15s,border-color .15s}.nav-group button:hover{border-color:#242c36;background:#141a22;color:#dfe6ed}.nav-group button.active{border-color:#29445a;background:#142536;color:#72b9e8;box-shadow:none}.nav-group button:focus-visible{outline:2px solid #54a9eb;outline-offset:2px}
  .owner{min-height:42px;display:flex;align-items:center;gap:9px;margin-top:auto;padding:8px;border-top:1px solid #202630;color:#cbd3dc;font-size:14px}.owner>i{width:30px;height:30px;display:grid;place-items:center;border-radius:9px;background:#182b3b;color:#72b9e8;font-style:normal;font-weight:750}
  @media(max-width:1100px){.admin-sidebar{padding-inline:8px}.brand>span:last-child,.nav-group h2,.nav-group button span,.owner span{display:none}.brand,.nav-group button,.owner{justify-content:center;padding-inline:0}.brand-icon{border:0;background:transparent}.admin-sidebar nav{gap:6px}.nav-group{gap:2px}}
  @media(max-width:560px){.admin-sidebar{position:fixed;z-index:10;top:auto;bottom:calc(8px + env(safe-area-inset-bottom,0px));left:50%;width:calc(100% - 20px);max-width:480px;height:58px;display:block;padding:6px;border:1px solid #29313d;border-radius:14px;transform:translateX(-50%);box-shadow:0 16px 42px rgba(0,0,0,.55);overflow:hidden}.brand,.owner,.nav-group h2{display:none}.admin-sidebar nav{height:44px;display:flex;gap:3px;margin:0;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x proximity}.nav-group{display:contents}.nav-group button{flex:0 0 44px;width:44px;height:44px;min-height:44px;justify-content:center;padding:0;border-radius:9px;scroll-snap-align:start}}
</style>
