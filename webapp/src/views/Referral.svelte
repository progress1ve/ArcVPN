<script>
  import { referral, loadReferral } from '../lib/data.js'
  import { openTelegram } from '../lib/telegram.js'
  import { copyText } from '../lib/ui.js'
  import { peopleWord, daysWord } from '../lib/format.js'
  import Icon from '../components/Icon.svelte'
  import Button from '../components/Button.svelte'

  loadReferral()

  $: d = $referral.data ?? {}
  $: enabled = d.enabled
  $: friends = d.friends ?? []
  $: earnedDays = d.earned_days ?? 0
  $: purchaseBonus = d.purchase_bonus_days ?? 15
  $: entryBonus = d.trial_bonus_days ?? 5

  $: STEPS = [
    { t: 'Поделитесь ссылкой', s: 'Отправьте другу свою реферальную ссылку' },
    { t: `Друг открыл бота — +${entryBonus} ${daysWord(entryBonus)}`, s: `Начислим вам сразу после его первого входа` },
    { t: `Друг купил подписку — +${purchaseBonus} ${daysWord(purchaseBonus)}`, s: `Вам и другу — по +${purchaseBonus} ${daysWord(purchaseBonus)} за его первую покупку` },
  ]

  function share() {
    if (!d.link) return
    const url = `https://t.me/share/url?url=${encodeURIComponent(d.link)}&text=${encodeURIComponent('Подключайся к ArcVPN')}`
    openTelegram(url)
  }
  function initials(name) {
    return (name || '?').trim().charAt(0).toUpperCase()
  }
</script>

<section class="view">
  <header class="head">
    <h1 class="display">Друзья</h1>
    <p class="muted">Получите +{entryBonus} дней за вход друга и ещё по {purchaseBonus} дней после его первой покупки.</p>
  </header>

  {#if $referral.loading && !$referral.data}
    <div class="skeleton" style="height:96px"></div>
    <div class="skeleton" style="height:160px"></div>
  {:else if $referral.error}
    <div class="panel pad"><p class="muted">Не удалось загрузить. Откройте приложение из бота ArcVPN.</p></div>
  {:else if !enabled}
    <div class="panel pad center">
      <span class="big-ico"><Icon name="gift" size={24} /></span>
      <p class="muted">Партнёрская программа сейчас отключена. Загляните позже.</p>
    </div>
  {:else}
    <!-- Счётчики-приборы -->
    <div class="stats">
      <div class="panel stat">
        <span class="stat-num mono">{d.total_invited ?? 0}</span>
        <span class="stat-label">{peopleWord(d.total_invited ?? 0)}</span>
      </div>
      <div class="panel stat">
        <span class="stat-num mono">{d.paid_invited ?? 0}</span>
        <span class="stat-label">оплатили</span>
      </div>
      <div class="panel stat hl">
        <span class="stat-num mono">{earnedDays}</span>
        <span class="stat-label">{daysWord(earnedDays)} получено</span>
      </div>
    </div>

    <!-- Ссылка -->
    <div class="panel link-card">
      <span class="eyebrow">Ваша ссылка</span>
      <code class="link mono">{d.link || '—'}</code>
      <div class="link-actions">
        <Button on:click={share}><Icon name="send" size={17} /> Поделиться</Button>
        <Button variant="ghost" full={false} on:click={() => copyText(d.link, 'Ссылка скопирована')}>
          <Icon name="copy" size={17} />
        </Button>
      </div>
    </div>

    <!-- Как это работает -->
    <div class="block-head"><span class="eyebrow">Как это работает</span></div>
    <div class="panel steps">
      {#each STEPS as st, i}
        <div class="step">
          <span class="step-n mono">{i + 1}</span>
          <div class="step-body">
            <span class="step-t">{st.t}</span>
            <span class="muted small">{st.s}</span>
          </div>
        </div>
      {/each}
    </div>

    <!-- Приглашённые -->
    <div class="block-head">
      <span class="eyebrow">Приглашённые</span>
      {#if friends.length}<span class="hint mono">{friends.length}</span>{/if}
    </div>
    {#if friends.length === 0}
      <div class="panel pad center">
        <span class="big-ico"><Icon name="users" size={24} /></span>
        <p class="muted">Пока никого. Поделитесь ссылкой — приглашённые появятся здесь.</p>
      </div>
    {:else}
      <div class="panel friends">
        {#each friends as f}
          <div class="friend">
            <span class="ava">{initials(f.name)}</span>
            <span class="fname">{f.name}{#if f.username}<span class="muted"> · @{f.username}</span>{/if}</span>
            <span class="tag" class:paid={f.has_paid}>{f.has_paid ? 'оплатил' : 'ждём'}</span>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</section>

<style>
  .view {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .head {
    margin-bottom: 2px;
  }
  .head h1 {
    font-size: 25px;
    font-weight: 800;
    margin-bottom: 4px;
  }
  .head p {
    font-size: 13.5px;
  }
  .small {
    font-size: 12.5px;
  }
  .pad {
    padding: 18px;
  }
  .center {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    text-align: center;
  }
  .big-ico {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    color: var(--brand);
    background: var(--brand-soft);
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;
  }
  .stat {
    padding: 16px 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .stat.hl {
    border-color: var(--brand-line);
    background: color-mix(in srgb, var(--brand-soft) 55%, var(--surface));
  }
  .stat-num {
    font-size: 23px;
    font-weight: 700;
    color: var(--text);
  }
  .stat-label {
    font-size: 11.5px;
    color: var(--muted);
  }

  .link-card {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .link {
    display: block;
    font-size: 12.5px;
    color: var(--text);
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 11px 13px;
    word-break: break-all;
    line-height: 1.5;
  }
  .link-actions {
    display: flex;
    gap: 8px;
  }

  .block-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 2px 4px 0;
    margin-top: 2px;
  }
  .hint {
    font-size: 12px;
    color: var(--faint);
  }

  .steps {
    display: flex;
    flex-direction: column;
  }
  .step {
    display: flex;
    gap: 13px;
    align-items: flex-start;
    padding: 14px 16px;
    border-top: 1px solid var(--hairline);
  }
  .step:first-child {
    border-top: none;
  }
  .step-n {
    flex: none;
    width: 26px;
    height: 26px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: var(--brand-soft);
    color: var(--brand);
    font-size: 13px;
    font-weight: 700;
  }
  .step-body {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .step-t {
    font-size: 14.5px;
    font-weight: 700;
  }

  .friends {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .friend {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 12px 14px;
    border-top: 1px solid var(--hairline);
  }
  .friend:first-child {
    border-top: none;
  }
  .ava {
    flex: none;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: var(--brand-soft);
    display: grid;
    place-items: center;
    font-weight: 800;
    font-size: 14px;
    color: var(--brand);
  }
  .fname {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tag {
    flex: none;
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 4px 9px;
    border-radius: var(--radius-pill);
    color: var(--faint);
    background: var(--surface-2);
  }
  .tag.paid {
    color: var(--signal);
    background: var(--signal-soft);
  }
</style>
