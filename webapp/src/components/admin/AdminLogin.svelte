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
  .auth-shell{box-sizing:border-box;min-height:100dvh;display:grid;place-items:center;padding:32px 20px;background:radial-gradient(720px 480px at 50% 20%,rgba(69,146,202,.18),transparent 65%),#070a10;color:#f4f8fc;font-family:Inter,system-ui,sans-serif}
  .auth-card{box-sizing:border-box;width:min(420px,100%);padding:38px;border:1px solid rgba(162,207,244,.12);border-radius:24px;background:rgba(12,18,27,.94);box-shadow:0 30px 80px rgba(0,0,0,.42)}
  .brand-mark{width:48px;height:48px;display:grid;place-items:center;margin-bottom:28px;border-radius:15px;background:#111c29}.brand-mark img{width:34px}.eyebrow{color:#80bfe7;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}h1{margin:8px 0 10px;font-size:30px;letter-spacing:-.04em}p{margin:0;color:#899aaa;font-size:13px;line-height:1.6}form{display:grid;gap:10px;margin-top:26px}label{color:#b9c7d3;font-size:11px;font-weight:800}input,button{box-sizing:border-box;width:100%;min-height:48px;border-radius:13px;font:inherit}input{border:1px solid rgba(162,207,244,.13);padding:0 15px;background:#080e16;color:#fff;outline:none}input:focus-visible{border-color:#8ed3ff;box-shadow:0 0 0 3px rgba(142,211,255,.1)}button{margin-top:4px;border:0;background:#9bd9ff;color:#07111d;font-weight:850;cursor:pointer}button:focus-visible{outline:3px solid #fff;outline-offset:3px}button:disabled{cursor:not-allowed;opacity:.5}
  @media(max-width:480px){.auth-card{padding:30px 24px;border-radius:20px}}
</style>
