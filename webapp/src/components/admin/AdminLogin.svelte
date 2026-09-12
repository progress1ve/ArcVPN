<script>
  export let error = 'auth'
  export let password = ''
  export let signingIn = false
  export let onSubmit = () => {}
</script>

<main class="auth-shell">
  <section class="auth-card" aria-labelledby="admin-login-title">
    <div class="brand-mark"><img src="/app/arc-logo-new.webp" alt="" /></div>
    <span class="eyebrow">Управление ArcVPN</span>
    <h1 id="admin-login-title">Вход в Admin</h1>
    <p>{error === 'auth' ? 'Введите пароль владельца или откройте панель из Telegram.' : error === 'forbidden' ? 'Для вашей роли пока нет доступных разделов.' : error}</p>
    {#if error !== 'forbidden'}
      <form on:submit|preventDefault={onSubmit}>
        <label for="admin-password">Пароль</label>
        <input id="admin-password" bind:value={password} type="password" autocomplete="current-password" placeholder="Введите пароль" />
        <button disabled={signingIn || !password}>{signingIn ? 'Проверяем…' : 'Войти'}</button>
      </form>
    {/if}
  </section>
</main>

<style>
  .auth-shell{box-sizing:border-box;min-height:100dvh;display:grid;place-items:center;padding:28px 18px;background:#090d12;color:#f1f4f7;font-family:Inter,system-ui,sans-serif}
  .auth-card{box-sizing:border-box;width:min(390px,100%);padding:30px;border:1px solid #252e39;border-radius:14px;background:#11171f;box-shadow:0 24px 70px rgba(0,0,0,.38)}
  .brand-mark{width:40px;height:40px;display:grid;place-items:center;margin-bottom:24px;border:1px solid #28323e;border-radius:10px;background:#161d26}.brand-mark img{width:26px}.eyebrow{color:#69b4e6;font-size:9px;font-weight:750;letter-spacing:.1em;text-transform:uppercase}h1{margin:7px 0 8px;font-size:25px;letter-spacing:-.03em}p{margin:0;color:#7f8c9c;font-size:12px;line-height:1.55}form{display:grid;gap:8px;margin-top:22px}label{color:#aab5c1;font-size:10px;font-weight:700}input,button{box-sizing:border-box;width:100%;min-height:42px;border-radius:8px;font:inherit;font-size:12px}input{border:1px solid #2a3440;padding:0 12px;background:#0c1117;color:#fff;outline:none}input:focus-visible{border-color:#54a9eb;box-shadow:0 0 0 3px rgba(84,169,235,.09)}button{margin-top:3px;border:0;background:#54a9eb;color:#07111d;font-weight:750;cursor:pointer}button:focus-visible{outline:2px solid #fff;outline-offset:2px}button:disabled{cursor:not-allowed;opacity:.5}
  @media(max-width:480px){.auth-card{padding:25px 20px}}
</style>
