<script>
  // Радиальный датчик-дуга — сигнатура бренда (Arc) и приборной айдентики.
  // 270° шкала с разрывом снизу. value: 0..1 — заполнение дуги.
  export let value = 1 // доля запаса
  export let color = 'var(--brand)'
  export let track = 'var(--surface-3)'
  export let size = 168

  const R = 50
  const C = 2 * Math.PI * R // 314.16
  const ARC = C * 0.75 // длина 270°-дуги

  $: v = Math.max(0, Math.min(1, value))
  $: fill = ARC * v
</script>

<div class="gauge" style="width:{size}px;height:{size}px">
  <svg viewBox="0 0 120 120" aria-hidden="true">
    <circle
      class="trk"
      cx="60"
      cy="60"
      r={R}
      stroke={track}
      stroke-dasharray="{ARC} {C}"
      transform="rotate(135 60 60)"
    />
    <circle
      class="val"
      cx="60"
      cy="60"
      r={R}
      stroke={color}
      stroke-dasharray="{fill} {C}"
      transform="rotate(135 60 60)"
    />
  </svg>
  <div class="center"><slot /></div>
</div>

<style>
  .gauge {
    position: relative;
    flex: none;
  }
  svg {
    width: 100%;
    height: 100%;
    display: block;
  }
  circle {
    fill: none;
    stroke-width: 8;
    stroke-linecap: round;
  }
  .val {
    transition: stroke-dasharray 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  }
  .center {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
</style>
