export interface DailyStatItem {
  date: string;
  referrals_count: number;
  earnings_kopeks: number;
}

export interface PeriodStats {
  days: number;
  referrals_count: number;
  earnings_kopeks: number;
}

export interface PeriodChange {
  absolute: number;
  percent: number;
  trend: 'up' | 'down' | 'stable';
}

export interface PeriodComparison {
  current: PeriodStats;
  previous: PeriodStats;
  referrals_change: PeriodChange;
  earnings_change: PeriodChange;
}
