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
  .page-header{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid rgba(255,255,255,.055)}.page-header>div:first-child>span{display:none}h1{margin:0;font-size:30px;line-height:1.1;letter-spacing:-.035em}.tools{display:flex;align-items:center;gap:10px}.tools p{display:flex;align-items:center;gap:8px;margin:0;color:#7890a5;font-size:11px;font-weight:700}.tools p i{width:7px;height:7px;border-radius:50%;background:#61d8a5;box-shadow:0 0 0 5px rgba(97,216,165,.07)}.tools p.stale{max-width:420px;color:#ffc57d}.tools p.stale i{background:#ffc57d}.tools button{min-height:40px;display:flex;align-items:center;gap:8px;padding:0 15px;border:1px solid rgba(162,207,244,.1);border-radius:11px;background:#111720;color:#bcd0e2;font-weight:750;cursor:pointer}.tools button:disabled{cursor:not-allowed;opacity:.48}.tools button:focus-visible{outline:3px solid #9bd9ff;outline-offset:2px}
  @media(max-width:560px){.page-header{align-items:flex-start}.tools p{display:none}.tools button{width:42px;padding:0;justify-content:center;font-size:0}}
</style>
