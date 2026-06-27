<script>
  import Icon from './Icon.svelte'
  import { haptic } from '../lib/telegram.js'
  export let active = 'home'

  const tabs = [
    { id: 'home', icon: 'home', label: 'Главная' },
    { id: 'connect', icon: 'connect', label: 'Подключение' },
    { id: 'referral', icon: 'users', label: 'Друзья' },
    { id: 'profile', icon: 'user', label: 'Профиль' },
  ]

  function go(id) {
    if (id === active) return
    active = id
    haptic('light')
  }
</script>

<div class="dock">
  <nav class="tabbar">
    {#each tabs as t}
      <button
        class="tab"
        class:active={t.id === active}
        on:click={() => go(t.id)}
        aria-label={t.label}
      >
        <span class="ico"><Icon name={t.icon} size={21} strokeWidth={2} /></span>
        <span class="lbl">{t.label}</span>
      </button>
    {/each}
  </nav>
</div>

<style>
  .dock {
    position: fixed;
    left: 50%;
    bottom: calc(var(--safe-bottom) + 12px);
    transform: translateX(-50%);
    width: 100%;
    max-width: var(--maxw);
    padding: 0 var(--pad);
    z-index: 40;
    pointer-events: none;
  }
  .tabbar {
    pointer-events: auto;
    display: flex;
    gap: 4px;
    padding: 7px;
    background: color-mix(in srgb, var(--surface) 86%, transparent);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-pill);
    box-shadow: var(--shadow-float);
  }
  .tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 8px 4px 7px;
    border-radius: var(--radius-pill);
    color: var(--faint);
    font-size: 10px;
    font-weight: 600;
    transition:
      color 0.16s ease,
      background 0.16s ease;
  }
  .ico {
    display: inline-flex;
    transition: transform 0.16s ease;
  }
  .lbl {
    letter-spacing: 0.01em;
  }
  .tab.active {
    color: var(--brand);
    background: var(--brand-soft);
  }
  .tab.active .ico {
    transform: translateY(-1px);
  }
  .tab:not(.active):active {
    color: var(--muted);
  }
</style>
