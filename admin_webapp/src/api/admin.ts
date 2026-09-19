import apiClient from './client';
import {
  dashboardStats as adaptDashboard,
  getOverview,
  getSupportThread,
  getSupportThreads,
  replySupportThread,
  getJson,
} from '@/arcvpn/api';

export interface AdminTicketUser {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
}

export interface AdminTicketMediaItem {
  type: 'photo' | 'video' | 'document';
  file_id: string;
  caption?: string | null;
}

export interface AdminTicketMessage {
  id: number;
  message_text: string;
  is_from_admin: boolean;
  has_media: boolean;
  media_type: string | null;
  media_file_id: string | null;
  media_caption: string | null;
  media_items?: AdminTicketMediaItem[] | null;
  created_at: string;
}

export interface AdminTicket {
  id: number;
  title: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  messages_count: number;
  user: AdminTicketUser | null;
  last_message: AdminTicketMessage | null;
}

export interface AdminTicketDetail {
  id: number;
  title: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  is_reply_blocked: boolean;
  user: AdminTicketUser | null;
  messages: AdminTicketMessage[];
}

export interface AdminTicketStats {
  total: number;
  open: number;
  pending: number;
  answered: number;
  closed: number;
}

export interface TicketSettings {
  sla_enabled: boolean;
  sla_minutes: number;
  sla_check_interval_seconds: number;
  sla_reminder_cooldown_minutes: number;
  support_system_mode: string; // tickets, contact, both
  cabinet_user_notifications_enabled: boolean;
  cabinet_admin_notifications_enabled: boolean;
  /** Поля, закреплённые в .env: из кабинета их не изменить. */
  env_locked?: string[];
}

export interface TicketSettingsUpdate {
  sla_enabled?: boolean;
  sla_minutes?: number;
  sla_check_interval_seconds?: number;
  sla_reminder_cooldown_minutes?: number;
  support_system_mode?: string;
  cabinet_user_notifications_enabled?: boolean;
  cabinet_admin_notifications_enabled?: boolean;
}

export interface AdminTicketListResponse {
  items: AdminTicket[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export const adminApi = {
  // Check if current user is admin
  checkIsAdmin: async (): Promise<{ is_admin: boolean }> => {
    const response = await apiClient.get('/cabinet/auth/me/is-admin');
    return response.data;
  },

  // Get ticket statistics
  getTicketStats: async (): Promise<AdminTicketStats> => {
    const response = await getSupportThreads();
    const rows = response.threads || [];
    const count = (status: string) => rows.filter((item: Record<string, unknown>) => String(item.status || 'open') === status).length;
    return { total: rows.length, open: count('open'), pending: count('pending'), answered: count('answered'), closed: count('closed') };
  },

  // Get all tickets
  getTickets: async (
    params: {
      page?: number;
      per_page?: number;
      status?: string;
      priority?: string;
      user_id?: number;
    } = {},
  ): Promise<AdminTicketListResponse> => {
    const response = await getSupportThreads();
    const rows = (response.threads || []).filter(
      (item: Record<string, unknown>) =>
        !params.user_id || Number(item.telegram_id) === Number(params.user_id),
    );
    const items = rows.map((item: Record<string, unknown>) => ({
      id: Number(item.id),
      title: 'Поддержка',
      status: String(item.status || 'open'),
      priority: 'normal',
      created_at: String(item.updated_at || ''),
      updated_at: String(item.updated_at || ''),
      closed_at: item.status === 'closed' ? String(item.updated_at || '') : null,
      messages_count: Number(item.unread || 0),
      user: {
        id: Number(item.telegram_id),
        telegram_id: Number(item.telegram_id),
        username: item.username ? String(item.username) : null,
        first_name: item.first_name ? String(item.first_name) : null,
        last_name: null,
      },
      last_message: item.last_message
        ? {
            id: 0,
            message_text: String(item.last_message),
            is_from_admin: false,
            has_media: false,
            media_type: null,
            media_file_id: null,
            media_caption: null,
            created_at: String(item.updated_at || ''),
          }
        : null,
    }));
    return { items, total: items.length, page: 1, per_page: params.per_page || 50, pages: 1 };
  },

  // Get single ticket with messages
  getTicket: async (ticketId: number): Promise<AdminTicketDetail> => {
    const response = await getSupportThread(ticketId);
    const thread = response.thread || {};
    return {
      id: Number(thread.id || ticketId),
      title: 'Поддержка',
      status: String(thread.status || 'open'),
      priority: 'normal',
      created_at: String(thread.created_at || thread.updated_at || ''),
      updated_at: String(thread.updated_at || ''),
      closed_at: thread.status === 'closed' ? String(thread.updated_at || '') : null,
      is_reply_blocked: false,
      user: thread.telegram_id
        ? {
            id: Number(thread.telegram_id),
            telegram_id: Number(thread.telegram_id),
            username: thread.username || null,
            first_name: thread.first_name || null,
            last_name: null,
          }
        : null,
      messages: (response.messages || []).map((message: Record<string, unknown>) => ({
        id: Number(message.id),
        message_text: String(message.body || ''),
        is_from_admin: message.sender === 'admin',
        has_media: false,
        media_type: null,
        media_file_id: null,
        media_caption: null,
        created_at: String(message.created_at || ''),
      })),
    };
  },

  // Reply to ticket
  replyToTicket: async (
    ticketId: number,
    message: string,
    media?: {
      media_type?: string;
      media_file_id?: string;
      media_caption?: string;
      media_items?: AdminTicketMediaItem[];
    },
  ): Promise<AdminTicketMessage> => {
    void media;
    const response = await replySupportThread(ticketId, message);
    const item = response.message || {};
    return {
      id: Number(item.id || 0),
      message_text: String(item.body || message),
      is_from_admin: true,
      has_media: false,
      media_type: null,
      media_file_id: null,
      media_caption: null,
      created_at: String(item.created_at || new Date().toISOString()),
    };
  },

  // Update ticket status
  updateTicketStatus: async (ticketId: number, status: string): Promise<AdminTicketDetail> => {
    await getJson(`/api/admin/support/threads/${ticketId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) });
    return adminApi.getTicket(ticketId);
  },

  // Update ticket priority
  updateTicketPriority: async (ticketId: number, priority: string): Promise<AdminTicketDetail> => {
    const response = await apiClient.post(`/cabinet/admin/tickets/${ticketId}/priority`, {
      priority,
    });
    return response.data;
  },

  // Get ticket settings
  getTicketSettings: async (): Promise<TicketSettings> => {
    const response = await apiClient.get('/cabinet/admin/tickets/settings');
    return response.data;
  },

  // Update ticket settings
  updateTicketSettings: async (settings: TicketSettingsUpdate): Promise<TicketSettings> => {
    const response = await apiClient.patch('/cabinet/admin/tickets/settings', settings);
    return response.data;
  },
};

export interface NodeStatus {
  uuid: string;
  name: string;
  address: string;
  is_connected: boolean;
  is_disabled: boolean;
  users_online: number;
  traffic_used_bytes?: number;
  last_status_message?: string;
  xray_uptime: number;
  is_xray_running?: boolean;
  versions?: { xray: string; node: string } | null;
  system?: Record<string, unknown> | null;
  country_code?: string;
}

export interface NodesOverview {
  total: number;
  online: number;
  offline: number;
  disabled: number;
  total_users_online: number;
  nodes: NodeStatus[];
}

export interface RevenueData {
  date: string;
  amount_kopeks: number;
  amount_rubles: number;
}

export interface SubscriptionStats {
  total: number;
  active: number;
  trial: number;
  paid: number;
  expired: number;
  purchased_today: number;
  purchased_week: number;
  purchased_month: number;
  trial_to_paid_conversion: number;
}

export interface FinancialStats {
  income_today_kopeks: number;
  income_today_rubles: number;
  income_month_kopeks: number;
  income_month_rubles: number;
  income_total_kopeks: number;
  income_total_rubles: number;
  subscription_income_kopeks: number;
  subscription_income_rubles: number;
}

export interface ServerStats {
  total_servers: number;
  available_servers: number;
  servers_with_connections: number;
  total_revenue_kopeks: number;
  total_revenue_rubles: number;
}

export interface TariffStatItem {
  tariff_id: number;
  tariff_name: string;
  active_subscriptions: number;
  trial_subscriptions: number;
  purchased_today: number;
  purchased_week: number;
  purchased_month: number;
}

export interface TariffStats {
  tariffs: TariffStatItem[];
  total_tariff_subscriptions: number;
}

export interface DashboardStats {
  nodes: NodesOverview;
  subscriptions: SubscriptionStats;
  financial: FinancialStats;
  servers: ServerStats;
  revenue_chart: RevenueData[];
  tariff_stats?: TariffStats;
}

export interface TopReferrerItem {
  user_id: number;
  telegram_id: number | null;
  username?: string;
  email?: string | null;
  display_name: string;
  invited_count: number;
  invited_today: number;
  invited_week: number;
  invited_month: number;
  earnings_today_kopeks: number;
  earnings_week_kopeks: number;
  earnings_month_kopeks: number;
  earnings_total_kopeks: number;
}

export interface TopReferrersResponse {
  by_earnings: TopReferrerItem[];
  by_invited: TopReferrerItem[];
  total_referrers: number;
  total_referrals: number;
  total_earnings_kopeks: number;
}

export interface TopCampaignItem {
  id: number;
  name: string;
  start_parameter: string;
  bonus_type: string;
  is_active: boolean;
  registrations: number;
  conversions: number;
  conversion_rate: number;
  total_revenue_kopeks: number;
  avg_revenue_per_user_kopeks: number;
  created_at?: string;
}

export interface TopCampaignsResponse {
  campaigns: TopCampaignItem[];
  total_campaigns: number;
  total_registrations: number;
  total_revenue_kopeks: number;
}

export interface RecentPaymentItem {
  id: number;
  user_id: number;
  telegram_id: number | null;
  email?: string | null;
  username?: string | null;
  display_name: string;
  amount_kopeks: number;
  amount_rubles: number;
  type: string;
  type_display: string;
  payment_method?: string | null;
  description?: string | null;
  created_at: string;
  is_completed: boolean;
}

export interface RecentPaymentsResponse {
  payments: RecentPaymentItem[];
  total_count: number;
  total_today_kopeks: number;
  total_week_kopeks: number;
}

export interface SystemInfo {
  bot_version: string;
  python_version: string;
  uptime_seconds: number;
  users_total: number;
  subscriptions_active: number;
}

export const statsApi = {
  // Get system info
  getSystemInfo: async (): Promise<SystemInfo> => {
    const data = await getOverview();
    return {
      bot_version: 'ArcVPN',
      python_version: '',
      uptime_seconds: Number(data.system?.uptime_seconds || 0),
      users_total: Number(data.users?.total || 0),
      subscriptions_active: Number(data.subscriptions?.active || 0),
    };
  },

  // Get complete dashboard stats
  getDashboardStats: async (): Promise<DashboardStats> => {
    return adaptDashboard(await getOverview()) as DashboardStats;
  },

  // Get nodes status
  getNodesStatus: async (): Promise<NodesOverview> => {
    return (adaptDashboard(await getOverview()) as DashboardStats).nodes;
  },

  // Restart a node
  restartNode: async (nodeUuid: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/cabinet/admin/stats/nodes/${nodeUuid}/restart`);
    return response.data;
  },

  // Toggle node (enable/disable)
  toggleNode: async (
    nodeUuid: string,
  ): Promise<{ success: boolean; message: string; is_disabled: boolean }> => {
    const response = await apiClient.post(`/cabinet/admin/stats/nodes/${nodeUuid}/toggle`);
    return response.data;
  },

  // Get top referrers
  getTopReferrers: async (limit: number = 20): Promise<TopReferrersResponse> => {
    const data = await getOverview();
    const rows = (data.referrals?.leaders || [])
      .slice(0, limit)
      .map((item: Record<string, any>) => ({
        user_id: Number(item.telegram_id),
        telegram_id: Number(item.telegram_id),
        username: item.username || undefined,
        email: null,
        display_name: item.first_name || item.username || `ID ${item.telegram_id}`,
        invited_count: Number(item.invited_count || 0),
        invited_today: 0,
        invited_week: 0,
        invited_month: 0,
        earnings_today_kopeks: 0,
        earnings_week_kopeks: 0,
        earnings_month_kopeks: 0,
        earnings_total_kopeks: 0,
      }));
    return {
      by_earnings: rows,
      by_invited: rows,
      total_referrers: rows.length,
      total_referrals: Number(data.referrals?.total_invited || 0),
      total_earnings_kopeks: 0,
    };
  },

  // Get top campaigns
  getTopCampaigns: async (limit: number = 20): Promise<TopCampaignsResponse> => {
    void limit;
    return { campaigns: [], total_campaigns: 0, total_registrations: 0, total_revenue_kopeks: 0 };
  },

  // Get recent payments
  getRecentPayments: async (limit: number = 50): Promise<RecentPaymentsResponse> => {
    const data = await getOverview();
    const payments = (data.recent_payments || [])
      .slice(0, limit)
      .map((item: Record<string, any>, index: number) => ({
        id: index + 1,
        user_id: Number(item.telegram_id),
        telegram_id: Number(item.telegram_id),
        email: null,
        username: item.username || null,
        display_name: item.first_name || item.username || `ID ${item.telegram_id}`,
        amount_kopeks: Math.round(Number(item.display_amount_rub || 0) * 100),
        amount_rubles: Number(item.display_amount_rub || 0),
        type: 'subscription',
        type_display: item.tariff_name || 'Подписка',
        payment_method: item.payment_type || null,
        description: item.tariff_name || null,
        created_at: item.paid_at,
        is_completed: ['paid', 'succeeded'].includes(item.status),
      }));
    return {
      payments,
      total_count: payments.length,
      total_today_kopeks: payments.reduce(
        (sum: number, item: RecentPaymentItem) => sum + item.amount_kopeks,
        0,
      ),
      total_week_kopeks: payments.reduce(
        (sum: number, item: RecentPaymentItem) => sum + item.amount_kopeks,
        0,
      ),
    };
  },
};
