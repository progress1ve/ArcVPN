<script>
  import { onMount } from 'svelte'
  import { createAdminBackup, fetchAdminBackups } from '../../lib/api.js'
  let backups = [], loading = true, creating = false, error = ''
  const size = (bytes) => bytes > 1024*1024 ? `${(bytes/1024/1024).toFixed(1)} МБ` : `${Math.ceil(bytes/1024)} КБ`
  async function load(){ loading=true; error=''; try{ backups=(await fetchAdminBackups()).backups||[] }catch(e){error='Не удалось прочитать резервные копии'}finally{loading=false} }
  async function create(){ if(creating)return; creating=true; error=''; try{ backups=(await createAdminBackup()).backups||[] }catch(e){error='Не удалось создать резервную копию'}finally{creating=false} }
  onMount(load)
</script>
<section class="page"><header><div><span>ВОССТАНОВЛЕНИЕ</span><h2>Резервные копии</h2><p>Проверенные SQLite-снимки основной базы ArcVPN.</p></div><button on:click={create} disabled={creating}>{creating?'Создаём…':'Создать копию'}</button></header>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="summary"><article><small>СОХРАНЕНО</small><b>{backups.length}</b></article><article><small>ПОСЛЕДНЯЯ КОПИЯ</small><b>{backups[0] ? new Date(backups[0].created_at).toLocaleString('ru-RU') : 'Ещё не создана'}</b></article><article><small>ПРОВЕРКА</small><b>PRAGMA quick_check</b></article></div>
  <section class="list"><header><h3>История копий</h3><button on:click={load}>Обновить</button></header>{#if loading}<p>Загружаем…</p>{:else if !backups.length}<p>Резервных копий пока нет.</p>{:else}{#each backups as backup}<article><span><b>{backup.name}</b><small>{new Date(backup.created_at).toLocaleString('ru-RU')}</small></span><em>{size(backup.size_bytes)}</em><strong>Проверена</strong></article>{/each}{/if}</section>
</section>
<style>.page{display:grid;gap:18px}.page>header,.list>header{display:flex;align-items:flex-end;justify-content:space-between}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 5px;font-size:30px}.page p{margin:0;color:#7890a5}.page button{border:1px solid rgba(155,217,255,.16);border-radius:15px;padding:12px 17px;background:#14283a;color:#bde7ff;font-weight:800}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.summary article,.list{border:1px solid rgba(155,217,255,.1);border-radius:22px;background:linear-gradient(145deg,#101b29,#0a121d)}.summary article{padding:21px}.summary small{color:#7890a5}.summary b{display:block;margin-top:12px;font-size:20px}.list{padding:22px}.list h3{margin:0 0 15px}.list>article{display:flex;align-items:center;gap:14px;padding:15px 3px;border-top:1px solid rgba(155,217,255,.07)}.list span{display:flex;flex:1;flex-direction:column;gap:4px}.list small{color:#7890a5}.list em{color:#9db2c4;font-style:normal}.list strong{padding:7px 10px;border-radius:12px;background:rgba(97,216,165,.09);color:#78e1b4;font-size:10px}.error{color:#ff9c9c!important}@media(max-width:800px){.summary{grid-template-columns:1fr}}</style>
