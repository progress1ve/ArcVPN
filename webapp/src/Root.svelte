<script>
  import { onMount } from 'svelte'

  let Page = null
  let loadError = false

  onMount(async () => {
    try {
      const isLanding = location.pathname === '/'
        || (import.meta.env.DEV && new URLSearchParams(location.search).has('landing'))
      const module = isLanding
        ? await import('./views/LandingPage.svelte')
        : await import('./App.svelte')
      Page = module.default
    } catch (error) {
      console.error(error)
      loadError = true
    }
  })
</script>

{#if Page}
  <svelte:component this={Page} />
{:else if loadError}
  <main class="boot-error">
    <b>ArcVPN временно не загрузился</b>
    <button on:click={() => location.reload()}>Повторить</button>
  </main>
{:else}
  <div class="boot" aria-label="Загружаем ArcVPN"><span></span></div>
{/if}

<style>
  .boot { min-height:100dvh; display:grid; place-items:center; background:#03070e; }
  .boot span { width:26px; height:26px; border:2px solid #18334d; border-top-color:#8ed8ff; border-radius:50%; animation:spin .8s linear infinite; }
  .boot-error { min-height:100dvh; display:grid; place-content:center; gap:18px; padding:24px; color:#f5f9ff; background:#03070e; text-align:center; }
  .boot-error button { min-height:48px; padding:0 20px; border:0; border-radius:999px; color:#06121d; background:#8ed8ff; font-weight:800; }
  @keyframes spin { to { transform:rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .boot span { animation:none; } }
</style>
