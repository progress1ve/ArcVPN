<script>
  export let size = 34
</script>

<span class="mark" style={`--mark-size:${size}px`} aria-label="ArcVPN">
  <span class="piece tl"></span><span class="piece tr"></span>
  <span class="piece bl"></span><span class="piece br"></span>
</span>

<style>
  .mark { position: relative; display: inline-block; width: var(--mark-size); height: var(--mark-size); color: currentColor; }
  .piece { position: absolute; width: 45%; height: 45%; background: currentColor; }
  .tl { top: 3%; left: 3%; border-radius: 32% 10% 48% 10%; }
  .tr { top: 3%; right: 3%; border-radius: 10% 32% 10% 48%; }
  .bl { bottom: 3%; left: 3%; border-radius: 10% 48% 10% 32%; }
  .br { right: 3%; bottom: 3%; border-radius: 48% 10% 32% 10%; }
  .mark::after { content: ''; position: absolute; z-index: 2; top: 41%; left: 27%; width: 46%; height: 18%; border-radius: 999px; background: var(--preview-mark-cut, #060a12); }
</style>
