<script>
  import { status, loadStatus } from '../lib/data.js'
  import { getUser, openTelegram } from '../lib/telegram.js'
  import { copyText } from '../lib/ui.js'
  import { theme, toggleTheme } from '../lib/theme.js'
  import {
    formatBytes,
    formatDate,
    daysLeft,
    daysWord,
    deviceWord,
  } from '../lib/format.js'
  import Icon from '../components/Icon.svelte'

  loadStatus()
  const user = getUser()

  $: keys = $status.data?.keys ?? []
  $: activeKeys = keys.filter((k) => k.is_active)
  $: primary = activeKeys[0] ?? keys[0] ?? null
  $: links = $status.data?.links ?? {}
  $: tgId = $status.data?.telegram_id ?? user?.id ?? null
  $: devices = activeKeys.reduce((n, k) => n + (k.online_devices || 0), 0)
  $: name = user ? [user.first_name, user.last_name].filter(Boolean).join(' ') : 'Профиль'
  $: photo = user?.photo_url || ''

  $: isActive = !!primary?.is_active
  $: tariffName = primary ? primary.display_name : 'Нет подписки'
  $: trafPct =
    primary && primary.traffic_limit
      ? Math.min(100, Math.round((primary.traffic_used / primary.traffic_limit) * 100))
      : 0
  $: traffic = primary?.traffic_limit
    ? `${formatBytes(primary.traffic_used)} / ${formatBytes(primary.traffic_limit)}`
    : primary
      ? 'Безлимит'
      : '—'
  $: expiry = primary
    ? isActive
      ? `${daysLeft(primary.expires_at_unix)} ${daysWord(daysLeft(primary.expires_at_unix))} · до ${formatDate(primary.expires_at_unix)}`
      : `истекла ${formatDate(primary.expires_at_unix)}`
    : '—'
</script>

<section class="view">
  <header class="phead">
    <h1 class="display">Профиль</h1>
  </header>

  <!-- Карточка пользователя -->
  <div class="panel user">
    {#if photo}
      <img class="ava" src={photo} alt="" />
    {:else}
      <span class="ava ava-txt">{(name || '?').charAt(0).toUpperCase()}</span>
    {/if}
    <div class="who">
      <span class="name">{name}</span>
      {#if user?.username}<span class="muted">@{user.username}</span>{/if}
    </div>
  </div>

  <!-- Аккаунт -->
  <div class="block-head"><span class="eyebrow">Аккаунт</span></div>
  <div class="panel rows">
    {#if tgId}
      <button class="row" on:click={() => copyText(String(tgId), 'ID скопирован')}>
        <span class="rt">ID</span>
        <span class="rv mono">{tgId}</span>
        <span class="rico"><Icon name="copy" size={15} /></span>
      </button>
    {/if}
    <div class="row">
      <span class="rt">Тариф</span>
      <span class="badge" class:on={isActive} class:off={!isActive}>{tariffName}</span>
    </div>
    <div class="row col">
      <div class="row-line">
        <span class="rt">Трафик</span>
        <span class="rv mono">{traffic}</span>
      </div>
      {#if primary?.traffic_limit}
        <div class="bar"><b style="width:{trafPct}%"></b></div>
      {/if}
    </div>
    <div class="row">
      <span class="rt">Подписка</span>
      <span class="rv" class:warn={primary && !isActive}>{expiry}</span>
    </div>
  </div>

  <!-- Устройства -->
  <div class="panel rows">
    <div class="row">
      <span class="lico"><Icon name="phone" size={18} /></span>
      <span class="rt grow">Устройства онлайн</span>
      <span class="rv mono">{devices} {deviceWord(devices)}</span>
    </div>
  </div>

  <!-- Ссылки -->
  <div class="block-head"><span class="eyebrow">Сервис</span></div>
  <div class="panel rows">
    {#if links.channel_url}
      <button class="row tap" on:click={() => openTelegram(links.channel_url)}>
        <span class="lico"><Icon name="channel" size={18} /></span>
        <span class="rt grow">Канал ArcVPN</span>
        <span class="rico"><Icon name="chevron" size={16} /></span>
      </button>
    {/if}
    {#if links.support_url}
      <button class="row tap" on:click={() => openTelegram(links.support_url)}>
        <span class="lico"><Icon name="headset" size={18} /></span>
        <span class="rt grow">Поддержка</span>
        <span class="rico"><Icon name="chevron" size={16} /></span>
      </button>
    {/if}
  </div>

  <!-- Тема -->
  <div class="block-head"><span class="eyebrow">Оформление</span></div>
  <div class="panel rows">
    <button class="row tap" on:click={toggleTheme}>
      <span class="lico"><Icon name={$theme === 'dark' ? 'sun' : 'moon'} size={18} /></span>
      <span class="rt grow">{$theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}</span>
      <span class="switch" class:on={$theme === 'light'}><i></i></span>
    </button>
  </div>

  <p class="foot mono">ArcVPN · Smart Route</p>
</section>

<style>
  .view {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .phead h1 {
    font-size: 25px;
    font-weight: 800;
    padding: 0 2px;
  }

  .user {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 16px;
  }
  .ava {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    flex: none;
    object-fit: cover;
    border: 1px solid var(--border-strong);
  }
  .ava-txt {
    display: grid;
    place-items: center;
    background: var(--brand-soft);
    color: var(--brand);
    font-size: 21px;
    font-weight: 800;
  }
  .who {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .name {
    font-size: 18px;
    font-weight: 700;
  }
  .who .muted {
    font-size: 13.5px;
  }

  .block-head {
    padding: 2px 4px 0;
    margin-top: 2px;
  }

  .rows {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 14px 16px;
    text-align: left;
    color: var(--text);
    border-top: 1px solid var(--hairline);
  }
  .row:first-child {
    border-top: none;
  }
  .row.col {
    flex-direction: column;
    align-items: stretch;
    gap: 9px;
  }
  .row-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .row.tap:active {
    background: var(--tap);
  }
  .lico {
    flex: none;
    color: var(--muted);
    display: inline-flex;
  }
  .rt {
    font-size: 14.5px;
    color: var(--muted);
  }
  .rt.grow {
    flex: 1;
    min-width: 0;
    color: var(--text);
    font-weight: 600;
  }
  .rv {
    margin-left: auto;
    font-size: 14px;
    font-weight: 600;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rv.warn {
    color: var(--amber);
  }
  .rico {
    flex: none;
    color: var(--faint);
    display: inline-flex;
  }
  .badge {
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 4px 10px;
    border-radius: var(--radius-pill);
  }
  .badge.on {
    color: var(--signal);
    background: var(--signal-soft);
  }
  .badge.off {
    color: var(--amber);
    background: var(--amber-soft);
  }
  .bar {
    height: 7px;
    border-radius: var(--radius-pill);
    background: var(--surface-3);
    overflow: hidden;
  }
  .bar b {
    display: block;
    height: 100%;
    border-radius: var(--radius-pill);
    background: var(--brand);
  }
  .switch {
    flex: none;
    margin-left: auto;
    width: 42px;
    height: 25px;
    border-radius: var(--radius-pill);
    background: var(--surface-3);
    border: 1px solid var(--border-strong);
    position: relative;
    transition: background 0.18s ease;
  }
  .switch.on {
    background: var(--brand);
    border-color: var(--brand);
  }
  .switch i {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 19px;
    height: 19px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.18s ease;
  }
  .switch.on i {
    transform: translateX(17px);
  }
  .foot {
    text-align: center;
    font-size: 11px;
    letter-spacing: 0.08em;
    color: var(--faint);
    margin: 8px 0 2px;
  }
</style>
