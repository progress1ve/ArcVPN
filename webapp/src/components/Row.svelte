<script>
  import Icon from './Icon.svelte'
  import { haptic } from '../lib/telegram.js'
  export let icon = ''
  export let title = ''
  export let value = ''
  export let chevron = false
  export let action = null // функция при тапе; если задана — строка кликабельна
</script>

<svelte:element
  this={action ? 'button' : 'div'}
  class="row"
  class:tappable={!!action}
  on:click={() => {
    if (action) {
      haptic('light')
      action()
    }
  }}
>
  {#if icon}
    <span class="ico"><Icon name={icon} size={19} /></span>
  {/if}
  <span class="title">{title}</span>
  {#if value !== ''}
    <span class="value tnum">{value}</span>
  {/if}
  {#if chevron}
    <span class="chev"><Icon name="chevron" size={18} /></span>
  {/if}
</svelte:element>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: 13px;
    width: 100%;
    padding: 14px 16px;
    text-align: left;
    color: var(--text);
  }
  .row.tappable:active {
    background: var(--tap);
  }
  .ico {
    color: var(--muted);
    display: inline-flex;
    flex: none;
  }
  .title {
    font-size: 15px;
    flex: 1;
    min-width: 0;
  }
  .value {
    font-size: 15px;
    color: var(--muted);
    font-weight: 500;
    text-align: right;
  }
  .chev {
    color: var(--faint);
    display: inline-flex;
    margin-left: -4px;
    flex: none;
  }
</style>
