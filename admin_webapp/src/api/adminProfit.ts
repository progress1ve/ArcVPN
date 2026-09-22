import { getJson } from '@/arcvpn/api';

export interface ProfitExpense {
  id: number;
  title: string;
  category: string;
  amount_rub: number;
  incurred_on: string;
  recurring_monthly: boolean;
  note?: string | null;
}

export interface ProfitMonth {
  month: string;
  recognized_revenue_rub: number;
  expenses_rub: number;
  net_profit_rub: number;
}

export interface ProfitReport {
  expenses: ProfitExpense[];
  summary: {
    month: string;
    month_revenue_rub: number;
    month_expenses_rub: number;
    month_net_rub: number;
  };
  monthly: ProfitMonth[];
}

const demo: ProfitReport = {
  expenses: [
    { id: 1, title: 'Основной хостинг', category: 'hosting', amount_rub: 4200, incurred_on: '2026-01-01', recurring_monthly: true },
    { id: 2, title: 'CDN', category: 'cdn', amount_rub: 1800, incurred_on: '2026-01-01', recurring_monthly: true },
    { id: 3, title: 'Реклама', category: 'advertising', amount_rub: 12000, incurred_on: '2026-09-04', recurring_monthly: false },
  ],
  summary: { month: '2026-09', month_revenue_rub: 28740, month_expenses_rub: 18000, month_net_rub: 10740 },
  monthly: Array.from({ length: 12 }, (_, index) => ({
    month: `2026-${String(index + 1).padStart(2, '0')}`,
    recognized_revenue_rub: 17000 + index * 1100,
    expenses_rub: index === 8 ? 18000 : 6000,
    net_profit_rub: 11000 + index * 1100 - (index === 8 ? 12000 : 0),
  })),
};
export const adminProfitApi = {
  get: async (month: string): Promise<ProfitReport> => {
    if (import.meta.env.DEV) return { ...demo, summary: { ...demo.summary, month } };
    return getJson(`/api/admin/expenses?month=${encodeURIComponent(month)}`) as Promise<ProfitReport>;
  },
  create: async (expense: Omit<ProfitExpense, 'id'>): Promise<void> => {
    if (import.meta.env.DEV) return;
    await getJson('/api/admin/expenses', { method: 'POST', body: JSON.stringify(expense) });
  },
  remove: async (id: number): Promise<void> => {
    if (import.meta.env.DEV) return;
    await getJson(`/api/admin/expenses/${id}`, { method: 'DELETE' });
  },
};
