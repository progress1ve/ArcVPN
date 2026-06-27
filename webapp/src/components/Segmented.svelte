<script>
  import { haptic } from '../lib/telegram.js'
  export let options = [] // [{value, label}]
  export let value

  function pick(v) {
    if (v === value) return
    value = v
    haptic('light')
  }
</script>

<div class="seg" role="tablist">
  {#each options as opt}
    <button
      role="tab"
      class="opt"
      class:active={opt.value === value}
      aria-selected={opt.value === value}
      on:click={() => pick(opt.value)}
    >
      {opt.label}
    </button>
  {/each}
</div>

<style>
  .seg {
    display: flex;
    gap: 4px;
    padding: 4px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }
  .opt {
    flex: 1;
    padding: 9px 8px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    transition:
      background 0.15s ease,
      color 0.15s ease;
  }
  .opt.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
  }
</style>
