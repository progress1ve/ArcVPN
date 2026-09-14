<script>
  import ArcIcon from '../ArcIcon.svelte'
  export let title = 'ArcVPN'
  export let context = ''
  export let stale = false
  export let disabled = false
  export let refreshLabel = 'Проверить'
  export let onRefresh = () => {}
</script>

<header class="page-header">
  <div><span>{context}</span><h1>{title}</h1></div>
  <div class="tools"><p class:stale aria-live="polite"><i></i>{context}</p><button disabled={disabled} aria-label={refreshLabel} on:click={onRefresh}><ArcIcon name="pulse" size={17} />{refreshLabel}</button></div>
</header>

<style>
  .page-header{min-height:45px;display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:24px;padding-bottom:13px;border-bottom:1px solid #2b384b}.page-header>div:first-child>span{display:none}h1{margin:0;color:#f0f3f6;font-size:28px;font-weight:600;line-height:1.15;letter-spacing:-.025em}.tools{display:flex;align-items:center;gap:10px}.tools p{display:flex;align-items:center;gap:7px;margin:0;color:#a6b4c8;font-size:13px;font-weight:600}.tools p i{width:6px;height:6px;border-radius:50%;background:#55c894}.tools p.stale{max-width:420px;color:#dca35c}.tools p.stale i{background:#dca35c}.tools button{min-height:42px;display:flex;align-items:center;gap:7px;padding:0 16px;border:1px solid #28313c;border-radius:8px;background:#151b23;color:#aeb8c5;font-size:13px;font-weight:650;cursor:pointer}.tools button:hover{border-color:#344250;background:#19212a;color:#e5ebf1}.tools button:disabled{cursor:not-allowed;opacity:.48}.tools button:focus-visible{outline:2px solid #54a9eb;outline-offset:2px}
  @media(max-width:560px){.page-header{align-items:flex-start}.tools p{display:none}.tools button{width:42px;padding:0;justify-content:center;font-size:0}}
</style>
