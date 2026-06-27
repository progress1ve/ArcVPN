<script>
  import { haptic } from '../lib/telegram.js'
  export let variant = 'primary' // primary | ghost | subtle | signal
  export let full = true
  export let disabled = false
  export let href = null
</script>

{#if href}
  <a
    class="btn {variant}"
    class:full
    {href}
    rel="noopener noreferrer"
    on:click={() => haptic('light')}
  >
    <slot />
  </a>
{:else}
  <button
    class="btn {variant}"
    class:full
    {disabled}
    on:click={() => haptic('light')}
    on:click
  >
    <slot />
  </button>
{/if}

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    padding: 14px 18px;
    border-radius: var(--radius-sm);
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
    transition:
      transform 0.12s ease,
      background 0.15s ease,
      border-color 0.15s ease;
    user-select: none;
  }
  .btn.full {
    width: 100%;
  }
  .btn:active {
    transform: scale(0.985);
  }
  .btn[disabled] {
    opacity: 0.45;
    pointer-events: none;
  }
  .primary {
    background: var(--brand);
    color: var(--brand-ink);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
  }
  .primary:active {
    background: var(--brand-press);
  }
  .signal {
    background: var(--signal);
    color: #06231a;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
  }
  .ghost {
    background: var(--glass-bg);
    color: var(--text);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(16px) saturate(135%);
    -webkit-backdrop-filter: blur(16px) saturate(135%);
    box-shadow: var(--glass-hi);
  }
  .ghost:active {
    border-color: var(--brand-line);
  }
  .subtle {
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--border);
  }
  .subtle:active {
    color: var(--text);
  }
</style>
