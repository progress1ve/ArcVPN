<script>
  import { status, tariffs, loadStatus, loadTariffs } from '../lib/data.js'
  import { openTelegram } from '../lib/telegram.js'
  import { theme, toggleTheme } from '../lib/theme.js'
  import { daysLeft, daysWord, leftVerb, formatDate, formatRub } from '../lib/format.js'
  import Icon from '../components/Icon.svelte'

  export let goConnect = () => {}
  export let goReferral = () => {}

  loadStatus()
  loadTariffs()

  let tariffsEl
  function scrollTariffs() {
    tariffsEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  $: keys = $status.data?.keys ?? []
  $: activeKeys = keys.filter((k) => k.is_active)
  $: primary = activeKeys[0] ?? keys[0] ?? null
  $: links = $status.data?.links ?? {}
  // На главной показываем не больше трёх тарифов.
  $: plans = ($tariffs.data?.tariffs ?? []).slice(0, 3)

  $: dleft = primary ? daysLeft(primary.expires_at_unix) : 0
  $: popularIdx = plans.length >= 3 ? 1 : -1

  function buy(id) {
    const base = links.bot_url || ''
    if (base) openTelegram(`${base}?start=buy_${id}`)
  }
  function extend() {
    const plan = plans[popularIdx] || plans[0]
    if (plan) buy(plan.id)
  }
  function openLink(url) {
    if (url) openTelegram(url)
  }

  $: SHORTCUTS = [
    { icon: 'wallet', label: 'Тарифы', act: scrollTariffs },
    { icon: 'users', label: 'Друзья', act: goReferral },
    { icon: 'channel', label: 'Канал', act: () => openLink(links.channel_url) },
    { icon: 'headset', label: 'Поддержка', act: () => openLink(links.support_url) },
    { icon: $theme === 'dark' ? 'sun' : 'moon', label: 'Тема', act: toggleTheme },
  ]

  const FEATURES = [
    { icon: 'phone', title: 'Без лимита устройств', val: 'Телефон, ПК и ТВ' },
    { icon: 'zap', title: 'Быстрые серверы', val: 'Низкий пинг' },
    { icon: 'eyeoff', title: 'Без логов', val: 'Полная приватность' },
    { icon: 'globe', title: 'Локации', val: 'Европа, Азия, Америка' },
  ]
</script>

<section class="view">
  <!-- Hero — карточка по референсу -->
  {#if $status.loading && !$status.data}
    <div class="skeleton" style="height:196px"></div>
  {:else}
    <div class="hero">
      <div class="stars" aria-hidden="true"></div>

      {#if primary && primary.is_active}
        <div class="hero-top">
          <span class="hero-label">Подписка активна</span>
          <span class="chip"><Icon name="pin" size={13} /> {primary.server_name || 'ArcVPN'}</span>
        </div>

        <div class="value-row">
          <span class="v-num mono">{dleft}</span>
          <span class="v-word">{daysWord(dleft)} {leftVerb(dleft)}</span>
        </div>
        <div class="v-sub">до {formatDate(primary.expires_at_unix)}</div>

        <div class="actions">
          <button class="act fill" on:click={goConnect}>
            <Icon name="connect" size={17} /> Подключить
          </button>
          <button class="act circle" on:click={extend} aria-label="Продлить">
            <Icon name="plus" size={20} strokeWidth={2.4} />
          </button>
          <button class="act out" on:click={goReferral}>
            <Icon name="gift" size={17} /> Пригласить
          </button>
        </div>
      {:else}
        <div class="hero-top">
          <span class="hero-label">Подписка</span>
          <span class="chip off">не активна</span>
        </div>
        <div class="value-row">
          <span class="v-num mono off">—</span>
        </div>
        <div class="v-sub">
          {#if primary}
            {primary.display_name} закончилась {formatDate(primary.expires_at_unix)}.
          {:else}
            Оформите подписку — оплата в боте.
          {/if}
        </div>
        {#if plans[popularIdx] || plans[0]}
          <div class="actions">
            <button class="act fill wide" on:click={extend}>
              <Icon name="zap" size={17} /> Оформить · {formatRub((plans[popularIdx] || plans[0]).price_rub)}
            </button>
          </div>
        {/if}
      {/if}
    </div>

    <!-- Ряд круглых ярлыков -->
    <div class="shortcuts">
      {#each SHORTCUTS as s}
        <button class="sc" on:click={s.act}>
          <span class="sc-ico"><Icon name={s.icon} size={20} /></span>
          <span class="sc-label">{s.label}</span>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Тарифы -->
  <div class="block-head" bind:this={tariffsEl}>
    <span class="eyebrow">Тарифы</span>
    <span class="hint mono">оплата в боте</span>
  </div>

  {#if $tariffs.loading && !$tariffs.data}
    <div class="plans">
      <div class="skeleton" style="height:118px"></div>
      <div class="skeleton" style="height:118px"></div>
      <div class="skeleton" style="height:118px"></div>
    </div>
  {:else}
    <div class="plans">
      {#each plans as p, i}
        <button class="plan" class:pop={i === popularIdx} on:click={() => buy(p.id)}>
          {#if i === popularIdx}<span class="pop-tag">Хит</span>{/if}
          <span class="plan-price mono">{formatRub(p.price_rub)}</span>
          <span class="plan-name">{p.name}</span>
          <span class="plan-sub">{p.traffic_limit_gb ? `${p.traffic_limit_gb} ГБ` : 'Безлимит'}</span>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Почему ArcVPN -->
  <div class="block-head"><span class="eyebrow">Почему ArcVPN</span></div>
  <ul class="feats">
    {#each FEATURES as f}
      <li class="feat">
        <span class="feat-ico"><Icon name={f.icon} size={17} /></span>
        <span class="feat-title">{f.title}</span>
        <span class="feat-val muted">{f.val}</span>
      </li>
    {/each}
  </ul>
</section>

<style>
  .view {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* Hero-карточка: тёмная база + голубой ореол в нижнем-правом углу */
  .hero {
    position: relative;
    overflow: hidden;
    border-radius: var(--radius-lg);
    border: 1px solid var(--glass-border);
    background:
      radial-gradient(
        100% 155% at 100% 100%,
        color-mix(in srgb, var(--brand) 95%, transparent) 0%,
        color-mix(in srgb, var(--brand) 55%, transparent) 26%,
        color-mix(in srgb, var(--brand) 22%, transparent) 50%,
        transparent 70%
      ),
      var(--surface);
    box-shadow: var(--glass-hi), var(--shadow-float);
    padding: 18px 18px 18px;
  }
  /* Светлая тема: мягче ореол и видимая граница карточки на белом */
  :global([data-theme='light']) .hero {
    border-color: var(--border-strong);
    background:
      radial-gradient(
        100% 150% at 100% 100%,
        color-mix(in srgb, var(--brand) 34%, transparent) 0%,
        color-mix(in srgb, var(--brand) 15%, transparent) 32%,
        transparent 64%
      ),
      var(--surface);
  }
  /* Тонкая «звёздная пыль» в зоне ореола */
  .stars {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image:
      radial-gradient(1.5px 1.5px at 76% 64%, rgba(255, 255, 255, 0.55), transparent),
      radial-gradient(1px 1px at 86% 78%, rgba(255, 255, 255, 0.45), transparent),
      radial-gradient(1px 1px at 68% 86%, rgba(255, 255, 255, 0.4), transparent),
      radial-gradient(1.5px 1.5px at 92% 58%, rgba(255, 255, 255, 0.4), transparent),
      radial-gradient(1px 1px at 60% 72%, rgba(255, 255, 255, 0.3), transparent),
      radial-gradient(1px 1px at 82% 92%, rgba(255, 255, 255, 0.35), transparent);
  }
  :global([data-theme='light']) .stars {
    opacity: 0;
  }
  .hero-top {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .hero-label {
    font-size: 13px;
    color: var(--muted);
    font-weight: 600;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text);
    padding: 6px 12px;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border-strong);
    background: color-mix(in srgb, var(--bg) 30%, transparent);
  }
  .chip :global(svg) {
    color: var(--brand);
  }
  .chip.off {
    color: var(--amber);
    border-color: color-mix(in srgb, var(--amber) 34%, transparent);
  }
  .value-row {
    position: relative;
    display: flex;
    align-items: baseline;
    gap: 9px;
  }
  .v-num {
    font-size: 52px;
    font-weight: 800;
    line-height: 1;
    color: var(--text);
  }
  .v-num.off {
    color: var(--muted);
  }
  .v-word {
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--text);
    white-space: nowrap;
  }
  .v-sub {
    position: relative;
    font-size: 12.5px;
    color: var(--muted);
    margin-top: 7px;
  }

  /* Ряд действий: пилюля + круг + пилюля */
  .actions {
    position: relative;
    display: flex;
    align-items: stretch;
    gap: 10px;
    margin-top: 18px;
  }
  .act {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 50px;
    border-radius: var(--radius-pill);
    font-family: var(--font-display);
    font-size: 14.5px;
    font-weight: 700;
    transition: transform 0.12s ease;
  }
  .act:active {
    transform: scale(0.97);
  }
  .act.fill {
    flex: 1;
    color: #fff;
    background: linear-gradient(135deg, var(--brand) 0%, var(--brand-press) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.25),
      0 8px 20px -10px var(--brand);
  }
  .act.fill.wide {
    flex: 1;
  }
  .act.out {
    flex: 1;
    color: var(--text);
    border: 1px solid var(--border-strong);
    background: color-mix(in srgb, var(--bg) 22%, transparent);
  }
  .act.circle {
    flex: none;
    width: 50px;
    color: var(--text);
    border: 1px solid var(--border-strong);
    background: color-mix(in srgb, var(--bg) 22%, transparent);
  }

  /* Круглые ярлыки */
  .shortcuts {
    display: flex;
    gap: 6px;
  }
  .sc {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .sc-ico {
    width: 54px;
    height: 54px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: var(--text);
    background: var(--surface-2);
    border: 1px solid var(--border);
    transition: transform 0.12s ease;
  }
  .sc:active .sc-ico {
    transform: scale(0.94);
  }
  .sc-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  /* Заголовки секций */
  .block-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 0 4px;
    margin-top: 2px;
    scroll-margin-top: 12px;
  }
  .hint {
    font-size: 11px;
    color: var(--faint);
    letter-spacing: 0.04em;
  }

  /* Тарифы */
  .plans {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;
  }
  .plan {
    position: relative;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--panel-top);
    padding: 18px 10px 15px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    text-align: center;
    transition:
      border-color 0.15s ease,
      transform 0.12s ease;
  }
  .plan:active {
    transform: scale(0.98);
  }
  .plan.pop {
    border-color: var(--brand-line);
    background: color-mix(in srgb, var(--brand-soft) 45%, var(--surface));
  }
  .pop-tag {
    position: absolute;
    top: -9px;
    left: 50%;
    transform: translateX(-50%);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--brand-ink);
    background: var(--brand);
    padding: 3px 9px;
    border-radius: var(--radius-pill);
  }
  .plan-price {
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
  }
  .plan-name {
    font-size: 13px;
    font-weight: 700;
  }
  .plan-sub {
    font-size: 11.5px;
    color: var(--muted);
  }

  /* Почему — лёгкие строки */
  .feats {
    list-style: none;
    display: flex;
    flex-direction: column;
  }
  .feat {
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 12px 4px;
    border-top: 1px solid var(--hairline);
  }
  .feat:first-child {
    border-top: none;
  }
  .feat-ico {
    flex: none;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: var(--brand);
    background: var(--surface-2);
    border: 1px solid var(--border);
  }
  .feat-title {
    flex: 1;
    min-width: 0;
    font-size: 14.5px;
    font-weight: 600;
  }
  .feat-val {
    font-size: 12.5px;
    text-align: right;
  }
</style>
