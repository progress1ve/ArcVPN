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
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return res.json()
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
        import_url: 'https://arcc.mooo.com:2053/import/demo',
        sub_url: 'https://arcc.mooo.com:2053/sub/demo?format=plain',
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
      { id: 1, name: '1 месяц', duration_days: 31, price_rub: 150, price_stars: 0, traffic_limit_gb: 0 },
      { id: 2, name: '3 месяца', duration_days: 90, price_rub: 449, price_stars: 0, traffic_limit_gb: 0 },
      { id: 3, name: 'Полгода', duration_days: 180, price_rub: 749, price_stars: 0, traffic_limit_gb: 0 },
    ],
  },
  referral: {
    ok: true,
    enabled: true,
    code: 'aB3kZ9xQ',
    link: 'https://t.me/arcvpn_bot?start=ref_aB3kZ9xQ',
    balance_cents: 0,
    reward_type: 'days',
    earned_days: 16,
    trial_bonus_days: 3,
    purchase_bonus_days: 5,
    total_invited: 4,
    paid_invited: 2,
    friends: [
      { name: 'Алексей', username: 'alex_k', created_at: '', has_paid: true },
      { name: 'Марина', username: null, created_at: '', has_paid: true },
      { name: 'Дмитрий', username: 'dmtr', created_at: '', has_paid: false },
      { name: 'Гость', username: null, created_at: '', has_paid: false },
    ],
  },
}

const mock = (key) => new Promise((r) => setTimeout(() => r(MOCK[key]), 250))

export const fetchStatus = () => (import.meta.env.DEV ? mock('status') : get('/api/status'))
export const fetchTariffs = () => (import.meta.env.DEV ? mock('tariffs') : get('/api/tariffs'))
export const fetchReferral = () => (import.meta.env.DEV ? mock('referral') : get('/api/referral'))
