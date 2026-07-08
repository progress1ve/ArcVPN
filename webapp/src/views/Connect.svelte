<script>
  import { status, loadStatus } from '../lib/data.js'
  import { openExternal, haptic } from '../lib/telegram.js'
  import { copyText } from '../lib/ui.js'
  import Button from '../components/Button.svelte'
  import Icon from '../components/Icon.svelte'
  import DeviceIcon from '../components/DeviceIcon.svelte'

  loadStatus()

  // Устройства → ссылка на установку клиента Happ. Десктоп/ТВ делят клиент.
  const STORE = {
    ios: 'https://apps.apple.com/app/happ-proxy-utility/id6504287215',
    android: 'https://play.google.com/store/apps/details?id=com.happproxy',
    desktop: 'https://happ.su/',
  }
  const DEVICES = [
    { id: 'iphone', label: 'iPhone / iPad', icon: 'apple', store: 'ios' },
    { id: 'android', label: 'Android', icon: 'android', store: 'android' },
    { id: 'windows', label: 'Windows', icon: 'windows', store: 'desktop' },
  ]
  let device = 'iphone'
  let stage = 'device' // device | guide
  $: current = DEVICES.find((d) => d.id === device)

  $: keys = $status.data?.keys ?? []
  $: subKey =
    keys.find((k) => k.is_active && k.has_sub) || keys.find((k) => k.has_sub) || null
  $: subUrl = subKey?.sub_url || ''
  $: importUrl = subKey?.import_url || ''
  // Прямой happ:// deeplink — openExternal открывает в системном браузере,
  // где Happ перехватывает свой протокол. В TG WebView happ:// не работает,
  // но openExternal выходит из WebView -> срабатывает.
  $: happLink = (subUrl ? 'happ://add/' + subUrl : importUrl)

  function toGuide() {
    stage = 'guide'
    haptic('light')
  }
  function toDevice() {
    stage = 'device'
    haptic('light')
  }
</script>

<section class="view" class:centered={stage === 'device'}>
  <header class="head">
    {#if stage === 'guide'}
      <button class="back" on:click={toDevice}>
        <Icon name="chevron" size={18} strokeWidth={2.4} /> Назад
      </button>
    {/if}
    <h1 class="display">{stage === 'device' ? 'Выберите устройство' : current.label}</h1>
    <p class="muted">
      {stage === 'device'
        ? 'На какое устройство подключаем VPN?'
        : 'Установите Happ и импортируйте подписку.'}
    </p>
  </header>

  <!-- Индикатор шага -->
  <div class="steps" aria-hidden="true">
    <span class="dot" class:done={stage === 'guide'} class:active={stage === 'device'}>1</span>
    <span class="rail"><i class:full={stage === 'guide'}></i></span>
    <span class="dot" class:active={stage === 'guide'}>2</span>
  </div>

  {#if stage === 'device'}
    <div class="grid">
      {#each DEVICES as d}
        <button class="dev" class:on={d.id === device} on:click={() => (device = d.id)}>
          {#if d.id === device}<span class="pick"><Icon name="check" size={13} strokeWidth={3} /></span>{/if}
          <span class="dev-tile"><DeviceIcon name={d.icon} size={26} /></span>
          <span class="dev-label">{d.label}</span>
        </button>
      {/each}
    </div>

    <div class="spacer"></div>
    <Button variant="primary" on:click={toGuide}>
      Продолжить <Icon name="chevron" size={18} strokeWidth={2.4} />
    </Button>
  {:else if !subKey}
    <div class="panel pad">
      <p class="muted">Активной подписки нет — оформите её на главной, и здесь появится импорт для {current.label}.</p>
    </div>
  {:else}
    <!-- Шаг 1: установка -->
    <div class="panel guide">
      <div class="g-head">
        <span class="g-n mono">1</span>
        <div class="g-text">
          <span class="g-title">Установите Happ</span>
          <span class="muted small">Бесплатный клиент для {current.label} из официального магазина.</span>
        </div>
      </div>
      <Button variant="ghost" on:click={() => openExternal(STORE[current.store])}>
        <Icon name="upright" size={16} /> Скачать Happ
      </Button>
    </div>

    <!-- Шаг 2: импорт -->
    <div class="panel guide">
      <div class="g-head">
        <span class="g-n mono">2</span>
        <div class="g-text">
          <span class="g-title">Импортируйте подписку</span>
          <span class="muted small">Кнопка откроет Happ и добавит профиль. Не сработало — скопируйте ссылку.</span>
        </div>
      </div>
      <Button on:click={() => openExternal(happLink)}><Icon name="connect" size={18} /> Импортировать в Happ</Button>
      <Button variant="subtle" on:click={() => copyText(subUrl, 'Ссылка подписки скопирована')}>
        <Icon name="copy" size={17} /> Скопировать подписку
      </Button>
    </div>

    <div class="panel hintbox">
      <span class="hint-ico"><Icon name="check" size={16} strokeWidth={2.6} /></span>
      <p class="muted small">Готово — в Happ нажмите кнопку подключения и разрешите конфигурацию VPN.</p>
    </div>
  {/if}
</section>

<style>
  .view {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  /* Этап выбора устройства — контент по центру свободной высоты */
  .view.centered {
    min-height: calc(100dvh - var(--safe-top) - var(--safe-bottom) - 150px);
    justify-content: center;
  }
  .head {
    position: relative;
    text-align: center;
    margin-bottom: 2px;
  }
  .view:not(.centered) .head {
    text-align: left;
  }
  .head h1 {
    font-size: 25px;
    font-weight: 800;
    margin-bottom: 4px;
  }
  .head p {
    font-size: 13.5px;
  }
  .back {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    color: var(--muted);
    font-size: 13.5px;
    font-weight: 600;
    margin-bottom: 8px;
    margin-left: -4px;
  }
  .back :global(svg) {
    transform: rotate(180deg);
  }
  .back:active {
    color: var(--text);
  }
  .small {
    font-size: 12.5px;
  }

  /* Индикатор шага */
  .steps {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 6px 4px;
  }
  .dot {
    flex: none;
    width: 28px;
    height: 28px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    color: var(--faint);
    background: var(--surface-2);
    border: 1px solid var(--border);
  }
  .dot.active {
    color: var(--brand-ink);
    background: var(--brand);
    border-color: var(--brand);
  }
  .dot.done {
    color: var(--brand);
    background: var(--brand-soft);
    border-color: var(--brand-line);
  }
  .rail {
    flex: 1;
    height: 2px;
    border-radius: 2px;
    background: var(--border);
    overflow: hidden;
  }
  .rail i {
    display: block;
    height: 100%;
    width: 0;
    background: var(--brand);
    transition: width 0.35s ease;
  }
  .rail i.full {
    width: 100%;
  }

  /* Сетка устройств */
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;
  }
  .dev {
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--panel-top);
    padding: 20px 8px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    transition:
      border-color 0.16s ease,
      background 0.16s ease,
      transform 0.12s ease;
  }
  .dev:active {
    transform: scale(0.97);
  }
  .dev.on {
    border-color: var(--brand);
    background: color-mix(in srgb, var(--brand-soft) 45%, var(--surface));
  }
  .dev-tile {
    width: 52px;
    height: 52px;
    border-radius: 15px;
    display: grid;
    place-items: center;
    color: var(--muted);
    background: var(--surface-2);
    border: 1px solid var(--border);
    transition:
      color 0.16s ease,
      background 0.16s ease,
      border-color 0.16s ease;
  }
  .dev.on .dev-tile {
    color: var(--brand);
    background: var(--brand-soft);
    border-color: var(--brand-line);
  }
  .dev-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }
  .pick {
    position: absolute;
    top: 9px;
    right: 9px;
    width: 19px;
    height: 19px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--brand);
    color: var(--brand-ink);
  }
  .spacer {
    height: 4px;
  }

  /* Инструкция */
  .pad {
    padding: 18px;
  }
  .guide {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .g-head {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .g-n {
    flex: none;
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: var(--brand-soft);
    color: var(--brand);
    font-size: 14px;
    font-weight: 700;
  }
  .g-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .g-title {
    font-size: 15px;
    font-weight: 700;
  }
  .hintbox {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 13px 15px;
  }
  .hint-ico {
    flex: none;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: var(--signal);
    background: var(--signal-soft);
  }
  .hintbox p {
    margin: 0;
  }
</style>
