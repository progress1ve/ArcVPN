import { describe, expect, it } from 'vitest';
import { dashboardStats } from './api';

describe('ArcVPN dashboard subscription stats', () => {
  it('preserves backend trial and paid counts', () => {
    const result = dashboardStats({
      subscriptions: { total: 12, active: 9, expired: 3, trial: 4, paid: 5 },
      business: { payments: {} },
      financials: {},
      remnawave: { nodes: [] },
    });

    expect(result.subscriptions.trial).toBe(4);
    expect(result.subscriptions.paid).toBe(5);
  });
});
