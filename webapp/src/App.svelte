<script>
  import { fly } from 'svelte/transition'
  import { cubicOut } from 'svelte/easing'
  import { theme } from './lib/theme.js'
  import { status } from './lib/data.js'
  import { openTelegram } from './lib/telegram.js'
  import TabBar from './components/TabBar.svelte'
  import Toast from './components/Toast.svelte'
  import Icon from './components/Icon.svelte'
  import Logo from './components/Logo.svelte'
  import Home from './views/Home.svelte'
  import Connect from './views/Connect.svelte'
  import Referral from './views/Referral.svelte'
  import Profile from './views/Profile.svelte'

  // тема применяется через подписку в theme.js; здесь просто держим store «живым»
  $: $theme

  $: supportUrl = $status.data?.links?.support_url || ''

  const known = ['home', 'connect', 'referral', 'profile']
  const fromHash = typeof location !== 'undefined' ? location.hash.slice(1) : ''
  let tab = known.includes(fromHash) ? fromHash : 'home'
</script>

<div class="shell">
  <!-- Фирменный «воздух»: один мягкий индиго-ореол сверху. Не иллюминация. -->
  <div class="ambient" aria-hidden="true"></div>

  <header class="brand">
    <div class="logo">
      <span class="logo-mark"><Logo size={27} /></span>
      <span class="word display">ArcVPN</span>
    </div>
    {#if supportUrl}
      <button class="support-pill" on:click={() => openTelegram(supportUrl)}>
        <Icon name="headset" size={15} strokeWidth={2} />
        <span>Поддержка</span>
      </button>
    {/if}
  </header>

  <main class="screen">
    {#key tab}
      <div class="view-anim" in:fly={{ y: 14, duration: 240, easing: cubicOut }}>
        {#if tab === 'home'}
          <Home goConnect={() => (tab = 'connect')} goReferral={() => (tab = 'referral')} />
        {:else if tab === 'connect'}
          <Connect />
        {:else if tab === 'referral'}
          <Referral goHome={() => (tab = 'home')} />
        {:else}
          <Profile />
        {/if}
      </div>
    {/key}
  </main>

  <TabBar bind:active={tab} />
  <Toast />
</div>

<style>
  .shell {
    position: relative;
    min-height: 100%;
    z-index: 0;
  }
  .ambient {
    position: fixed;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: var(--maxw);
    height: 360px;
    pointer-events: none;
    z-index: -1;
    background: radial-gradient(
      120% 80% at 50% -20%,
      color-mix(in srgb, var(--brand) 26%, transparent),
      transparent 60%
    );
    -webkit-mask-image: linear-gradient(180deg, #000 0%, transparent 100%);
    mask-image: linear-gradient(180deg, #000 0%, transparent 100%);
  }
  :global([data-theme='light']) .ambient {
    opacity: 0.5;
  }
  .brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: calc(var(--safe-top) + 14px) var(--pad) 12px;
    animation: drop-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }
  .logo-mark {
    display: inline-flex;
    color: var(--text);
  }
  .word {
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .support-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: none;
    padding: 7px 13px;
    border-radius: var(--radius-pill);
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    color: var(--muted);
    font-size: 13px;
    font-weight: 600;
    box-shadow: var(--glass-hi);
  }
  .support-pill:active {
    color: var(--text);
  }
  /* Анимация загрузки: .screen монтируется один раз → проигрывается на старте.
     Переходы между секциями делает in:fly на .view-anim (на каждой смене tab). */
  .screen {
    padding: 4px var(--pad) calc(var(--tabbar-h) + var(--safe-bottom) + 28px);
    animation: rise-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.05s both;
  }
  .view-anim {
    will-change: transform, opacity;
  }
  @keyframes drop-in {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
  }
  @keyframes rise-in {
    from {
      opacity: 0;
      transform: translateY(16px);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .brand,
    .screen {
      animation: none;
    }
  }
</style>
