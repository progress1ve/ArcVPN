<script>
  import { onMount } from 'svelte'
  import { createAdminBackup, fetchAdminBackups } from '../../lib/api.js'
  export let canCreate = true
  let backups=[];let loading=true;let creating=false;let error='';let notice=''
  const size=bytes=>Number(bytes)>1024*1024?`${(Number(bytes)/1024/1024).toFixed(1)} МБ`:`${Math.ceil(Number(bytes||0)/1024)} КБ`
  const stamp=value=>value?new Date(value).toLocaleString('ru-RU'):'—'
  async function load({preserveNotice=false}={}){loading=true;error='';if(!preserveNotice)notice='';try{backups=(await fetchAdminBackups()).backups||[]}catch(e){error=`Не удалось прочитать список копий: ${e.reason||e.message}`}finally{loading=false}}
  async function create(){if(creating||!canCreate)return;creating=true;error='';notice='';try{backups=(await createAdminBackup()).backups||[];notice='Снимок создан. При создании сервер выполнил SQLite quick_check.'}catch(e){error=`Не удалось создать снимок: ${e.reason||e.message}`}finally{creating=false}}
  onMount(load)
</script>

<section class="page">
  <header><div><span>ВОССТАНОВЛЕНИЕ</span><h2>Резервные копии</h2><p>Локальные SQLite-снимки основной базы ArcVPN. Список подтверждает наличие файлов, а не готовность процедуры восстановления.</p></div><button on:click={create} disabled={creating||!canCreate}>{creating?'Создаём…':'Создать снимок'}</button></header>
  {#if error}<div class="state error" role="alert"><span>{error}</span><button on:click={()=>load()} disabled={loading}>Повторить</button></div>{/if}
  {#if notice}<p class="notice" role="status">{notice}</p>{/if}
  <div class="summary"><article><small>СОХРАНЕНО</small><b>{backups.length}</b></article><article><small>ПОСЛЕДНИЙ СНИМОК</small><b>{backups[0]?stamp(backups[0].created_at):'Ещё не создан'}</b></article><article><small>ПРИ СОЗДАНИИ</small><b>SQLite quick_check</b></article></div>
  <section class="list" aria-busy={loading}><header><div><h3>История снимков</h3><p>До 50 последних локальных файлов.</p></div><button on:click={()=>load()} disabled={loading||creating}>{loading?'Обновляем…':'Обновить'}</button></header>{#if loading&&!backups.length}<p role="status">Загружаем список снимков…</p>{:else if !error&&!backups.length}<p>Снимков пока нет.</p>{:else}{#each backups as backup}<article><span><b>{backup.name}</b><small>{stamp(backup.created_at)}</small></span><em>{size(backup.size_bytes)}</em><strong>Создан</strong></article>{/each}{/if}</section>
</section>

<style>
.page{display:grid;gap:18px;min-width:0}.page>header,.list>header{display:flex;align-items:flex-end;justify-content:space-between;gap:18px}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 5px;font-size:30px}.page p{margin:0;color:#7890a5;line-height:1.45}.page button{border:1px solid rgba(155,217,255,.16);border-radius:15px;padding:12px 17px;background:#14283a;color:#bde7ff;font-weight:800;white-space:nowrap}.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.summary article,.list{border:1px solid rgba(155,217,255,.1);border-radius:22px;background:linear-gradient(145deg,#101b29,#0a121d)}.summary article{padding:21px;min-width:0}.summary small{color:#7890a5}.summary b{display:block;margin-top:12px;font-size:20px;overflow-wrap:anywhere}.list{padding:22px}.list h3{margin:0 0 4px}.list>header{margin-bottom:15px}.list>article{display:flex;align-items:center;gap:14px;padding:15px 3px;border-top:1px solid rgba(155,217,255,.07)}.list span{display:flex;min-width:0;flex:1;flex-direction:column;gap:4px}.list span b{overflow-wrap:anywhere}.list small{color:#7890a5}.list em{color:#9db2c4;font-style:normal;white-space:nowrap}.list strong{padding:7px 10px;border-radius:12px;background:rgba(155,217,255,.08);color:#9bd9ff;font-size:10px}.state,.notice{padding:14px;border-radius:13px;background:#14283a;color:#bde7ff}.state{display:flex;align-items:center;justify-content:space-between;gap:12px}.state.error{background:rgba(150,54,65,.15);color:#ffb1b6}button:focus-visible{outline:2px solid #9bd9ff;outline-offset:2px}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:800px){.summary{grid-template-columns:1fr}}@media(max-width:520px){.page h2{font-size:25px}.page>header,.list>header{align-items:flex-start;flex-direction:column}.page>header>button,.list>header>button{width:100%}.list{padding:18px}.list>article{display:grid;grid-template-columns:minmax(0,1fr) auto}.list>article>strong{grid-column:1/-1;justify-self:start}.summary b{font-size:18px}}
</style>
