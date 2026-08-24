<script>
  import { onMount } from 'svelte'
  import { fetchAdminCatalog, saveAdminCatalog } from '../../lib/api.js'
  export let canManage = true
  let profiles = []
  let baselineProfiles = []
  let loading = true
  let saving = false
  let error = ''
  let message = ''
  const clone = (value) => JSON.parse(JSON.stringify(value))
  $: validationErrors = profiles.map((profile, index) => !String(profile.display_name || '').trim() ? `У профиля ${index + 1} нет названия` : '').filter(Boolean)
  $: dirty = JSON.stringify(profiles) !== JSON.stringify(baselineProfiles)
  $: canPublish = canManage && profiles.length > 0 && dirty && !saving && !validationErrors.length

  onMount(load)
  async function load() {
    loading = true
    error = ''
    message = ''
    try {
      const result = await fetchAdminCatalog()
      profiles = clone(result.profiles || [])
      baselineProfiles = clone(profiles)
    } catch (exception) {
      profiles = []
      baselineProfiles = []
      error = exception.reason || 'Не удалось загрузить каталог.'
    } finally { loading = false }
  }
  function move(index, delta) {
    const target = index + delta
    if (!canManage || saving || target < 0 || target >= profiles.length) return
    const copy = [...profiles]
    ;[copy[index], copy[target]] = [copy[target], copy[index]]
    profiles = copy
    message = ''
  }
  function reset() {
    if (!canManage || saving || !dirty) return
    profiles = clone(baselineProfiles)
    message = 'Локальные изменения сброшены.'
  }
  async function save() {
    if (!canPublish) return
    saving = true
    error = ''
    message = 'Публикуем каталог…'
    try {
      const result = await saveAdminCatalog(profiles.map((profile) => ({ ...profile, display_name: profile.display_name.trim() })))
      profiles = clone(result.profiles || profiles)
      baselineProfiles = clone(profiles)
      message = 'Каталог опубликован. Новые подписки получат этот порядок.'
    } catch (exception) {
      error = exception.reason || 'Не удалось сохранить каталог. Изменения оставлены в редакторе.'
      message = ''
    } finally { saving = false }
  }
</script>

<section class="page" aria-labelledby="catalog-title" aria-busy={loading || saving}>
  <header><span>МАРШРУТ ПОДПИСКИ</span><h2 id="catalog-title">Каталог подключений</h2><p>{canManage ? 'Меняйте подпись и порядок существующих Remnawave Hosts.' : 'Опубликованный порядок существующих Remnawave Hosts доступен только для чтения.'} Редактор не создаёт inbound и не меняет UUID.</p></header>
  {#if loading}<div class="state" role="status"><i></i><b>Загружаем каталог…</b><p>Получаем актуальный порядок из ArcVPN.</p></div>
  {:else if error && !profiles.length}<div class="state error" role="alert"><b>Каталог недоступен</b><p>{error}</p><button on:click={load}>Повторить</button></div>
  {:else if !profiles.length}<div class="state"><b>Каталог пуст</b><p>В Remnawave не найдены профили, которые можно безопасно редактировать.</p><button on:click={load}>Обновить</button></div>
  {:else}
    <div class="route">{#each profiles as profile,index (profile.source_name)}<article class:disabled={!profile.enabled}>
      <b>{String(index + 1).padStart(2, '0')}</b><div><label><span class="sr-only">Название профиля {index + 1}</span><input bind:value={profile.display_name} maxlength="120" disabled={saving || !canManage} class:invalid={!String(profile.display_name || '').trim()} aria-invalid={!String(profile.display_name || '').trim()}/></label><small>{profile.protocol_label || 'Протокол определяется Remnawave'}</small></div>
      <div class="toggles"><label><input type="checkbox" bind:checked={profile.enabled} disabled={saving || !canManage}/><span>{profile.enabled ? 'Отдельно' : 'Скрыт'}</span></label><label><input type="checkbox" bind:checked={profile.include_in_auto} disabled={saving || !canManage}/><span>В автовыборе</span></label></div>
      <nav aria-label={`Порядок профиля ${profile.display_name || index + 1}`}><button on:click={()=>move(index,-1)} disabled={!canManage || saving || index===0} aria-label="Переместить выше">↑</button><button on:click={()=>move(index,1)} disabled={!canManage || saving || index===profiles.length-1} aria-label="Переместить ниже">↓</button></nav>
    </article>{/each}</div>
    <div class="feedback" aria-live="polite">{#if validationErrors.length}<p class="validation" role="alert">{validationErrors[0]}</p>{:else if error}<p class="validation" role="alert">{error}</p>{:else if message}<p class:success={!dirty}>{message}</p>{:else if dirty}<p>Есть неопубликованные изменения.</p>{:else}<p>Каталог совпадает с опубликованной версией.</p>{/if}</div>
    {#if canManage}<footer><button class="reset" on:click={reset} disabled={!dirty || saving}>Сбросить изменения</button><button on:click={save} disabled={!canPublish}>{saving ? 'Публикуем…' : dirty ? 'Опубликовать порядок' : 'Изменений нет'}</button></footer>{/if}
  {/if}
</section>

<style>
.page{display:grid;min-width:0;max-width:1100px;gap:20px}.page>header span{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.15em}.page h2{margin:8px 0 6px;font-size:clamp(25px,3vw,30px)}.page p{margin:0;color:#7890a5}.route{display:grid;gap:8px}.route article{display:grid;grid-template-columns:48px minmax(0,1fr) 210px 82px;align-items:center;gap:14px;padding:13px 14px;border:1px solid rgba(155,217,255,.1);border-radius:17px;background:#10141c}.route article.disabled{opacity:.72}.route article>b{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#14283a;color:#9bd9ff;font-family:monospace}.route article>div{display:grid;min-width:0;gap:4px}.route article>div.toggles{display:flex;flex-wrap:wrap;gap:9px}.route article>div input{box-sizing:border-box;width:100%;border:0;border-bottom:1px solid transparent;background:transparent;color:#edf7ff;font:700 14px inherit;outline:0}.route article>div input.invalid{border-color:#ff8f8f}.route small{overflow:hidden;color:#667b8d;font-size:10px;text-overflow:ellipsis}.route label{display:flex;align-items:center;gap:6px;color:#8da1b2;font-size:10px}.route article>div>label{display:block}.route nav{display:flex;gap:5px}.route nav button{width:36px;height:36px;border:0;border-radius:11px;background:#172535;color:#bde7ff;cursor:pointer}.route nav button:disabled,.page button:disabled{cursor:not-allowed;opacity:.3}.state{display:grid;min-height:230px;place-content:center;justify-items:center;gap:7px;padding:24px;border:1px dashed #26394a;border-radius:20px;text-align:center}.state.error{border-color:#54303a}.state button{min-height:42px;margin-top:8px;padding:0 16px;border:1px solid #2a455c;border-radius:12px;background:#14283a;color:#bde7ff}.feedback{min-height:20px}.feedback .validation{color:#ff9ca7}.feedback .success{color:#75d8aa}footer{display:flex;align-items:center;justify-content:flex-end;gap:9px}footer button{min-height:46px;border:0;border-radius:14px;padding:0 20px;background:#9bd9ff;color:#07111d;font-weight:900;cursor:pointer}footer button.reset{border:1px solid #294056;background:#101b28;color:#91a9ba}.page button:focus-visible,.route input:focus-visible{outline:2px solid #9bd9ff;outline-offset:2px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
@media(max-width:760px){.route article{grid-template-columns:40px minmax(0,1fr) 72px}.route article>div.toggles{grid-column:2/4}.route nav{grid-column:2/4}.route article{align-items:start}}
@media(max-width:520px){.route article{grid-template-columns:36px minmax(0,1fr);gap:10px}.route article>div.toggles,.route nav{grid-column:2}.route nav{justify-content:flex-end}footer{align-items:stretch;flex-direction:column-reverse}footer button{width:100%}}
</style>
