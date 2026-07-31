// API-клиент Mini App. Каждый запрос несёт initData в заголовке
// X-Telegram-Init-Data — сервер валидирует подпись (HMAC по токену бота) и
// достаёт telegram_id. Origin тот же (Flask раздаёт и SPA, и /api/*), CORS не нужен.
import { getInitData } from './telegram.js'

async function get(path) {
  const res = await fetch(path, {
    headers: { 'X-Telegram-Init-Data': getInitData() },
    cache: 'no-store',
  })
  if (res.status === 401) {
    const err = new Error('unauthorized')
    err.code = 401
    throw err
  }
  if (!res.ok) throw await apiError(res)
  return res.json()
}

async function post(path, payload = {}, options = {}) {
  const res = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    keepalive: Boolean(options.keepalive),
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw await apiError(res)
  return res.json()
}

async function mutate(path, method, payload) {
  const res = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  })
  if (!res.ok) throw await apiError(res)
  return res.json()
}

async function apiError(res) {
  let payload = {}
  try { payload = await res.json() } catch (_) { /* empty response */ }
  const err = new Error(payload.error || `HTTP ${res.status}`)
  err.code = res.status
  err.reason = payload.error || ''
  return err
}

// DEV-моки: только для `npm run dev` (предпросмотр дизайна без Telegram/боевого
// API). В прод-сборке import.meta.env.DEV === false → ветка вырезается.
const MOCK = {
  status: {
    ok: true,
    telegram_id: 318471122,
    keys: [
      {
        id: 1,
        display_name: 'ArcVPN · 3 месяца',
        server_name: 'Германия',
        is_active: true,
        is_trial: false,
        expires_at_unix: Math.floor(Date.now() / 1000) + 41 * 86400,
        traffic_used: 23 * 1024 ** 3,
        traffic_limit: 0,
        online_devices: 2,
        has_sub: true,
        import_url: 'happ://add/https://sub.arccnet.space/sub/demo?format=plain',
        sub_url: 'https://sub.arccnet.space/sub/demo?format=plain',
      },
    ],
    links: {
      support_url: 'https://t.me/Turan11627',
      channel_url: 'https://t.me/arcvpn1',
      bot_url: 'https://t.me/arcvpn_bot',
      bot_username: 'arcvpn_bot',
    },
  },
  tariffs: {
    ok: true,
    tariffs: [
      { id: 1, name: '1 месяц', duration_days: 30, price_rub: 125, price_stars: 0, traffic_limit_gb: 0 },
      { id: 2, name: '3 месяца', duration_days: 90, price_rub: 300, price_stars: 0, traffic_limit_gb: 0 },
      { id: 3, name: '6 месяцев', duration_days: 180, price_rub: 540, price_stars: 0, traffic_limit_gb: 0 },
      { id: 4, name: '12 месяцев', duration_days: 365, price_rub: 960, price_stars: 0, traffic_limit_gb: 0 },
    ],
  },
  referral: {
    ok: true,
    enabled: true,
    code: 'aB3kZ9xQ',
    link: 'https://t.me/arcvpn_bot?start=ref_aB3kZ9xQ',
    site_link: 'https://sub.arccnet.space/invite/aB3kZ9xQ',
    balance_cents: 0,
    reward_type: 'days',
    earned_days: 30,
    trial_bonus_days: 5,
    purchase_bonus_days: 15,
    total_invited: 4,
    paid_invited: 2,
    friends: [
      { name: 'Алексей', username: 'alex_k', created_at: '', has_paid: true },
      { name: 'Марина', username: null, created_at: '', has_paid: true },
      { name: 'Дмитрий', username: 'dmtr', created_at: '', has_paid: false },
      { name: 'Гость', username: null, created_at: '', has_paid: false },
    ],
  },
  account: {
    ok: true,
    telegram_id: 318471122,
    username: 'arc_user',
    email: null,
    email_verified: false,
    email_available: true,
  },
  preferences: {
    ok: true,
    notifications: { expiry: true, traffic: true, connection: true },
  },
  devices: {
    ok: true,
    online_total: 2,
    devices: [
      { id: 1, platform: 'ios', model: 'iPhone', display_name: 'iPhone', browser: 'Telegram', imported_at: '2026-07-29 12:40:00', last_seen_at: '2026-07-29 12:40:00' },
      { id: 2, platform: 'windows', model: 'Windows', display_name: 'Windows PC', browser: 'Chrome', imported_at: '2026-07-28 19:12:00', last_seen_at: '2026-07-28 19:12:00' },
    ],
  },
  support: {
    ok: true,
    thread_id: 1,
    messages: [
      { id: 1, sender: 'admin', body: 'Здравствуйте! Опишите вопрос — ответ придёт сюда и уведомлением в Telegram.', created_at: '2026-07-29 13:00:00' },
    ],
  },
}

const mock = (key) => new Promise((r) => setTimeout(() => r(MOCK[key]), 250))

export const fetchStatus = () => (import.meta.env.DEV ? mock('status') : get('/api/status'))
export const fetchAdminOverview = () => (import.meta.env.DEV
  ? Promise.resolve({
      ok: true,
      users: { day: 12, week: 74, month: 286, total: 1824 },
      subscriptions: { active: 641, expired: 138, month: 207, total: 779 },
      revenue: { day: { total_rub: 4875, count: 31 }, month: { total_rub: 126400, count: 812 } },
      conversion: { conversion_rate: 28.4, trial_users: 972, converted: 276 },
      activity: { online_now: 93, d3: 508, week: 617, month: 705 },
      operations: { open_support_threads: 7, pending_payments: 14 },
      local_panel: { healthy: true, inbounds: 8, detail: 'ok' },
      servers: [
        { id: 10, name: 'Германия', is_active: 1, active_clients: 402, clients_count: 510 },
        { id: 11, name: 'Финляндия', is_active: 1, active_clients: 239, clients_count: 303 },
      ],
    })
  : get('/api/admin/overview'))
export const loginAdmin = (password) => post('/api/admin/login', { password })
export const logoutAdmin = () => post('/api/admin/logout')
export const fetchTariffs = () => (import.meta.env.DEV ? mock('tariffs') : get('/api/tariffs'))
export const fetchReferral = () => (import.meta.env.DEV ? mock('referral') : get('/api/referral'))
export const fetchAccount = () => (import.meta.env.DEV ? mock('account') : get('/api/account'))
export const fetchPreferences = () => (import.meta.env.DEV ? mock('preferences') : get('/api/preferences'))
export const fetchDevices = () => (import.meta.env.DEV ? mock('devices') : get('/api/devices'))
export const renameDevice = (deviceId, displayName) =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, device_id: deviceId, display_name: displayName })
    : mutate(`/api/devices/${encodeURIComponent(deviceId)}`, 'PATCH', { display_name: displayName }))
export const releaseDevice = (deviceId) =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, released: true })
    : mutate(`/api/devices/${encodeURIComponent(deviceId)}`, 'DELETE'))
export const registerImportDevice = (subId, device) =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, device_name: device?.model || device?.platform || 'Устройство' })
    : post(`/api/device/import/${encodeURIComponent(subId)}`, device, { keepalive: true }))
export const createSbpPayment = (tariffId, devices = 2, lteGb = 20) =>
  post('/api/payments/sbp', { tariff_id: tariffId, devices, lte_gb: lteGb })
export const fetchSbpPayment = (orderId) =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, status: 'succeeded', applied: true })
    : get(`/api/payments/sbp/${encodeURIComponent(orderId)}`))
export const fetchSupportMessages = (after = 0) => (import.meta.env.DEV ? mock('support') : get(`/api/support/messages?after=${encodeURIComponent(after)}`))

export async function sendSupportMessage(body) {
  if (import.meta.env.DEV) {
    const message = { id: Date.now(), sender: 'user', body, created_at: new Date().toISOString() }
    MOCK.support.messages.push(message)
    return { ok: true, thread_id: 1, message }
  }
  return post('/api/support/messages', { body })
}

export async function savePreferences(values) {
  if (import.meta.env.DEV) {
    MOCK.preferences.notifications = { ...MOCK.preferences.notifications, ...values }
    return structuredClone(MOCK.preferences)
  }
  return post('/api/preferences', values)
}

export async function requestEmailCode(email, purpose = 'link') {
  if (import.meta.env.DEV) return { ok: true, sent: true }
  return post('/api/auth/email/request', { email, purpose })
}

export async function verifyEmailCode(email, code, purpose = 'link') {
  if (import.meta.env.DEV) {
    if (code !== '123456') throw Object.assign(new Error('invalid_code'), { reason: 'invalid_code', code: 400 })
    MOCK.account.email = email
    MOCK.account.email_verified = true
    return { ok: true, email }
  }
  return post('/api/auth/email/verify', { email, code, purpose })
}

export async function unlinkEmail() {
  if (import.meta.env.DEV) {
    MOCK.account.email = null
    MOCK.account.email_verified = false
    return { ok: true }
  }
  return post('/api/auth/email/unlink')
}

export const logout = () => (import.meta.env.DEV ? Promise.resolve({ ok: true }) : post('/api/auth/logout'))
