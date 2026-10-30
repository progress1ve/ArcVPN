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


describe('ArcVPN online customers', () => {
  it('uses unique customer presence rather than summed node sessions', () => {
    const result = dashboardStats({ remnawave: {
      healthy: true, online_users: [{}, {}], nodes: [{ users_online: 12 }, { users_online: 8 }],
    } });
    expect(result.online_users).toBe(2);
  });
  it('distinguishes known zero from unavailable telemetry', () => {
    expect(dashboardStats({ remnawave: { healthy: true, online_users: [] } }).online_users).toBe(0);
    expect(dashboardStats({ remnawave: { healthy: false, online_users: [] } }).online_users).toBeNull();
    expect(dashboardStats({}).online_users).toBeNull();
  });
});
