<script>
  // Фирменный элемент: тонкая линия-маршрут «устройство → выходной узел».
  // Узел — 4-лучевая звезда (мотив логотипа ArcVPN). Линия прорисовывается
  // штрихом при появлении. Без свечения и заливок — только hairline.
  export let active = true
  $: stroke = active ? 'var(--accent)' : 'var(--faint)'
</script>

<svg class="route" viewBox="0 0 320 64" fill="none" preserveAspectRatio="none" aria-hidden="true">
  <!-- пунктирная «дорога» под маршрутом -->
  <path d="M14 50 C 110 50, 150 18, 306 14" stroke="var(--border-strong)" stroke-width="1.5" stroke-dasharray="2 6" stroke-linecap="round" />
  <!-- активный маршрут -->
  <path
    class="line"
    d="M14 50 C 110 50, 150 18, 306 14"
    stroke={stroke}
    stroke-width="2"
    stroke-linecap="round"
  />
  <!-- точка устройства -->
  <circle cx="14" cy="50" r="4" fill={stroke} />
  <circle cx="14" cy="50" r="8" stroke={stroke} stroke-width="1.5" opacity="0.35" />
  <!-- узел-звезда (выход) -->
  <g class="star" transform="translate(306 14)" fill={stroke}>
    <path d="M0 -9 C 1.6 -3, 3 -1.6, 9 0 C 3 1.6, 1.6 3, 0 9 C -1.6 3, -3 1.6, -9 0 C -3 -1.6, -1.6 -3, 0 -9 Z" />
  </g>
</svg>

<style>
  .route {
    width: 100%;
    height: 56px;
    display: block;
  }
  .line {
    stroke-dasharray: 340;
    stroke-dashoffset: 340;
    animation: draw 1.1s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }
  .star {
    opacity: 0;
    animation: fade 0.4s ease 0.85s forwards;
  }
  @keyframes draw {
    to {
      stroke-dashoffset: 0;
    }
  }
  @keyframes fade {
    to {
      opacity: 1;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .line {
      stroke-dashoffset: 0;
    }
    .star {
      opacity: 1;
    }
  }
</style>
