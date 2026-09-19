import { adminModuleJson } from '@/arcvpn/api';

// ============ Period Params ============

export interface SalesStatsParams {
  days?: number;
  start_date?: string;
  end_date?: string;
}

// ============ Summary ============

export interface SalesSummary {
  total_revenue_kopeks: number;
  manual_topup_kopeks: number;
  active_subscriptions: number;
  active_trials: number;
  new_trials: number;
  new_paid_subscriptions: number;
  expired_subscriptions: number;
  trial_to_paid_conversion: number;
  renewals_count: number;
  addon_revenue_kopeks: number;
}

// ============ Trials ============

export interface ProviderBreakdownItem {
  provider: string;
  count: number;
}

export interface DailyTrialItem {
  date: string;
  registrations: number;
  trials: number;
}

export interface TrialsStats {
  total_trials: number;
  total_registrations: number;
  conversion_rate: number;
  avg_trial_duration_days: number;
  by_provider: ProviderBreakdownItem[];
  daily: DailyTrialItem[];
}

// ============ Sales ============

export interface SalesByTariffItem {
  tariff_id: number;
  tariff_name: string;
  count: number;
}

export interface SalesByPeriodItem {
  period_days: number;
  count: number;
}

export interface DailySalesItem {
  date: string;
  count: number;
  revenue_kopeks: number;
}

export interface DailyTariffSalesItem {
  date: string;
  tariff_name: string;
  count: number;
}

export interface SalesStats {
  total_sales: number;
  total_revenue_kopeks: number;
  avg_order_kopeks: number;
  top_tariff_name: string;
  by_tariff: SalesByTariffItem[];
  by_period: SalesByPeriodItem[];
  daily: DailySalesItem[];
  daily_by_tariff: DailyTariffSalesItem[];
}

// ============ Renewals ============

export interface RenewalPeriodStats {
  count: number;
  revenue_kopeks: number;
}

export interface RenewalChange {
  absolute: number;
  percent: number;
  trend: 'up' | 'down' | 'stable';
}

export interface DailyRenewalItem {
  date: string;
  count: number;
}

export interface RenewalsStats {
  total_renewals: number;
  total_revenue_kopeks: number;
  renewal_rate: number;
  current_period: RenewalPeriodStats;
  previous_period: RenewalPeriodStats;
  change: RenewalChange;
  daily: DailyRenewalItem[];
}

// ============ Add-ons ============

export interface AddonByPackageItem {
  traffic_gb: number;
  count: number;
}

export interface DailyAddonItem {
  date: string;
  count: number;
  total_gb: number;
}

export interface DailyDeviceItem {
  date: string;
  count: number;
}

export interface AddonsStats {
  total_purchases: number;
  total_gb_purchased: number;
  addon_revenue_kopeks: number;
  device_purchases: number;
  device_revenue_kopeks: number;
  by_package: AddonByPackageItem[];
  daily: DailyAddonItem[];
  daily_devices: DailyDeviceItem[];
}

// ============ Deposits ============

export interface DepositByMethodItem {
  method: string;
  count: number;
  amount_kopeks: number;
}

export interface DailyDepositItem {
  date: string;
  count: number;
  amount_kopeks: number;
}

export interface DailyDepositByMethodItem {
  date: string;
  method: string;
  amount_kopeks: number;
}

export interface DepositsStats {
  total_deposits: number;
  total_amount_kopeks: number;
  avg_deposit_kopeks: number;
  by_method: DepositByMethodItem[];
  daily: DailyDepositItem[];
  daily_by_method: DailyDepositByMethodItem[];
}

export interface GatewaySuccessItem {
  method: string;
  total: number;
  paid: number;
  success_rate: number;
}

export interface PaymentHealth {
  total_attempts: number;
  total_paid: number;
  success_rate: number;
  failed_purchases: number;
  by_gateway: GatewaySuccessItem[];
}

// ============ API ============

type RawSale = { id: number; user_id: number; payment_type: string | null; operation_type: string | null; status: string; period_days: number | null; created_at: string; paid_at: string | null; tariff_id: number | null; tariff_name: string; amount_rub: number };
type SalesRaw = { payments: RawSale[]; active_subscriptions: number };
async function loadRaw(params: SalesStatsParams): Promise<SalesRaw> {
  const query = new URLSearchParams();
  if (params.days !== undefined) query.set('days', String(params.days));
  if (params.start_date) query.set('start_date', params.start_date);
  if (params.end_date) query.set('end_date', params.end_date);
  return adminModuleJson(`/api/admin/sales-stats?${query}`, { active_subscriptions: 2, payments: [{ id: 1, user_id: 1, payment_type: 'cards', operation_type: 'new', status: 'paid', period_days: 30, created_at: '2026-09-14T12:00:00Z', paid_at: '2026-09-14T12:00:00Z', tariff_id: 1, tariff_name: 'Стандарт', amount_rub: 399 }] }) as Promise<SalesRaw>;
}
const paid = (rows: RawSale[]) => rows.filter((p) => ['paid', 'succeeded'].includes(p.status));
const kopeks = (rows: RawSale[]) => Math.round(rows.reduce((sum, p) => sum + Number(p.amount_rub || 0), 0) * 100);
const day = (p: RawSale) => String(p.paid_at || p.created_at).slice(0, 10);

export const salesStatsApi = {
  getSummary: async (params: SalesStatsParams = {}): Promise<SalesSummary> => {
    const raw = await loadRaw(params); const successful = paid(raw.payments); const trials = successful.filter((p) => p.payment_type === 'trial'); const sales = successful.filter((p) => p.payment_type !== 'trial');
    const seen = new Set<number>(); let renewals = 0; for (const p of sales) { if (seen.has(p.user_id)) renewals++; seen.add(p.user_id); }
    return { total_revenue_kopeks: kopeks(sales), manual_topup_kopeks: 0, active_subscriptions: raw.active_subscriptions, active_trials: 0, new_trials: trials.length, new_paid_subscriptions: seen.size, expired_subscriptions: 0, trial_to_paid_conversion: trials.length ? Math.round(seen.size / trials.length * 1000) / 10 : 0, renewals_count: renewals, addon_revenue_kopeks: 0 };
  },

  getTrials: async (params: SalesStatsParams = {}): Promise<TrialsStats> => {
    const raw = await loadRaw(params); const trials = paid(raw.payments).filter((p) => p.payment_type === 'trial'); const registrations = new Set(raw.payments.map((p) => p.user_id)).size; const daily = new Map<string, { registrations: Set<number>; trials: number }>(); for (const p of raw.payments) { const key = day(p); const x = daily.get(key) || { registrations: new Set<number>(), trials: 0 }; x.registrations.add(p.user_id); if (p.payment_type === 'trial' && ['paid','succeeded'].includes(p.status)) x.trials++; daily.set(key, x); }
    return { total_trials: trials.length, total_registrations: registrations, conversion_rate: registrations ? Math.round(trials.length / registrations * 1000) / 10 : 0, avg_trial_duration_days: trials.length ? trials.reduce((s,p)=>s+Number(p.period_days||0),0)/trials.length : 0, by_provider: [], daily: [...daily].map(([date,x])=>({date,registrations:x.registrations.size,trials:x.trials})) };
  },

  getSales: async (params: SalesStatsParams = {}): Promise<SalesStats> => {
    const rows = paid((await loadRaw(params)).payments).filter((p) => p.payment_type !== 'trial'); const byTariff = new Map<string,{id:number,count:number}>(); const byPeriod = new Map<number,number>(); const daily = new Map<string,{count:number,revenue:number}>(); for (const p of rows) { const tariff=byTariff.get(p.tariff_name)||{id:Number(p.tariff_id||0),count:0}; tariff.count++; byTariff.set(p.tariff_name,tariff); const period=Number(p.period_days||0); byPeriod.set(period,(byPeriod.get(period)||0)+1); const d=daily.get(day(p))||{count:0,revenue:0}; d.count++; d.revenue+=Math.round(Number(p.amount_rub||0)*100); daily.set(day(p),d); }
    const by_tariff=[...byTariff].map(([tariff_name,x])=>({tariff_id:x.id,tariff_name,count:x.count})); const top=[...by_tariff].sort((a,b)=>b.count-a.count)[0];
    return { total_sales: rows.length,total_revenue_kopeks:kopeks(rows),avg_order_kopeks:rows.length?Math.round(kopeks(rows)/rows.length):0,top_tariff_name:top?.tariff_name||'—',by_tariff,by_period:[...byPeriod].map(([period_days,count])=>({period_days,count})),daily:[...daily].map(([date,x])=>({date,count:x.count,revenue_kopeks:x.revenue})),daily_by_tariff:rows.map(p=>({date:day(p),tariff_name:p.tariff_name,count:1})) };
  },

  getRenewals: async (params: SalesStatsParams = {}): Promise<RenewalsStats> => {
    const rows=paid((await loadRaw(params)).payments).filter(p=>p.payment_type!=='trial'); const seen=new Set<number>(); const renewals=rows.filter(p=>{const old=seen.has(p.user_id);seen.add(p.user_id);return old;}); const current={count:renewals.length,revenue_kopeks:kopeks(renewals)}; return {total_renewals:current.count,total_revenue_kopeks:current.revenue_kopeks,renewal_rate:rows.length?Math.round(current.count/rows.length*1000)/10:0,current_period:current,previous_period:{count:0,revenue_kopeks:0},change:{absolute:current.count,percent:current.count?100:0,trend:current.count?'up':'stable'},daily:[...new Set(renewals.map(day))].map(date=>({date,count:renewals.filter(p=>day(p)===date).length}))};
  },

  getAddons: async (params: SalesStatsParams = {}): Promise<AddonsStats> => {
    void params; return { total_purchases:0,total_gb_purchased:0,addon_revenue_kopeks:0,device_purchases:0,device_revenue_kopeks:0,by_package:[],daily:[],daily_devices:[] };
  },

  getDeposits: async (params: SalesStatsParams = {}): Promise<DepositsStats> => {
    const rows=paid((await loadRaw(params)).payments).filter(p=>p.payment_type==='balance'); const by=new Map<string,{count:number,amount:number}>(); for(const p of rows){const key=p.payment_type||'balance';const x=by.get(key)||{count:0,amount:0};x.count++;x.amount+=Math.round(Number(p.amount_rub||0)*100);by.set(key,x);} return {total_deposits:rows.length,total_amount_kopeks:kopeks(rows),avg_deposit_kopeks:rows.length?Math.round(kopeks(rows)/rows.length):0,by_method:[...by].map(([method,x])=>({method,count:x.count,amount_kopeks:x.amount})),daily:rows.map(p=>({date:day(p),count:1,amount_kopeks:Math.round(Number(p.amount_rub||0)*100)})),daily_by_method:rows.map(p=>({date:day(p),method:p.payment_type||'balance',amount_kopeks:Math.round(Number(p.amount_rub||0)*100)}))};
  },

  getPaymentHealth: async (params: SalesStatsParams = {}): Promise<PaymentHealth> => {
    const rows=(await loadRaw(params)).payments.filter(p=>p.payment_type!=='trial'); const success=paid(rows); const methods=[...new Set(rows.map(p=>p.payment_type||'unknown'))]; return {total_attempts:rows.length,total_paid:success.length,success_rate:rows.length?Math.round(success.length/rows.length*1000)/10:0,failed_purchases:rows.length-success.length,by_gateway:methods.map(method=>{const all=rows.filter(p=>(p.payment_type||'unknown')===method);const ok=paid(all);return {method,total:all.length,paid:ok.length,success_rate:all.length?Math.round(ok.length/all.length*1000)/10:0};})};
  },
};
