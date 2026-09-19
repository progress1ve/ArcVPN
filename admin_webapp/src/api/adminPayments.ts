import { adminModuleJson } from '@/arcvpn/api';
import type { PaginatedResponse, PendingPayment, ManualCheckResponse } from '../types';

export interface PaymentsStats {
  total_pending: number;
  by_method: Record<string, number>;
}

export interface SearchStats {
  total: number;
  pending: number;
  paid: number;
  cancelled: number;
  by_method: Record<string, number>;
}

export const adminPaymentsApi = {
  // Get all pending payments (admin)
  getPendingPayments: async (params?: {
    page?: number;
    per_page?: number;
    method_filter?: string;
  }): Promise<PaginatedResponse<PendingPayment>> => {
    return adminPaymentsApi.searchPayments({ ...params, status_filter: 'pending' });
  },

  // Get payments statistics
  getStats: async (): Promise<PaymentsStats> => {
    const stats = await adminPaymentsApi.getSearchStats({ status_filter: 'pending' });
    return { total_pending: stats.pending, by_method: stats.by_method };
  },

  // Search payments with filters
  searchPayments: async (params?: {
    search?: string;
    status_filter?: string;
    method_filter?: string;
    period?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<PendingPayment>> => {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.status_filter && params.status_filter !== 'all') query.set('status', params.status_filter);
    if (params?.method_filter) query.set('method', params.method_filter);
    if (params?.period) query.set('period', params.period);
    if (params?.date_from) query.set('date_from', params.date_from);
    if (params?.date_to) query.set('date_to', params.date_to);
    query.set('page', String(params?.page || 1));
    query.set('per_page', String(params?.per_page || 20));
    const demo = {
      items: [{ id: 1, order_id: 'demo-1', payment_type: 'cards', status: 'paid', created_at: '2026-09-14T12:32:00Z', paid_at: '2026-09-14T12:32:00Z', amount_rub: 399, telegram_id: 700001, username: 'alex' }],
      total: 1, page: 1, per_page: 20, pages: 1,
      stats: [{ status: 'paid', method: 'cards', count: 1 }],
    };
    const data = await adminModuleJson(`/api/admin/payments?${query}`, demo);
    return {
      items: (data.items || []).map((row: Record<string, unknown>) => ({
        id: Number(row.id), method: String(row.payment_type || 'unknown'),
        method_display: String(row.payment_type || 'unknown'), identifier: String(row.order_id || row.id),
        amount_kopeks: Math.round(Number(row.amount_rub || 0) * 100), amount_rubles: Number(row.amount_rub || 0),
        status: String(row.status || 'unknown'), status_emoji: '', status_text: String(row.status || 'unknown'),
        is_paid: ['paid', 'succeeded'].includes(String(row.status)), is_checkable: false,
        created_at: String(row.paid_at || row.created_at || ''), expires_at: null, payment_url: null,
        user_id: Number(row.user_id || row.telegram_id), user_telegram_id: Number(row.telegram_id),
        user_username: row.username ? String(row.username) : null, user_email: null,
      })),
      total: Number(data.total || 0), page: Number(data.page || 1), per_page: Number(data.per_page || 20), pages: Number(data.pages || 1),
    };
  },

  // Get search statistics with filters
  getSearchStats: async (params?: {
    search?: string;
    status_filter?: string;
    method_filter?: string;
    period?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<SearchStats> => {
    const data = await adminPaymentsApi.searchPayments({ ...params, page: 1, per_page: 100 });
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.status_filter && params.status_filter !== 'all') query.set('status', params.status_filter);
    if (params?.method_filter) query.set('method', params.method_filter);
    if (params?.period) query.set('period', params.period);
    if (params?.date_from) query.set('date_from', params.date_from);
    if (params?.date_to) query.set('date_to', params.date_to);
    query.set('page', '1'); query.set('per_page', '10');
    const raw = await adminModuleJson(`/api/admin/payments?${query}`, { stats: [{ status: 'paid', method: 'cards', count: data.total }], total: data.total });
    const result: SearchStats = { total: Number(raw.total || 0), pending: 0, paid: 0, cancelled: 0, by_method: {} };
    for (const item of raw.stats || []) { const count = Number(item.count || 0); const status = String(item.status); const method = String(item.method); if (status === 'pending' || status === 'created') result.pending += count; else if (status === 'paid' || status === 'succeeded') result.paid += count; else result.cancelled += count; result.by_method[method] = (result.by_method[method] || 0) + count; }
    return result;
  },

  // Get specific payment details
  getPayment: async (method: string, paymentId: number): Promise<PendingPayment> => {
    const data = await adminPaymentsApi.searchPayments({ page: 1, per_page: 100 });
    const payment = data.items.find((item) => item.id === paymentId && item.method === method);
    if (!payment) throw new Error('Payment not found');
    return payment;
  },

  // Manually check payment status
  checkPaymentStatus: async (method: string, paymentId: number): Promise<ManualCheckResponse> => {
    void method; void paymentId;
    throw new Error('Проверка провайдера ещё не подключена к безопасной ArcVPN job');
  },
};
