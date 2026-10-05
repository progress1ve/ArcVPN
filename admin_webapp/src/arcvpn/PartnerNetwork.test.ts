import { expect, it } from 'vitest';
import { partnerGraph } from './PartnerNetwork';

it('adapts anonymized partner network to actual admin graph without original customer IDs or foreign edges', () => {
  const graph = partnerGraph([
    { client: 'C-root', parent: null, source_id: 7, bound_at: '2026-10-05', purchases: 1, spent_cents: 9900 },
    { client: 'C-child', parent: 'C-root', source_id: 7, bound_at: '2026-10-05', purchases: 0, spent_cents: 0 },
    { client: 'C-separate', parent: 'C-foreign', source_id: 7, bound_at: '2026-10-05', purchases: 0, spent_cents: 0 },
  ], [{ id: 7, name: 'Assigned link', active: true, enabled: true }]);
  expect(graph.users.map(user => user.id)).toEqual([1, 2, 3]);
  expect(graph.users.every(user => user.tg_id === null && user.username === null && user.email === null)).toBe(true);
  expect(graph.edges).toContainEqual({ source: 'user_1', target: 'user_2', type: 'referral' });
  expect(graph.edges).toContainEqual({ source: 'campaign_7', target: 'user_3', type: 'campaign' });
  expect(JSON.stringify(graph)).not.toContain('C-foreign');
  expect(graph.campaigns[0].total_revenue_kopeks).toBe(9900);
  expect(graph.campaigns[0].conversion_rate).toBeCloseTo(100 / 3);
});
