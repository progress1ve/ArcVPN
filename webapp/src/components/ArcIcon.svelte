<script>
  import Icon from '@iconify/svelte'
  import icons from '../lib/arc-icons.js'

  export let name = ''
  export let size = 22
  export let weight = 'regular'
  export let mirrored = false

  $: activeName = `${name}Active`
  $: glyph = weight !== 'regular' && icons[activeName] ? icons[activeName] : (icons[name] || icons.question)
</script>

<span class:mirrored class="arc-icon" aria-hidden="true">
  <Icon icon={glyph} width={size} height={size} />
</span>

<style>
  .arc-icon {
    display: inline-flex;
    flex: none;
    align-items: center;
    justify-content: center;
    line-height: 0;
  }
  .mirrored { transform: scaleX(-1); }
</style>
