// API-клиент Mini App. Каждый запрос несёт initData в заголовке
// X-Telegram-Init-Data — сервер валидирует подпись (HMAC по токену бота) и
// достаёт telegram_id. Origin тот же (Flask раздаёт и SPA, и /api/*), CORS не нужен.
import { getInitData } from './telegram.js'

async function get(path) {
  const res = await fetch(path, {
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
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
        traffic_limit: 1024 * 1024 ** 3,
        lte_quota_gb: 45,
        lte_used_bytes: 13 * 1024 ** 3,
        lte_remaining_bytes: 32 * 1024 ** 3,
        lte_cycle_reset_at: '2026-09-18 10:00:00',
        online_devices: 2,
        has_sub: true,
        import_url: 'happ://add/https://sub.arccnet.space/sub/demo?format=json',
        sub_url: 'https://sub.arccnet.space/sub/demo',
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
      ...[['economy','Эконом',500,0,2,[93,259,499,931]],['standard','Стандарт',1024,45,3,[145,399,759,1469]],['family','Семейный',0,115,10,[345,939,1789,3389]]]
        .flatMap(([product_code,label,traffic_limit_gb,lte_quota_gb,device_limit,prices], familyIndex) => [1,3,6,12].map((period_months,index) => ({ id: familyIndex*4+index+1, name: `${label} · ${period_months} мес.`, product_code, period_months, duration_days: period_months===12?365:period_months*30, price_rub: prices[index], price_stars: 0, traffic_limit_gb, lte_quota_gb, device_limit, lte_cycle_days: 30 }))),
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
  adminSupportThreads: [
    { id: 31, telegram_id: 318471122, first_name: 'Алексей', username: 'alex_k', status: 'open', unread: 2, last_message: 'На ноутбуке перестал открываться профиль, а телефон работает.', updated_at: '2026-08-24 16:42:00' },
    { id: 28, telegram_id: 774215009, first_name: 'Марина', username: 'marina_vpn', status: 'open', unread: 0, last_message: 'Спасибо, после повторного импорта всё подключилось.', updated_at: '2026-08-24 15:18:00' },
    { id: 19, telegram_id: 990120044, first_name: '', username: 'north_wind', status: 'open', unread: 1, last_message: 'Подскажите, как добавить второе устройство?', updated_at: '2026-08-23 21:06:00' },
  ],
  adminSupportMessages: {
    31: [
      { id: 311, sender: 'user', body: 'Здравствуйте. На ноутбуке перестал открываться профиль, а телефон работает.', created_at: '2026-08-24 16:37:00' },
      { id: 312, sender: 'admin', body: 'Добрый день! Уточните, пожалуйста, операционную систему и версию Happ.', created_at: '2026-08-24 16:39:00' },
      { id: 313, sender: 'user', body: 'Windows 11, Happ 2.5.1. Повторный импорт пока не делал.', created_at: '2026-08-24 16:42:00' },
    ],
    28: [
      { id: 281, sender: 'user', body: 'После обновления не подключался телефон.', created_at: '2026-08-24 14:52:00' },
      { id: 282, sender: 'admin', body: 'Удалите старый профиль и импортируйте подписку ещё раз из ArcVPN.', created_at: '2026-08-24 15:03:00' },
      { id: 283, sender: 'user', body: 'Спасибо, после повторного импорта всё подключилось.', created_at: '2026-08-24 15:18:00' },
    ],
    19: [],
  },
}

const mock = (key) => new Promise((r) => setTimeout(() => r(MOCK[key]), 250))
const devSupportState = () => typeof window === 'undefined'
  ? ''
  : new URLSearchParams(window.location.search).get('support-state') || ''
const devAdminState = (key) => typeof window === 'undefined'
  ? ''
  : new URLSearchParams(window.location.search).get(key) || ''
const DEV_ADMIN_PERMISSIONS = {
  owner: ['*'],
  operator: ['audit.read', 'backups.create', 'backups.read', 'campaigns.manage', 'catalog.manage', 'nodes.diagnose', 'overview.read', 'promocodes.manage', 'subscriptions.manage', 'support.read', 'support.reply'],
  support: ['support.read', 'support.reply'],
  finance: ['campaigns.manage', 'expenses.manage', 'overview.read', 'promocodes.manage'],
  viewer: ['backups.read', 'overview.read', 'support.read'],
}
const mockAdminError = (reason, code = 503) => {
  const error = new Error(reason)
  error.code = code
  error.reason = reason
  return error
}
const mockAdminAccess = () => new Promise((resolve, reject) => setTimeout(() => {
  const state = devAdminState('access-state')
  if (state === 'unauthorized') return reject(mockAdminError('admin_unauthorized', 403))
  if (state === 'error') return reject(mockAdminError('admin_access_unavailable'))
  const role = DEV_ADMIN_PERMISSIONS[devAdminState('admin-role')] ? devAdminState('admin-role') : 'owner'
  resolve({ ok: true, role, permissions: [...DEV_ADMIN_PERMISSIONS[role]] })
}, 180))
let mockOverviewRequests = 0
let mockOverviewMode = ''
const mockAdminOverview = () => new Promise((resolve, reject) => setTimeout(() => {
  const state = devAdminState('overview-state')
  if (state !== mockOverviewMode) { mockOverviewMode = state; mockOverviewRequests = 0 }
  mockOverviewRequests += 1
  if (state === 'error' || (state === 'refresh-error' && mockOverviewRequests > 1)) {
    reject(mockAdminError('admin_overview_unavailable'))
    return
  }
  resolve({
    ok: true,
    users: { day: 12, week: 74, month: 286, total: 1824 },
    subscriptions: { active: 641, expired: 138, month: 207, total: 779 },
    revenue: { day: { total_rub: 4875, count: 31 }, month: { total_rub: 126400, count: 812 } },
    financials: { month_rub: 126400, successful_orders: 812 },
    conversion: { conversion_rate: 28.4, trial_users: 972, converted: 276 },
    activity: { online_now: 93, d3: 508, week: 617, month: 705 },
    operations: { open_support_threads: 7, pending_payments: 14, subscription_service: true },
    recurring: { provider_ready: false, active: 0 },
    integrations: { smtp_ready: true, smtp_tls: true },
    local_panel: { healthy: true, inbounds: 8, detail: 'ok' },
    system: { database_integrity: 'ok', disk_used_pct: 43, disk_used_gb: 21.5, disk_total_gb: 50, uptime_seconds: 1284300 },
    device_security: { active_devices: 887, revoked_devices: 19, protected_users: 603, users_over_limit: 2, awaiting_reimport: 4 },
    referrals: { conversion_rate: 31.5, day_invited: 9, month_invited: 184, total_invited: 932, converted: 294, leaders: [] },
    recent_users: [],
    recent_payments: [],
    servers: [
      { id: 10, name: 'Германия', is_active: 1, active_clients: 402, clients_count: 510, telemetry_available: true, latency_ms: 38 },
      { id: 11, name: 'Нидерланды', is_active: 1, active_clients: 239, clients_count: 303, telemetry_available: true, latency_ms: 45 },
    ],
    remnawave: {
      healthy: true, detail: 'ok', users: 779, online_users: Array.from({ length: 93 }, (_, id) => ({ id })),
      nodes: [
        { uuid: 'de-node', name: 'Germany Edge', country_code: 'DE', address: 'edge-de.example.test', connected: true, disabled: false, users_online: 58, traffic_used_gb: 812, memory_used_pct: 43, rx_bps: 2400000, tx_bps: 980000, xray_uptime_seconds: 812000, inbounds: [{ network: 'tcp', port: 443, tag: 'DE Reality' }] },
        { uuid: 'nl-node', name: 'Netherlands Edge', country_code: 'NL', address: 'edge-nl.example.test', connected: true, disabled: false, users_online: 35, traffic_used_gb: 507, memory_used_pct: 38, rx_bps: 1900000, tx_bps: 760000, xray_uptime_seconds: 604000, inbounds: [{ network: 'tcp', port: 443, tag: 'NL Reality' }] },
      ],
      lte_edges: [{ id: 'lte-de', country_code: 'DE', name: 'DE CDN edge', profile_name: 'Обход блокировок', public_host: 'cdn-de.example.test', origin: 'edge-de.example.test', port: 443, network: 'xhttp', path: '/api', users_online: 3, inbound_active: true, healthy: true }],
      connection_schemes: [{ id: 'auto', name: 'Основная схема', kind: 'client_balancer', probe_interval_seconds: 20 }, { id: 'fallback', name: 'Аварийный CDN', kind: 'client_cdn_fallback', origins: ['cdn-de.example.test'], probe_interval_seconds: 20 }],
    },
  })
}, devAdminState('overview-state') === 'slow' ? 1600 : 260))
const mockSupportError = (reason) => {
  const error = new Error(reason)
  error.code = 503
  error.reason = reason
  return error
}

const mockAdminSupportThreads = () => new Promise((resolve, reject) => setTimeout(() => {
  if (devSupportState() === 'list-error') {
    reject(mockSupportError('support_threads_unavailable'))
    return
  }
  resolve({
    ok: true,
    threads: devSupportState() === 'empty' ? [] : MOCK.adminSupportThreads.map((thread) => ({ ...thread })),
  })
}, 420))

const mockAdminSupportThread = (threadId) => new Promise((resolve, reject) => setTimeout(() => {
  if (devSupportState() === 'detail-error') {
    reject(mockSupportError('support_detail_unavailable'))
    return
  }
  const thread = MOCK.adminSupportThreads.find((item) => item.id === Number(threadId))
  if (!thread) {
    const error = new Error('support_thread_not_found')
    error.code = 404
    reject(error)
    return
  }
  thread.unread = 0
  resolve({ ok: true, thread: { ...thread }, messages: (MOCK.adminSupportMessages[thread.id] || []).map((message) => ({ ...message })) })
}, 320))

const mockAdminSupportReply = (threadId, body) => new Promise((resolve, reject) => setTimeout(() => {
  if (devSupportState() === 'send-error') {
    reject(mockSupportError('support_reply_unavailable'))
    return
  }
  const thread = MOCK.adminSupportThreads.find((item) => item.id === Number(threadId))
  if (!thread) {
    const error = new Error('support_thread_not_found')
    error.code = 404
    reject(error)
    return
  }
  const message = { id: Date.now(), sender: 'admin', body, created_at: new Date().toISOString() }
  MOCK.adminSupportMessages[thread.id] = [...(MOCK.adminSupportMessages[thread.id] || []), message]
  thread.last_message = body
  thread.updated_at = message.created_at
  resolve({ ok: true, message: { ...message } })
}, 500))

const devSectionState = (section) => devAdminState(`${section}-state`) || devAdminState('ui-state')
const mockAdminSection = (section, data, emptyData) => new Promise((resolve, reject) => setTimeout(() => {
  const state = devSectionState(section)
  if (state === 'error') return reject(mockAdminError(`${section}_unavailable`))
  resolve(structuredClone(state === 'empty' ? emptyData : data))
}, 280))
let mockCatalogProfiles = [
  { source_name: 'Germany Reality', display_name: 'Германия', protocol_label: 'VLESS Reality', enabled: true, include_in_auto: true, sort_order: 0 },
  { source_name: 'Netherlands Reality', display_name: 'Нидерланды', protocol_label: 'VLESS Reality', enabled: true, include_in_auto: true, sort_order: 1 },
  { source_name: 'Germany LTE', display_name: 'Обход блокировок', protocol_label: 'XHTTP CDN', enabled: true, include_in_auto: false, sort_order: 2 },
]
let mockExpenses = [{ id: 1, title: 'Нода DE', category: 'hosting', amount_rub: 2200, incurred_on: '2026-08-01', recurring_monthly: true, note: 'Месячная аренда' }]
let mockCampaigns = [
  { id: 1, name: 'Яндекс · поиск', code: 'yandex_search', link: 'https://t.me/arcvpn1?start=ad_yandex_search', is_active: 1, entry_bonus_days: 0, payment_bonus_days: 0, arrivals: 184, paying_users: 39, paid_orders: 47, repeat_paid_orders: 8, revenue_cents: 1264000, conversion_percent: 21.2 },
  { id: 2, name: 'Telegram · канал VPN', code: 'tg_vpn_channel', link: 'https://t.me/arcvpn1?start=ad_tg_vpn_channel', is_active: 1, entry_bonus_days: 2, payment_bonus_days: 0, arrivals: 76, paying_users: 22, paid_orders: 24, repeat_paid_orders: 2, revenue_cents: 724300, conversion_percent: 28.95 },
]
let mockPromocodes = [
  { id: 1, code: 'START20', discount_type: 'percent', discount_percent: 20, discount_rub: 0, max_uses: 250, used_count: 68, expires_at: '2026-10-01T00:00:00', is_active: 1 },
  { id: 2, code: 'BACK50', discount_type: 'fixed', discount_percent: 0, discount_rub: 50, max_uses: 100, used_count: 100, expires_at: '2026-09-01T00:00:00', is_active: 0 },
]
let mockBackups = [{ name: 'vpn_bot-20260824-120000.db', size_bytes: 7340032, created_at: '2026-08-24T12:00:00Z' }]
const mockUsers = [
  { telegram_id: 700001, first_name: 'Алексей', username: 'alex', paid_rub: 1250, expires_at: '2026-09-20 12:00:00', active: 1, online_devices: 1, online_node: 'Germany Edge', main_used_bytes: 184 * 1024**3, lte_used_bytes: 29 * 1024**3, lte_quota_gb: 45 },
  { telegram_id: 700002, first_name: 'Марина', username: 'marina', paid_rub: 750, expires_at: '2026-09-05 12:00:00', active: 1, online_devices: 0, main_used_bytes: 88 * 1024**3, lte_used_bytes: 6 * 1024**3, lte_quota_gb: 45 },
]
const mockUserDetail = (telegramId) => ({ ok: true, user: { telegram_id: Number(telegramId), balance_rub: 125, device_limit: 2, lte_used_bytes: 29 * 1024**3, lte_quota_gb: 45 }, subscriptions: [{ id: 10, custom_name: 'ArcVPN', expires_at: '2026-09-20 12:00:00', active: 1, traffic_used: 184 * 1024**3, online_devices: 1 }], payments: [{ order_id: 'qa-order', payment_type: 'sbp', status: 'succeeded', amount_rub: 125, paid_at: '2026-08-20 10:00:00' }], devices: [{ id: 1, active: 1 }], timeline: [{ kind: 'payment', title: 'Оплата подтверждена', detail: '1 месяц', at: '2026-08-20 10:00:00' }] })
const mockAuditEvents = [{ id: 1, action: 'catalog.update', outcome: 'success', actor_id: 'owner', target_type: 'subscription_catalog', created_at: '2026-08-24T12:10:00Z' }, { id: 2, action: 'rbac.denied', outcome: 'denied', actor_id: 'viewer', target_type: 'permission', target_id: 'catalog.manage', created_at: '2026-08-24T12:08:00Z' }]

export const fetchStatus = () => (import.meta.env.DEV
  ? (new URLSearchParams(location.search).get('auth') === 'login'
      ? Promise.reject(Object.assign(new Error('unauthorized'), { code: 401 }))
      : mock('status'))
  : get('/api/status'))
export const fetchAdminAccess = () => (import.meta.env.DEV ? mockAdminAccess() : get('/api/admin/access'))
let mockAdminRoleAssignments = [{ telegram_id: 700001, role: 'operator', assigned_by: 1, updated_at: new Date().toISOString() }]
export const fetchAdminRoles = () => (import.meta.env.DEV
  ? Promise.resolve({ ok: true, assignments: mockAdminRoleAssignments.map((item) => ({ ...item })) })
  : get('/api/admin/roles'))
export const assignAdminRole = (telegramId, role) => (import.meta.env.DEV
  ? Promise.resolve({ ok: true, assignments: (mockAdminRoleAssignments = [
      ...mockAdminRoleAssignments.filter((item) => item.telegram_id !== Number(telegramId)),
      { telegram_id: Number(telegramId), role, assigned_by: 1, updated_at: new Date().toISOString() },
    ]).map((item) => ({ ...item })) })
  : post('/api/admin/roles', { telegram_id: Number(telegramId), role }))
export const fetchAdminOverview = () => (import.meta.env.DEV ? mockAdminOverview() : get('/api/admin/overview'))
export const loginAdmin = (password) => post('/api/admin/login', { password })
export const logoutAdmin = () => post('/api/admin/logout')
export const runAdminNodeDiagnostic = (nodeUuid) => post('/api/admin/diagnostics/run', { node_uuid: nodeUuid })
export const fetchAdminNodeMetrics = (host, range = '1h') => (import.meta.env.DEV
  ? mockAdminSection('metrics', { ok: true, host, range, samples: Array.from({ length: 18 }, (_, index) => ({ cpu_pct: 18 + index % 7, mem_pct: 38 + index % 5, net_rx_bps: 1200000 + index * 70000, net_tx_bps: 420000 + index * 30000 })) }, { ok: true, host, range, samples: [] })
  : get(`/api/admin/nodes/metrics?host=${encodeURIComponent(host)}&range=${encodeURIComponent(range)}`))
export const preflightAdminNode = (payload) => (import.meta.env.DEV
  ? mockAdminSection('preflight', { ok: true, host: payload.host, addresses: [payload.host], preset: payload.preset, system: 'Linux qa', docker: true, curl: true, next_step: 'bootstrap' }, {})
  : post('/api/admin/nodes/preflight', payload))
export const fetchAdminBackups = () => (import.meta.env.DEV ? mockAdminSection('backups', { ok: true, backups: mockBackups }, { ok: true, backups: [] }) : get('/api/admin/backups'))
export const createAdminBackup = () => (import.meta.env.DEV ? mockAdminSection('backups', { ok: true, backups: (mockBackups = [{ name: `vpn_bot-${Date.now()}.db`, size_bytes: 7340032, created_at: new Date().toISOString() }, ...mockBackups]) }, { ok: true, backups: [] }) : post('/api/admin/backups'))
export const fetchAdminAudit = (limit = 100) => (import.meta.env.DEV ? mockAdminSection('audit', { ok: true, events: mockAuditEvents.slice(0, limit) }, { ok: true, events: [] }) : get(`/api/admin/audit?limit=${encodeURIComponent(limit)}`))
export const fetchAdminSupportThreads = () => (import.meta.env.DEV
  ? mockAdminSupportThreads()
  : get('/api/admin/support/threads'))
export const fetchAdminSupportThread = (threadId) => (import.meta.env.DEV
  ? mockAdminSupportThread(threadId)
  : get(`/api/admin/support/threads/${threadId}`))
export const sendAdminSupportReply = (threadId, body) => (import.meta.env.DEV
  ? mockAdminSupportReply(threadId, body)
  : post(`/api/admin/support/threads/${threadId}`, { body }))
export const fetchAdminCatalog = () => (import.meta.env.DEV ? mockAdminSection('catalog', { ok: true, profiles: mockCatalogProfiles }, { ok: true, profiles: [] }) : get('/api/admin/subscription-catalog'))
export const saveAdminCatalog = (profiles) => (import.meta.env.DEV ? mockAdminSection('catalog', { ok: true, profiles: (mockCatalogProfiles = profiles.map((item, sort_order) => ({ ...item, sort_order }))) }, { ok: true, profiles: [] }) : mutate('/api/admin/subscription-catalog', 'PATCH', { profiles }))
export const fetchAdminExpenses = () => (import.meta.env.DEV ? mockAdminSection('finance', { ok: true, expenses: mockExpenses, summary: { month_revenue_rub: 126400, month_expenses_rub: mockExpenses.reduce((sum, item) => sum + item.amount_rub, 0), month_net_rub: 124200 } }, { ok: true, expenses: [], summary: { month_revenue_rub: 0, month_expenses_rub: 0, month_net_rub: 0 } }) : get('/api/admin/expenses'))
export const createAdminExpense = (expense) => (import.meta.env.DEV ? mockAdminSection('finance', { ok: true, expenses: (mockExpenses = [{ id: Date.now(), ...expense }, ...mockExpenses]), summary: { month_revenue_rub: 126400, month_expenses_rub: mockExpenses.reduce((sum, item) => sum + Number(item.amount_rub || 0), 0), month_net_rub: 126400 - mockExpenses.reduce((sum, item) => sum + Number(item.amount_rub || 0), 0) } }, {}) : post('/api/admin/expenses', expense))
export const deleteAdminExpense = (expenseId) => (import.meta.env.DEV ? mockAdminSection('finance', { ok: true, expenses: (mockExpenses = mockExpenses.filter((item) => item.id !== expenseId)), summary: { month_revenue_rub: 126400, month_expenses_rub: mockExpenses.reduce((sum, item) => sum + Number(item.amount_rub || 0), 0), month_net_rub: 126400 - mockExpenses.reduce((sum, item) => sum + Number(item.amount_rub || 0), 0) } }, {}) : mutate(`/api/admin/expenses/${encodeURIComponent(expenseId)}`, 'DELETE'))
export const fetchAdminCampaigns = () => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, campaigns: mockCampaigns }, { ok: true, campaigns: [] }) : get('/api/admin/campaigns'))
export const createAdminCampaign = (payload) => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, campaigns: (mockCampaigns = [{ id: Date.now(), code: payload.code || `campaign_${Date.now()}`, link: `https://t.me/arcvpn1?start=ad_${payload.code || `campaign_${Date.now()}`}`, is_active: 1, arrivals: 0, paying_users: 0, paid_orders: 0, repeat_paid_orders: 0, revenue_cents: 0, conversion_percent: 0, ...payload }, ...mockCampaigns]) }, { ok: true, campaigns: [] }) : post('/api/admin/campaigns', payload))
export const updateAdminCampaign = (campaignId, payload) => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, campaigns: (mockCampaigns = mockCampaigns.map((item) => item.id === campaignId ? { ...item, ...payload } : item)) }, { ok: true, campaigns: [] }) : mutate(`/api/admin/campaigns/${encodeURIComponent(campaignId)}`, 'PATCH', payload))
export const fetchAdminPromocodes = () => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, promocodes: mockPromocodes }, { ok: true, promocodes: [] }) : get('/api/admin/promocodes'))
export const createAdminPromocode = (payload) => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, promocodes: (mockPromocodes = [{ id: Date.now(), code: payload.code, discount_type: payload.discount_type, discount_percent: payload.discount_type === 'percent' ? payload.discount_value : 0, discount_rub: payload.discount_type === 'fixed' ? payload.discount_value : 0, max_uses: payload.max_uses, used_count: 0, expires_at: new Date(Date.now() + payload.duration_days * 86400000).toISOString(), is_active: 1 }, ...mockPromocodes]) }, { ok: true, promocodes: [] }) : post('/api/admin/promocodes', payload))
export const updateAdminPromocode = (promocodeId, payload) => (import.meta.env.DEV ? mockAdminSection('growth', { ok: true, promocodes: (mockPromocodes = mockPromocodes.map((item) => item.id === promocodeId ? { ...item, ...payload } : item)) }, { ok: true, promocodes: [] }) : mutate(`/api/admin/promocodes/${encodeURIComponent(promocodeId)}`, 'PATCH', payload))
export const manageAdminSubscription = (telegramId, action) => (import.meta.env.DEV ? mockAdminSection('users', { ok: true, key_id: 10, expires_at: action.action === 'disable' ? new Date().toISOString() : '2026-09-20T12:00:00Z' }, {}) : mutate(`/api/admin/users/${encodeURIComponent(telegramId)}/subscription`, 'PATCH', action))
export const fetchAdminUserDetail = (telegramId) => (import.meta.env.DEV ? mockAdminSection('users', mockUserDetail(telegramId), {}) : get(`/api/admin/users/${encodeURIComponent(telegramId)}`))
export const fetchAdminUsers = ({ q = '', status = 'all', sort = 'new', usage = 'all', cohort = 'all', cursor = 0, limit = 40 } = {}) => {
  if (import.meta.env.DEV) {
    const filtered = mockUsers.filter((item) => (!q || `${item.first_name} ${item.username} ${item.telegram_id}`.toLocaleLowerCase('ru-RU').includes(q.toLocaleLowerCase('ru-RU'))) && (status === 'all' || (status === 'active' && item.active) || (status === 'inactive' && !item.active) || (status === 'online' && item.online_devices)) && (usage === 'all' || (usage === 'main' && item.main_used_bytes) || (usage === 'lte' && item.lte_used_bytes))).sort((a,b)=>sort==='main_usage'?b.main_used_bytes-a.main_used_bytes:sort==='lte_usage'?b.lte_used_bytes-a.lte_used_bytes:0)
    return mockAdminSection('users', { ok: true, users: filtered.slice(cursor, cursor + limit), total: filtered.length, cursor, next_cursor: null, presence_source: 'remnawave' }, { ok: true, users: [], total: 0, cursor: 0, next_cursor: null, presence_source: 'remnawave' })
  }
  const params = new URLSearchParams({ q, status, sort, usage, cohort, cursor: String(cursor), limit: String(limit) })
  return get(`/api/admin/users?${params.toString()}`)
}
export const fetchTariffs = () => (import.meta.env.DEV ? mock('tariffs') : get('/api/tariffs'))
export const fetchReferral = () => (import.meta.env.DEV ? mock('referral') : get('/api/referral'))
export const fetchAccount = () => (import.meta.env.DEV ? mock('account') : get('/api/account'))
export const fetchPublicConfig = () => (import.meta.env.DEV
  ? Promise.resolve({ ok: true, bot_url: 'https://t.me/arcvpn_bot' })
  : get('/api/public/config'))
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
export const createSbpPayment = (tariffId, devices = 2, lteGb = 0, promocode = '', autoRenew = true) =>
  post('/api/payments/sbp', { tariff_id: tariffId, devices, lte_gb: lteGb, promocode, auto_renew: autoRenew })
export const createCardPayment = (tariffId, devices = 2, lteGb = 0, promocode = '', autoRenew = true) =>
  post('/api/payments/card', { tariff_id: tariffId, devices, lte_gb: lteGb, promocode, auto_renew: autoRenew })
export const createEmailTrialPayment = (method = 'sbp') => post('/api/payments/email-trial', { method })
export const validatePromocode = async (tariffId, code) => {
  if (!import.meta.env.DEV) return post('/api/promocodes/validate', { tariff_id: tariffId, code })
  const normalized = code.trim().toUpperCase()
  if (normalized !== 'START10') {
    const error = new Error('promocode_not_found')
    error.reason = 'promocode_not_found'
    throw error
  }
  const catalog = await mock('tariffs')
  const base = Number(catalog.tariffs.find((tariff) => tariff.id === tariffId)?.price_rub || 0)
  const discount = Math.floor(base * 0.1)
  return { ok: true, code: normalized, base_amount_rub: base, discount_type: 'percent', discount_value: 10, discount_label: '10%', discount_rub: discount, final_amount_rub: base - discount }
}
export const fetchSbpPayment = (orderId) =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, status: 'succeeded', applied: true })
    : get(`/api/payments/sbp/${encodeURIComponent(orderId)}`))
export const fetchRecurringPayment = () =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, enabled: false, method: null, provider_ready: false })
    : get('/api/billing/recurring'))
export const disableRecurringPayment = () =>
  (import.meta.env.DEV
    ? Promise.resolve({ ok: true, disabled: true })
    : mutate('/api/billing/recurring', 'DELETE'))
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
