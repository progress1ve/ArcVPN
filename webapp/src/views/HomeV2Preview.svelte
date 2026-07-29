<script>
  import Icon from '../components/Icon.svelte'
  import BrandPlaceholder from '../components/BrandPlaceholder.svelte'

  export let variant = 'blue'
  const nav = [
    { icon: 'home', label: 'Главная' },
    { icon: 'gift', label: 'Друзья' },
    { icon: 'headset', label: 'Поддержка' },
    { icon: 'user', label: 'Настройки' },
  ]
</script>

<div class="preview" class:mono={variant === 'mono'}>
  <div class="ambient a1" aria-hidden="true"></div>
  <div class="ambient a2" aria-hidden="true"></div>

  <header class="topbar">
    <div class="brand">
      <span class="brand-mark"><BrandPlaceholder size={31} /></span>
      <span class="word">ArcVPN</span>
    </div>
    <button class="avatar" aria-label="Профиль">K</button>
  </header>

  <main>
    <section class="hero">
      <div class="hero-shape" aria-hidden="true"><BrandPlaceholder size={164} /></div>
      <div class="status"><i></i> Подписка активна</div>
      <div class="remaining">Осталось</div>
      <div class="days-row"><strong>27</strong><span>дней</span></div>
      <p>до 21 августа 2026</p>
    </section>

    <section class="primary-actions" aria-label="Основные действия">
      <button class="primary"><Icon name="wallet" size={19} /> Продлить подписку</button>
      <button class="secondary"><Icon name="connect" size={19} /> Подключить VPN</button>
    </section>

    <section class="metrics" aria-label="Статистика подписки">
      <article class="metric">
        <span class="metric-icon"><Icon name="gauge" size={18} /></span>
        <span class="metric-label">Обычный трафик</span>
        <strong>804 ГБ</strong>
        <span class="metric-sub">осталось из 1 ТБ</span>
        <div class="progress"><i style="width:78%"></i></div>
      </article>
      <article class="metric">
        <span class="metric-icon"><Icon name="signal" size={18} /></span>
        <span class="metric-label">Обход LTE</span>
        <strong>Безлимит</strong>
        <span class="metric-sub">белые списки</span>
        <div class="progress unlimited"><i></i></div>
      </article>
      <button class="devices">
        <span class="device-icon"><Icon name="phone" size={19} /></span>
        <span class="device-copy"><b>Устройства</b><small>2 устройства подключено</small></span>
        <span class="device-count">2</span><Icon name="chevron" size={18} />
      </button>
    </section>

    <section class="quick-grid">
      <button class="quick referral">
        <span class="quick-icon"><Icon name="gift" size={22} /></span>
        <b>Пригласи друга</b><small>Вам обоим по 15 дней</small>
        <span class="quick-link">Подробнее <Icon name="chevron" size={15} /></span>
      </button>
      <button class="quick support">
        <span class="quick-icon"><Icon name="headset" size={22} /></span>
        <b>Поддержка</b><small>FAQ и живой чат</small>
        <span class="quick-link">Написать <Icon name="chevron" size={15} /></span>
      </button>
    </section>
  </main>

  <div class="dock">
    <nav>
      {#each nav as item, i}
        <button class:active={i === 0} aria-label={item.label}>
          <span><Icon name={item.icon} size={21} strokeWidth={2.1} /></span><small>{item.label}</small>
        </button>
      {/each}
    </nav>
  </div>
</div>

<style>
  .preview {
    --p-bg: #060a12; --p-surface: #0c1422; --p-raised: #111d2d;
    --p-border: rgba(157, 204, 255, 0.13); --p-border-strong: rgba(157, 204, 255, 0.22);
    --p-text: #f7faff; --p-muted: #8fa2b8; --p-faint: #61758b;
    --p-accent: #48b8ff; --p-accent-strong: #168dff; --p-accent-soft: rgba(72, 184, 255, 0.13);
    --p-success: #49d39a; --preview-mark-cut: var(--p-bg);
    position: relative; min-height: 100dvh; padding-bottom: calc(102px + env(safe-area-inset-bottom, 0px));
    overflow: hidden; color: var(--p-text); background: var(--p-bg);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .preview.mono {
    --p-bg: #070707; --p-surface: #101010; --p-raised: #161616;
    --p-border: rgba(255, 255, 255, 0.09); --p-border-strong: rgba(255, 255, 255, 0.17);
    --p-text: #f5f5f2; --p-muted: #a3a3a0; --p-faint: #696966;
    --p-accent: #f5f5f2; --p-accent-strong: #d6d6d2; --p-accent-soft: rgba(255, 255, 255, 0.08);
    --p-success: #79e2b7;
  }
  .ambient { position: absolute; pointer-events: none; border-radius: 50%; }
  .a1 { width: 360px; height: 360px; top: -170px; right: -170px; background: radial-gradient(circle, rgba(22, 141, 255, 0.3), transparent 69%); }
  .a2 { width: 300px; height: 300px; top: 520px; left: -230px; background: radial-gradient(circle, rgba(72, 184, 255, 0.14), transparent 70%); }
  .mono .ambient { display: none; }
  .topbar, main, .dock { position: relative; z-index: 2; }
  .topbar { display: flex; align-items: center; justify-content: space-between; padding: calc(env(safe-area-inset-top, 0px) + 18px) 20px 16px; }
  .brand { display: flex; align-items: center; gap: 10px; }
  .brand-mark { display: inline-flex; color: var(--p-text); }
  .word, .days-row strong, .days-row span { font-family: 'Unbounded', 'Inter', sans-serif; }
  .word { font-size: 17px; font-weight: 700; letter-spacing: -0.04em; }
  .avatar { width: 40px; height: 40px; border: 1px solid var(--p-border-strong); border-radius: 50%; color: var(--p-text); background: color-mix(in srgb, var(--p-raised) 82%, transparent); font-weight: 700; }
  main { display: flex; flex-direction: column; gap: 16px; padding: 0 16px; }
  .hero { position: relative; min-height: 214px; overflow: hidden; padding: 22px; border: 1px solid var(--p-border); border-radius: 28px; background: radial-gradient(120% 150% at 105% 105%, rgba(72, 184, 255, 0.24), transparent 60%), linear-gradient(145deg, rgba(17, 29, 45, 0.96), rgba(8, 15, 26, 0.98)); box-shadow: 0 22px 70px -38px rgba(22, 141, 255, 0.75); }
  .mono .hero { background: var(--p-surface); box-shadow: none; }
  .hero::after { content: ''; position: absolute; inset: 0; pointer-events: none; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05); border-radius: inherit; }
  .hero-shape { position: absolute; right: -32px; bottom: -42px; color: rgba(72, 184, 255, 0.08); transform: rotate(-8deg); }
  .mono .hero-shape { color: rgba(255, 255, 255, 0.025); }
  .status { position: relative; display: inline-flex; align-items: center; gap: 8px; padding: 7px 11px; border: 1px solid rgba(73, 211, 154, 0.2); border-radius: 999px; color: #a9efd0; background: rgba(73, 211, 154, 0.08); font-size: 12px; font-weight: 650; }
  .status i { width: 7px; height: 7px; border-radius: 50%; background: var(--p-success); box-shadow: 0 0 14px var(--p-success); }
  .remaining { position: relative; margin-top: 22px; color: var(--p-muted); font-size: 13px; font-weight: 600; }
  .days-row { position: relative; display: flex; align-items: baseline; gap: 10px; margin-top: 1px; }
  .days-row strong { font-size: 56px; line-height: 1.05; letter-spacing: -0.08em; }
  .days-row span { font-size: 19px; font-weight: 600; letter-spacing: -0.04em; }
  .hero p { position: relative; margin-top: 4px; color: var(--p-muted); font-size: 13px; }
  .primary-actions { display: grid; gap: 10px; }
  .primary-actions button { min-height: 54px; display: flex; align-items: center; justify-content: center; gap: 10px; border-radius: 18px; font-size: 15px; font-weight: 750; }
  .primary { color: #04121e; background: linear-gradient(135deg, #79cbff, var(--p-accent)); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55), 0 14px 34px -20px rgba(72, 184, 255, 0.9); }
  .mono .primary { color: #090909; background: var(--p-text); box-shadow: none; }
  .secondary { color: var(--p-text); border: 1px solid var(--p-border-strong); background: var(--p-accent-soft); }
  .mono .secondary { background: transparent; }
  .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .metric, .devices, .quick { border: 1px solid var(--p-border); background: color-mix(in srgb, var(--p-surface) 93%, transparent); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035); }
  .metric { min-width: 0; padding: 16px; border-radius: 22px; }
  .metric-icon, .device-icon, .quick-icon { display: grid; place-items: center; color: var(--p-accent); background: var(--p-accent-soft); }
  .metric-icon { width: 34px; height: 34px; margin-bottom: 14px; border-radius: 12px; }
  .metric-label, .metric-sub { display: block; overflow: hidden; color: var(--p-muted); font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }
  .metric strong { display: block; margin: 3px 0 1px; overflow: hidden; font-size: 17px; text-overflow: ellipsis; white-space: nowrap; }
  .progress { height: 4px; margin-top: 13px; overflow: hidden; border-radius: 99px; background: rgba(255, 255, 255, 0.07); }
  .progress i { display: block; height: 100%; border-radius: inherit; background: var(--p-accent); }
  .progress.unlimited i { width: 100%; background: linear-gradient(90deg, var(--p-accent), var(--p-success)); }
  .mono .progress.unlimited i { background: var(--p-text); }
  .devices { grid-column: 1 / -1; min-height: 68px; display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 20px; color: var(--p-muted); text-align: left; }
  .device-icon { flex: none; width: 40px; height: 40px; border-radius: 14px; }
  .device-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .device-copy b { color: var(--p-text); font-size: 14px; }
  .device-copy small { margin-top: 2px; color: var(--p-muted); font-size: 11.5px; }
  .device-count { min-width: 30px; padding: 5px 9px; border-radius: 999px; color: var(--p-text); background: var(--p-accent-soft); font-size: 12px; font-weight: 700; text-align: center; }
  .quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .quick { min-height: 148px; display: flex; flex-direction: column; align-items: flex-start; padding: 16px; overflow: hidden; border-radius: 23px; color: var(--p-text); text-align: left; }
  .quick-icon { width: 40px; height: 40px; margin-bottom: 14px; border-radius: 14px; }
  .quick b { font-size: 14px; }
  .quick small { min-height: 34px; margin-top: 4px; color: var(--p-muted); font-size: 11.5px; line-height: 1.4; }
  .quick-link { display: flex; align-items: center; gap: 2px; margin-top: auto; color: var(--p-accent); font-size: 12px; font-weight: 700; }
  .dock { position: fixed; z-index: 20; left: 50%; bottom: calc(env(safe-area-inset-bottom, 0px) + 12px); width: min(100%, 460px); padding: 0 16px; transform: translateX(-50%); }
  .dock nav { display: flex; gap: 4px; padding: 7px; border: 1px solid var(--p-border-strong); border-radius: 24px; background: rgba(10, 17, 28, 0.92); box-shadow: 0 20px 60px -22px rgba(0, 0, 0, 0.85); backdrop-filter: blur(20px); }
  .mono .dock nav { background: rgba(16, 16, 16, 0.94); }
  .dock button { flex: 1; min-width: 0; min-height: 53px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; border-radius: 18px; color: var(--p-faint); }
  .dock button span { display: inline-flex; }
  .dock button small { overflow: hidden; max-width: 100%; font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
  .dock button.active { color: var(--p-text); background: var(--p-accent-soft); }
  .mono .dock button.active { color: #090909; background: var(--p-text); }
  @media (max-width: 360px) { .days-row strong { font-size: 50px; } .quick, .metric { padding: 14px; } }
</style>
