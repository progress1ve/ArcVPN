<script>
  import { toastMsg } from '../lib/ui.js'
</script>

{#if $toastMsg}
  <div class="toast" role="status">{$toastMsg}</div>
{/if}

<style>
  .toast {
    position: fixed;
    left: 50%;
    bottom: calc(var(--tabbar-h) + var(--safe-bottom) + 30px);
    transform: translateX(-50%);
    max-width: calc(var(--maxw) - 40px);
    background: var(--text);
    color: var(--bg);
    padding: 11px 18px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    z-index: 50;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    animation: rise 0.22s ease;
  }
  @keyframes rise {
    from {
      opacity: 0;
      transform: translate(-50%, 8px);
    }
    to {
      opacity: 1;
      transform: translate(-50%, 0);
    }
  }
</style>
