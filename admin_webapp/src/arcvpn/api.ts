type Json = Record<string, any>;
const GB = 1024 ** 3;
let overviewCache: Promise<Json> | null = null;
const detailCache = new Map<number, Promise<Json>>();
let referralNetworkCache: Promise<Json> | null = null;

const mockOverview: Json = {
  generated_at: new Date().toISOString(),
  users: { total: 779, day: 11, week: 74, month: 286 },
  subscriptions: { total: 779, active: 641, expired: 138, trial: 23, paid: 618 },
  financials: { lifetime_rub: 486320, month_rub: 126400, paying_users: 412 },
  business: {
    payments: {
      day: { orders: 31, revenue_rub: 4875 },
      month: { orders: 812, revenue_rub: 126400 },
    },
    revenue_series: Array.from({ length: 14 }, (_, i) => ({
      day: `2026-09-${String(i + 1).padStart(2, '0')}`,
      revenue_rub: 4200 + ((i * 1741) % 7200),
      orders: 19 + (i % 17),
    })),
  },
  system: { uptime_seconds: 1281600, disk_used_pct: 43 },
  remnawave: {
    healthy: true,
    users: 779,
    online_users: Array.from({ length: 93 }),
    nodes: [
      {
        uuid: 'de',
        name: 'ArcVPN Germany DHost',
        address: 'de.arc.test',
        connected: true,
        users_online: 58,
        xray_uptime_seconds: 1281600,
        traffic_used_gb: 2180,
        country_code: 'DE',
      },
      {
        uuid: 'nl',
        name: 'ArcVPN Netherlands DHost',
        address: 'nl.arc.test',
        connected: true,
        users_online: 35,
        xray_uptime_seconds: 604800,
        traffic_used_gb: 1430,
        country_code: 'NL',
      },
      {
        uuid: 'ee',
        name: 'ArcVPN Estonia 1chost',
        address: 'ee.arc.test',
        connected: true,
        users_online: 12,
        xray_uptime_seconds: 431000,
        traffic_used_gb: 918,
        country_code: 'EE',
      },
    ],
    squads: [
      {
        uuid: 'main-squad',
        name: 'ArcVPN Main',
        members_count: 641,
        inbounds_count: 4,
        inbounds: [{ tag: 'VLESS Reality' }, { tag: 'AutoSelect' }],
      },
      {
        uuid: 'lte-squad',
        name: 'ArcVPN LTE',
        members_count: 188,
        inbounds_count: 2,
        inbounds: [{ tag: 'LTE XHTTP NL' }, { tag: 'LTE XHTTP EE' }],
      },
    ],
  },
  recent_payments: [
    {
      order_id: 'demo-1',
      telegram_id: 700001,
      username: 'alex',
      first_name: 'Алексей',
      tariff_name: 'Стандарт · 3 месяца',
      payment_type: 'СБП',
      paid_at: '2026-09-14T12:32:00Z',
      display_amount_rub: 399,
      status: 'paid',
    },
    {
      order_id: 'demo-2',
      telegram_id: 700002,
      username: 'marina',
      first_name: 'Марина',
      tariff_name: 'Стандарт · 1 месяц',
      payment_type: 'Карта',
      paid_at: '2026-09-14T10:04:00Z',
      display_amount_rub: 145,
      status: 'paid',
    },
  ],
  referrals: {
    total_invited: 932,
    converted: 294,
    leaders: [
      {
        telegram_id: 700001,
        username: 'alex',
        first_name: 'Алексей',
        invited_count: 41,
        converted_count: 17,
        earned_days: 170,
      },
    ],
  },
};

const mockUsers = [
  {
    telegram_id: 700001,
    username: 'alex',
    first_name: 'Алексей',
    created_at: '2026-07-19T11:30:00Z',
    active: 1,
    online_devices: 1,
    online_node: 'Germany DHost',
    expires_at: '2026-10-20T12:00:00Z',
    main_used_bytes: 184 * GB,
    lte_used_bytes: 29 * GB,
    lte_quota_gb: 50,
    paid_rub: 544,
  },
  {
    telegram_id: 700002,
    username: 'marina',
    first_name: 'Марина',
    created_at: '2026-08-08T08:00:00Z',
    active: 1,
    online_devices: 0,
    expires_at: '2026-09-28T12:00:00Z',
    main_used_bytes: 88 * GB,
    lte_used_bytes: 6 * GB,
    lte_quota_gb: 20,
    paid_rub: 750,
  },
  {
    telegram_id: 700003,
    username: 'north',
    first_name: 'Никита',
    created_at: '2026-09-12T12:00:00Z',
    active: 0,
    online_devices: 0,
    expires_at: '2026-09-12T12:00:00Z',
    main_used_bytes: 4 * GB,
    lte_used_bytes: 0,
    lte_quota_gb: 5,
    paid_rub: 0,
  },
];

const mockSupport = {
  threads: [
    {
      id: 91,
      status: 'open',
      updated_at: '2026-09-13T17:40:00Z',
      telegram_id: 700001,
      username: 'alex',
      first_name: 'Алексей',
      last_message: 'Не подключается на iPhone',
      unread: 1,
    },
  ],
};

const mockDetail = (telegramId: number): Json => ({
  user: {
    telegram_id: telegramId,
    username: 'alex',
    first_name: 'Алексей',
    created_at: '2026-07-19T11:30:00Z',
    device_limit: 2,
    lte_quota_gb: 50,
    lte_used_bytes: 29 * GB,
    balance_rub: 125,
    online_node: 'ArcVPN Estonia 1chost',
    online_at: '2026-09-21T13:40:00Z',
  },
  subscriptions: [
    {
      id: 10,
      tariff_name: 'Стандарт · 3 месяца',
      created_at: '2026-07-19T11:30:00Z',
      expires_at: '2026-10-20T12:00:00Z',
      traffic_used: 184 * GB,
      traffic_limit: 300 * GB,
      online_devices: 1,
      active: 1,
      is_trial: telegramId === 700003 ? 1 : 0,
      server_name: 'ArcVPN Estonia 1chost',
      last_online_at: '2026-09-21T13:40:00Z',
    },
  ],
  payments: [
    {
      order_id: 'p-1',
      payment_type: 'СБП',
      status: 'paid',
      period_days: 90,
      paid_at: '2026-09-14T12:32:00Z',
      tariff_name: 'Стандарт · 3 месяца',
      amount_rub: 399,
    },
    {
      order_id: 'p-2',
      payment_type: 'Карта',
      status: 'paid',
      period_days: 30,
      paid_at: '2026-08-14T09:00:00Z',
      tariff_name: 'Стандарт',
      amount_rub: 145,
    },
  ],
  devices: [
    {
      id: 1,
      display_name: 'iPhone',
      platform: 'iOS',
      model: 'iPhone 15',
      imported_at: '2026-08-01T09:00:00Z',
      last_seen_at: '2026-09-14T12:20:00Z',
    },
    {
      id: 2,
      display_name: 'Ноутбук',
      platform: 'Windows',
      model: 'Windows',
      imported_at: '2026-08-10T09:00:00Z',
      last_seen_at: '2026-09-13T18:15:00Z',
    },
  ],
  lifecycle_answers: [
    {
      event_key: 'trial_day1_rating',
      answer: 'service: Не открывался YouTube',
      sent_at: '2026-09-19T12:00:00Z',
      answered_at: '2026-09-19T12:05:00Z',
    },
    {
      event_key: 'expired_winback',
      answer: 'expensive',
      sent_at: '2026-09-21T12:00:00Z',
      answered_at: '2026-09-21T12:03:00Z',
    },
  ],
  referrals: {
    invited_count: 4,
    paid_count: 2,
    earned_days: 40,
    friends: [
      {
        telegram_id: 710001,
        first_name: 'Ирина',
        username: 'irina',
        created_at: '2026-09-10T09:00:00Z',
        has_paid: 1,
        reward_days: 20,
      },
      {
        telegram_id: 710002,
        first_name: 'Олег',
        username: 'oleg',
        created_at: '2026-09-08T15:00:00Z',
        has_paid: 1,
        reward_days: 20,
      },
      {
        telegram_id: 710003,
        first_name: 'Анна',
        username: 'anna',
        created_at: '2026-09-07T18:00:00Z',
        has_paid: 0,
        reward_days: 0,
      },
      {
        telegram_id: 710004,
        first_name: 'Гость',
        username: null,
        created_at: '2026-09-04T08:00:00Z',
        has_paid: 0,
        reward_days: 0,
      },
    ],
  },
  timeline: [
    {
      kind: 'payment',
      at: '2026-09-14T12:32:00Z',
      title: 'Оплата подтверждена',
      detail: 'Стандарт · 3 месяца',
    },
    {
      kind: 'device',
      at: '2026-09-13T18:15:00Z',
      title: 'Устройство подключено',
      detail: 'Ноутбук · Windows',
    },
    {
      kind: 'subscription',
      at: '2026-07-19T11:30:00Z',
      title: 'Подписка создана',
      detail: 'Стандарт',
    },
  ],
});

export async function getJson(path: string, init?: RequestInit): Promise<Json> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) throw new Error(`ArcVPN API ${response.status}`);
  return response.json();
}

export const access = (): Promise<Json> =>
  import.meta.env.DEV
    ? Promise.resolve({ ok: true, role: 'owner', permissions: ['*'] })
    : getJson('/api/admin/access');
export const login = (password: string): Promise<Json> =>
  getJson('/api/admin/login', { method: 'POST', body: JSON.stringify({ password }) });
export function getOverview(): Promise<Json> {
  if (!overviewCache)
    overviewCache = import.meta.env.DEV
      ? Promise.resolve(mockOverview)
      : getJson('/api/admin/overview');
  return overviewCache;
}
export async function getUsers(params: Record<string, unknown> = {}): Promise<Json> {
  if (import.meta.env.DEV) {
    const q = String(params.search || '').toLowerCase();
    const status = String(params.status || '');
    const sortBy = String(params.sort_by || 'created_at');
    const users = mockUsers
      .filter(
        (item) =>
          (!q ||
            `${item.first_name} ${item.username} ${item.telegram_id}`.toLowerCase().includes(q)) &&
          (status !== 'online' || item.online_devices > 0) &&
          (status !== 'active' || item.active) &&
          (status !== 'inactive' || !item.active),
      )
      .sort((a, b) => {
        if (sortBy === 'lte_traffic') return b.lte_used_bytes - a.lte_used_bytes;
        if (sortBy === 'main_traffic' || sortBy === 'traffic')
          return b.main_used_bytes - a.main_used_bytes;
        if (sortBy === 'last_activity') return b.online_devices - a.online_devices;
        return String(b.created_at).localeCompare(String(a.created_at));
      });
    return {
      users,
      total: users.length,
      cursor: Number(params.offset || 0),
      limit: Number(params.limit || 20),
    };
  }
  const query = new URLSearchParams({
    cursor: String(params.offset || 0),
    limit: String(params.limit || 20),
  });
  if (params.search) query.set('q', String(params.search));
  if (['active', 'inactive', 'online'].includes(String(params.status || ''))) {
    query.set('status', String(params.status));
  }
  const sortMap: Record<string, string> = {
    created_at: 'new',
    total_spent: 'top',
    subscription_end_date: 'expiry',
    last_activity: 'online',
    traffic: 'main_usage',
    main_traffic: 'main_usage',
    lte_traffic: 'lte_usage',
  };
  query.set('sort', sortMap[String(params.sort_by || '')] || 'new');
  return getJson(`/api/admin/users?${query}`);
}
export function getUser(telegramId: number): Promise<Json> {
  if (!detailCache.has(telegramId))
    detailCache.set(
      telegramId,
      import.meta.env.DEV
        ? Promise.resolve(mockDetail(telegramId))
        : getJson(`/api/admin/users/${encodeURIComponent(telegramId)}`),
    );
  return detailCache.get(telegramId)!;
}
export const asGb = (bytes: unknown) => Number(bytes || 0) / GB;
export const getSupportThreads = (): Promise<Json> =>
  import.meta.env.DEV ? Promise.resolve(mockSupport) : getJson('/api/admin/support/threads');

export function getReferralNetwork(): Promise<Json> {
  if (!referralNetworkCache) {
    const demoUsers = mockUsers.map((user, index) => ({
      id: index + 1,
      tg_id: user.telegram_id,
      username: user.username,
      email: null,
      display_name: user.first_name || user.username,
      is_partner: false,
      referrer_id: index === 0 ? null : 1,
      campaign_id: index === 1 ? 1 : null,
      direct_referrals: index === 0 ? mockUsers.length - 1 : 0,
      total_branch_users: index === 0 ? mockUsers.length - 1 : 0,
      branch_revenue_kopeks: 0,
      personal_revenue_kopeks: 0,
      personal_spent_kopeks: user.paid_rub * 100,
      subscription_name: 'ArcVPN',
      subscription_end: user.expires_at,
      subscription_status:
        user.paid_rub > 0
          ? user.active
            ? 'paid_active'
            : 'paid_expired'
          : user.active
            ? 'trial_active'
            : 'trial_expired',
      registered_at: user.created_at,
    }));
    referralNetworkCache = import.meta.env.DEV
      ? Promise.resolve({
          users: demoUsers,
          campaigns: [
            {
              id: 1,
              name: 'Telegram September',
              start_parameter: 'ad_telegram_sep',
              is_active: true,
              direct_users: 1,
              total_network_users: 1,
              total_revenue_kopeks: 75000,
              conversion_rate: 100,
              avg_check_kopeks: 75000,
              top_referrers: [],
            },
          ],
          edges: [
            ...demoUsers
              .slice(1)
              .map((user) => ({ source: 'user_1', target: `user_${user.id}`, type: 'referral' })),
            { source: 'campaign_1', target: 'user_2', type: 'campaign' },
          ],
          total_users: demoUsers.length,
          total_referrers: 1,
          total_campaigns: 1,
          total_earnings_kopeks: 0,
          total_subscription_revenue_kopeks: demoUsers.reduce(
            (sum, user) => sum + user.personal_spent_kopeks,
            0,
          ),
        })
      : getJson('/api/admin/referral-network');
  }
  return referralNetworkCache;
}

export function adminModuleJson(path: string, mock: Json): Promise<Json> {
  return import.meta.env.DEV ? Promise.resolve(mock) : getJson(path);
}

export const getSupportThread = (threadId: number): Promise<Json> =>
  import.meta.env.DEV
    ? Promise.resolve({
        thread: mockSupport.threads.find((item) => item.id === threadId),
        messages: [
          {
            id: 1,
            sender: 'user',
            body: 'Не подключается на iPhone',
            created_at: '2026-09-13T17:40:00Z',
            read_at: null,
          },
        ],
      })
    : getJson(`/api/admin/support/threads/${threadId}`);

export const replySupportThread = (threadId: number, body: string): Promise<Json> =>
  getJson(`/api/admin/support/threads/${threadId}`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });

export function userListItem(row: Json): Json {
  const active = Boolean(row.active);
  const isTrial = Boolean(row.active_trial);
  return {
    id: Number(row.telegram_id),
    telegram_id: Number(row.telegram_id),
    username: row.username || null,
    first_name: row.first_name || null,
    last_name: null,
    full_name: row.first_name || row.username || `ID ${row.telegram_id}`,
    status: 'active',
    balance_kopeks: 0,
    balance_rubles: 0,
    created_at: row.created_at,
    last_activity: row.last_online_at || null,
    has_subscription: Boolean(row.expires_at),
    subscription_status: isTrial ? 'trial' : active ? 'active' : 'expired',
    subscription_is_trial: isTrial,
    subscription_end_date: row.expires_at || null,
    tariff_id: null,
    tariff_name: null,
    traffic_used_gb: asGb(row.main_used_bytes),
    traffic_limit_gb: 0,
    device_limit: 2,
    days_remaining:
      active && row.expires_at
        ? Math.max(0, Math.ceil((new Date(row.expires_at).getTime() - Date.now()) / 86400000))
        : 0,
    promo_group_id: null,
    promo_group_name: null,
    total_spent_kopeks: Math.round(Number(row.paid_rub || 0) * 100),
    purchase_count: Number(row.purchase_count || 0),
    has_restrictions: false,
    restriction_topup: false,
    restriction_subscription: false,
    online_devices: Number(row.online_devices || 0),
    online_node: row.online_node || null,
    main_used_gb: asGb(row.main_used_bytes),
    lte_used_gb: asGb(row.lte_used_bytes),
    lte_quota_gb: Number(row.lte_quota_gb || 0),
  };
}

export function dashboardStats(data: Json): Json {
  const nodes = (data.remnawave?.nodes || []).map((node: Json) => ({
    uuid: String(node.uuid || node.address),
    name: node.name,
    address: node.address,
    is_connected: Boolean(node.connected),
    is_disabled: Boolean(node.disabled),
    users_online: Number(node.users_online || 0),
    traffic_used_bytes: Number(node.traffic_used_gb || 0) * GB,
    xray_uptime: Number(node.xray_uptime_seconds || 0),
    is_xray_running: Boolean(node.connected),
    country_code: node.country_code || null,
    system: { stats: { loadAvg: [node.load_1m], memoryUsed: node.memory_used_pct } },
  }));
  const active = Number(data.subscriptions?.active || 0);
  const trial = Number(data.subscriptions?.trial || 0);
  const total = Number(data.subscriptions?.total || active);
  const today = Number(data.business?.payments?.day?.revenue_rub || 0);
  const month = Number(
    data.financials?.month_rub || data.business?.payments?.month?.revenue_rub || 0,
  );
  const lifetime = Number(data.financials?.lifetime_rub || 0);
  return {
    nodes: {
      total: nodes.length,
      online: nodes.filter((n: Json) => n.is_connected && !n.is_disabled).length,
      offline: nodes.filter((n: Json) => !n.is_connected && !n.is_disabled).length,
      disabled: nodes.filter((n: Json) => n.is_disabled).length,
      total_users_online: nodes.reduce((sum: number, n: Json) => sum + n.users_online, 0),
      nodes,
    },
    subscriptions: {
      total,
      active,
      trial,
      paid: Number(data.subscriptions?.paid ?? Math.max(0, active - trial)),
      expired: Number(data.subscriptions?.expired || Math.max(0, total - active)),
      purchased_today: Number(data.business?.payments?.day?.orders || 0),
      purchased_week: Number(data.business?.payments?.week?.orders || 0),
      purchased_month: Number(data.business?.payments?.month?.orders || 0),
      trial_to_paid_conversion: 0,
    },
    financial: {
      income_today_kopeks: today * 100,
      income_today_rubles: today,
      income_month_kopeks: month * 100,
      income_month_rubles: month,
      income_total_kopeks: lifetime * 100,
      income_total_rubles: lifetime,
      subscription_income_kopeks: lifetime * 100,
      subscription_income_rubles: lifetime,
    },
    servers: {
      total_servers: nodes.length,
      available_servers: nodes.filter((n: Json) => n.is_connected).length,
      servers_with_connections: nodes.filter((n: Json) => n.users_online > 0).length,
      total_revenue_kopeks: lifetime * 100,
      total_revenue_rubles: lifetime,
    },
    revenue_chart: (data.business?.revenue_series || []).map((item: Json) => ({
      date: item.day,
      amount_kopeks: Number(item.revenue_rub || 0) * 100,
      amount_rubles: Number(item.revenue_rub || 0),
    })),
  };
}

export async function userDetail(telegramId: number): Promise<Json> {
  const data = await getUser(telegramId);
  const user = data.user || {};
  const subscriptions = (data.subscriptions || []).map((sub: Json) => ({
    id: Number(sub.id),
    status: sub.is_trial ? 'trial' : sub.active ? 'active' : 'expired',
    is_trial: Boolean(sub.is_trial),
    start_date: sub.created_at || null,
    end_date: sub.expires_at || null,
    traffic_limit_gb: asGb(sub.traffic_limit),
    traffic_used_gb: asGb(sub.traffic_used),
    device_limit: Number(user.device_limit || 2),
    tariff_id: null,
    tariff_name: sub.tariff_name || sub.custom_name || 'Подписка',
    autopay_enabled: false,
    sbp_recurring_status: null,
    sbp_recurring_id: null,
    is_active: Boolean(sub.active),
    days_remaining: sub.expires_at
      ? Math.max(0, Math.ceil((new Date(sub.expires_at).getTime() - Date.now()) / 86400000))
      : 0,
    purchased_traffic_gb: 0,
    traffic_purchases: [],
  }));
  const payments = data.payments || [];
  const commercialPayments = payments.filter(
    (payment: Json) =>
      payment.payment_type !== 'trial' &&
      payment.operation_type !== 'trial_start' &&
      payment.offer_code !== 'email_paid_trial',
  );
  const referral = data.referrals || { invited_count: 0, friends: [] };
  return {
    id: telegramId,
    telegram_id: telegramId,
    username: user.username || null,
    first_name: user.first_name || null,
    last_name: null,
    full_name: user.first_name || user.username || `ID ${telegramId}`,
    status: 'active',
    language: 'ru',
    balance_kopeks: Math.round(Number(user.balance_rub || 0) * 100),
    balance_rubles: Number(user.balance_rub || 0),
    email: null,
    email_verified: false,
    created_at: user.created_at,
    updated_at: null,
    last_activity: null,
    cabinet_last_login: null,
    subscription: subscriptions[0] || null,
    subscriptions,
    promo_group: null,
    referral: {
      referral_code: '',
      referrals_count: Number(referral.invited_count || 0),
      paid_referrals: Number(referral.paid_count || 0),
      earned_days: Number(referral.earned_days || 0),
      total_earnings_kopeks: 0,
      commission_percent: null,
      referred_by_id: null,
      referred_by_username: null,
    },
    total_spent_kopeks: Math.round(
      commercialPayments.reduce((sum: number, p: Json) => sum + Number(p.amount_rub || 0), 0) * 100,
    ),
    purchase_count: commercialPayments.length,
    used_promocodes: 0,
    has_had_paid_subscription: commercialPayments.some((payment: Json) =>
      ['paid', 'succeeded'].includes(String(payment.status || '').toLowerCase()),
    ),
    lifetime_used_traffic_bytes: Number(
      data.subscriptions?.reduce(
        (sum: number, sub: Json) => sum + Number(sub.traffic_used || 0),
        0,
      ) || 0,
    ),
    campaign_name: null,
    campaign_id: null,
    restriction_topup: false,
    restriction_subscription: false,
    restriction_reason: null,
    promo_offer_discount_percent: 0,
    promo_offer_discount_source: null,
    promo_offer_discount_expires_at: null,
    recent_transactions: payments.map((p: Json, index: number) => ({
      id: index + 1,
      type: 'payment',
      amount_kopeks: Math.round(Number(p.amount_rub || 0) * 100),
      amount_rubles: Number(p.amount_rub || 0),
      description: p.tariff_name || null,
      payment_method: p.payment_type || null,
      is_completed: ['paid', 'succeeded'].includes(p.status),
      created_at: p.paid_at,
    })),
    lifecycle_answers: data.lifecycle_answers || [],
    remnawave_id: null,
  };
}

export async function referralUsers(telegramId: number): Promise<Json> {
  const data = await getUser(telegramId);
  const users = (data.referrals?.friends || []).map((friend: Json) =>
    userListItem({
      ...friend,
      active: friend.has_paid,
      paid_rub: 0,
      purchase_count: friend.has_paid ? 1 : 0,
    }),
  );
  return { users, total: users.length, offset: 0, limit: 100 };
}

export const getMarketing = async (): Promise<Json> => {
  if (import.meta.env.DEV) {
    return {
      campaigns: [
        {
          id: 1,
          name: 'Telegram September',
          code: 'telegram_sep',
          link: 'https://t.me/arcvpnnbot?start=ad_telegram_sep',
          is_active: 1,
          arrivals: 8,
          paying_users: 2,
          entry_bonus_days: 3,
          payment_bonus_days: 5,
        },
      ],
      promocodes: [
        {
          id: 1,
          code: 'START20',
          discount_type: 'percent',
          discount_percent: 20,
          discount_rub: 0,
          max_uses: 100,
          used_count: 12,
          expires_at: '2026-10-21T00:00:00',
          is_active: 1,
        },
      ],
    };
  }
  const [campaigns, promocodes] = await Promise.all([
    getJson('/api/admin/campaigns'),
    getJson('/api/admin/promocodes'),
  ]);
  return { campaigns: campaigns.campaigns || [], promocodes: promocodes.promocodes || [] };
};

export const createMarketingCampaign = (payload: Json): Promise<Json> =>
  getJson('/api/admin/campaigns', { method: 'POST', body: JSON.stringify(payload) });

export const updateMarketingCampaign = (id: number, payload: Json): Promise<Json> =>
  getJson(`/api/admin/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });

export const createMarketingPromocode = (payload: Json): Promise<Json> =>
  getJson('/api/admin/promocodes', { method: 'POST', body: JSON.stringify(payload) });

export const updateMarketingPromocode = (id: number, payload: Json): Promise<Json> =>
  getJson(`/api/admin/promocodes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
export async function userDevices(telegramId: number): Promise<Json> {
  const data = await getUser(telegramId);
  return {
    devices: (data.devices || []).map((device: Json) => ({
      hwid: String(device.id),
      platform: device.platform || '',
      device_model: device.model || device.display_name || '',
      created_at: device.imported_at || null,
      local_name: device.display_name || null,
    })),
    total: (data.devices || []).length,
    device_limit: Number(data.user?.device_limit || 2),
  };
}
export async function userActivity(telegramId: number): Promise<Json> {
  const data = await getUser(telegramId);
  const items = (data.timeline || []).map((item: Json, index: number) => ({
    id: index + 1,
    type: item.kind || 'system',
    subtype: null,
    source: 'arcvpn',
    title: item.title,
    amount_kopeks: null,
    timestamp: item.at,
    meta: { detail: item.detail },
  }));
  return { items, total: items.length, offset: 0, limit: 25 };
}
export async function syncStatus(telegramId: number): Promise<Json> {
  const data = await getUser(telegramId);
  const sub = data.subscriptions?.[0];
  return {
    user_id: telegramId,
    telegram_id: telegramId,
    remnawave_id: null,
    subscription_id: sub?.id || null,
    subscription_tariff_name: sub?.tariff_name || null,
    last_sync: null,
    bot_subscription_status: sub?.active ? 'active' : 'expired',
    bot_subscription_end_date: sub?.expires_at || null,
    bot_traffic_limit_gb: asGb(sub?.traffic_limit),
    bot_traffic_used_gb: asGb(sub?.traffic_used),
    bot_device_limit: Number(data.user?.device_limit || 2),
    bot_squads: [],
    panel_found: true,
    panel_status: sub?.active ? 'ACTIVE' : 'DISABLED',
    panel_expire_at: sub?.expires_at || null,
    panel_traffic_limit_gb: asGb(sub?.traffic_limit),
    panel_traffic_used_gb: asGb(sub?.traffic_used),
    panel_device_limit: Number(data.user?.device_limit || 2),
    panel_squads: [],
    has_differences: false,
    differences: [],
  };
}
export async function usersStats(): Promise<Json> {
  const [overview, listing] = await Promise.all([getOverview(), getUsers({ limit: 100 })]);
  return {
    total_users: Number(overview.users?.total || listing.total || 0),
    active_users: listing.users.filter((u: Json) => u.active).length,
    blocked_users: 0,
    deleted_users: 0,
    new_today: Number(overview.users?.day || 0),
    new_week: Number(overview.users?.week || 0),
    new_month: Number(overview.users?.month || 0),
    users_with_subscription: Number(overview.subscriptions?.total || 0),
    users_with_active_subscription: Number(overview.subscriptions?.active || 0),
    users_with_trial: 0,
    users_with_expired_subscription: Number(overview.subscriptions?.expired || 0),
    total_balance_kopeks: 0,
    total_balance_rubles: 0,
    avg_balance_kopeks: 0,
    active_today: Number(overview.remnawave?.online_users?.length || 0),
    active_week: 0,
    active_month: 0,
  };
}
