<script>
  import { onMount } from 'svelte'
  import { fetchAdminCatalog, saveAdminCatalog } from '../../lib/api.js'
  let profiles = []; let loading = true; let saving = false; let message = ''
  onMount(load)
  async function load(){ loading=true; try{profiles=(await fetchAdminCatalog()).profiles||[]}finally{loading=false} }
  function move(index, delta){ const target=index+delta;if(target<0||target>=profiles.length)return; const copy=[...profiles];[copy[index],copy[target]]=[copy[target],copy[index]];profiles=copy }
  async function save(){ saving=true;message='';try{profiles=(await saveAdminCatalog(profiles)).profiles||profiles;message='Каталог опубликован'}catch(e){message='Не удалось сохранить каталог'}finally{saving=false} }
</script>
<section class="page">
  <header><span>МАРШРУТ ПОДПИСКИ</span><h2>Каталог подключений</h2><p>Меняйте подпись и порядок существующих Remnawave Hosts. Флаг страны восстанавливается автоматически; редактор не создаёт inbound и не меняет UUID.</p></header>
  {#if loading}<p>Загружаем каталог…</p>{:else}
    <div class="route">{#each profiles as profile,index}<article class:disabled={!profile.enabled}>
      <b>{String(index+1).padStart(2,'0')}</b><div><input bind:value={profile.display_name} maxlength="120" aria-label="Название профиля"/><small>{profile.protocol_label||'Протокол определяется Remnawave'}</small></div>
      <label><input type="checkbox" bind:checked={profile.enabled}/><span>{profile.enabled?'В подписке':'Скрыт'}</span></label>
      <nav><button on:click={()=>move(index,-1)} disabled={index===0} aria-label="Выше">↑</button><button on:click={()=>move(index,1)} disabled={index===profiles.length-1} aria-label="Ниже">↓</button></nav>
    </article>{/each}</div>
    <footer><p>{message}</p><button on:click={save} disabled={saving}>{saving?'Сохраняем…':'Опубликовать порядок'}</button></footer>
  {/if}
</section>
<style>.page{display:grid;gap:20px;max-width:1050px}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 6px;font-size:30px}.page p{margin:0;color:#7890a5}.route{display:grid;gap:8px}.route article{display:grid;grid-template-columns:48px minmax(0,1fr) 120px 82px;align-items:center;gap:14px;padding:13px 14px;border:1px solid rgba(155,217,255,.1);border-radius:17px;background:#10141c}.route article.disabled{opacity:.55}.route article>b{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#14283a;color:#9bd9ff;font-family:monospace}.route article>div{display:grid;gap:4px}.route input[type=text],.route article>div input{border:0;border-bottom:1px solid transparent;background:transparent;color:#edf7ff;font:700 14px inherit;outline:0}.route article>div input:focus{border-color:#80c9f4}.route small{color:#667b8d;font-size:10px}.route label{display:flex;align-items:center;gap:7px;color:#8da1b2;font-size:11px}.route nav{display:flex;gap:5px}.route nav button{width:36px;height:36px;border:0;border-radius:11px;background:#172535;color:#bde7ff}.route nav button:disabled{opacity:.25}footer{display:flex;align-items:center;justify-content:space-between}footer button{min-height:46px;border:0;border-radius:14px;padding:0 20px;background:#9bd9ff;color:#07111d;font-weight:900}@media(max-width:700px){.route article{grid-template-columns:40px 1fr 72px}.route label{display:none}.route nav{grid-column:2/4}}</style>
