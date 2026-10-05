import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import type { NetworkGraphData, SubscriptionStatus } from '@/types/referralNetwork';
import { useReferralNetworkStore } from '@/store/referralNetwork';

const NetworkGraph = lazy(() => import('@/pages/ReferralNetwork/components/NetworkGraph').then(m => ({ default: m.NetworkGraph })));
const NetworkLegend = lazy(() => import('@/pages/ReferralNetwork/components/NetworkLegend').then(m => ({ default: m.NetworkLegend })));
const NetworkControls = lazy(() => import('@/pages/ReferralNetwork/components/NetworkControls').then(m => ({ default: m.NetworkControls })));
export type PartnerNode = { client: string; parent: string | null; source_id: number; purchases: number; spent_cents: number; bound_at: string; subscription_status?: SubscriptionStatus | null };
type Source = { id: number; name: string; active: boolean; enabled: boolean };

export function partnerGraph(nodes: PartnerNode[], sources: Source[]): NetworkGraphData {
  // IDs are local display indexes, never database or Telegram customer IDs.
  const ids = new Map(nodes.map((node, index) => [node.client, index + 1]));
  const children = new Map<string, number>();
  nodes.forEach(node => { if (node.parent && ids.has(node.parent)) children.set(node.parent, (children.get(node.parent) || 0) + 1); });
  const sourceIds = new Set(sources.map(source => source.id));
  const users = nodes.map(node => ({
    id: ids.get(node.client)!, tg_id: null, username: null, email: null, display_name: `Клиент ${ids.get(node.client)}`, is_partner: false,
    referrer_id: node.parent ? ids.get(node.parent) || null : null, campaign_id: sourceIds.has(node.source_id) ? node.source_id : null,
    direct_referrals: children.get(node.client) || 0, total_branch_users: 0, branch_revenue_kopeks: 0,
    personal_revenue_kopeks: node.spent_cents, personal_spent_kopeks: node.spent_cents,
    subscription_name: null, subscription_end: null, subscription_status: node.subscription_status || null, registered_at: node.bound_at,
  }));
  const campaigns = sources.map(source => {
    const clients = nodes.filter(node => node.source_id === source.id);
    const purchases = clients.reduce((sum, node) => sum + node.purchases, 0);
    const revenue = clients.reduce((sum, node) => sum + node.spent_cents, 0);
    return { id: source.id, name: source.name, start_parameter: '', is_active: source.active && source.enabled,
      direct_users: clients.length, total_network_users: clients.length, total_revenue_kopeks: revenue,
      conversion_rate: clients.length ? clients.filter(node => node.purchases > 0).length * 100 / clients.length : 0,
      avg_check_kopeks: purchases ? Math.round(revenue / purchases) : 0, top_referrers: [] };
  });
  return { users, campaigns, edges: users.map(user => user.referrer_id !== null
    ? { source: 'user_' + user.referrer_id, target: 'user_' + user.id, type: 'referral' as const }
    : { source: 'campaign_' + user.campaign_id, target: 'user_' + user.id, type: 'campaign' as const }).filter(edge => edge.source !== 'campaign_null'),
    total_users: users.length, total_referrers: children.size, total_campaigns: campaigns.length,
    total_earnings_kopeks: 0, total_subscription_revenue_kopeks: nodes.reduce((sum, node) => sum + node.spent_cents, 0) };
}

export default function PartnerNetwork({ nodes, sources, truncated }: { nodes: PartnerNode[]; sources: Source[]; truncated: boolean }) {
  const [webgl, setWebgl] = useState(false);
  const selected = useReferralNetworkStore(state => state.selectedNode);
  const graph = useMemo(() => partnerGraph(nodes, sources), [nodes, sources]);
  useEffect(() => { useReferralNetworkStore.getState().setSelectedNode(null); }, [nodes, sources]);
  useEffect(() => {
    useReferralNetworkStore.getState().setFullNetwork(true);
    try { const canvas = document.createElement('canvas'); const gl = canvas.getContext('webgl2') || canvas.getContext('webgl'); setWebgl(!!gl); gl?.getExtension('WEBGL_lose_context')?.loseContext(); } catch { setWebgl(false); }
    return () => { useReferralNetworkStore.getState().setFullNetwork(false); };
  }, []);
  const node = selected?.type === 'user' ? nodes[selected.id - 1] : null;
  const source = selected?.type === 'campaign' ? sources.find(item => item.id === selected.id) : null;
  return <section className="relative min-h-0 flex-1">
    {truncated && <p role="status" className="absolute left-4 top-14 z-30 max-w-sm rounded-xl bg-dark-900/95 p-3 text-xs text-warning-400">На графе показаны первые 2 000 клиентов. Используйте фильтр ссылки и периода или полный список клиентов.</p>}
    <div id="referral-network-container" className="absolute inset-0 overflow-hidden bg-[#0a0a0f]">
      {webgl && (nodes.length || sources.length) ? <Suspense fallback={<p className="p-5 text-sm text-dark-400">Загружаем сеть…</p>}><NetworkGraph compact data={graph} className="h-full w-full" /><NetworkControls className="absolute bottom-4 left-1/2 -translate-x-1/2" /><NetworkLegend className="absolute bottom-4 right-4 hidden lg:block" /></Suspense> : <p className="p-5 text-sm text-dark-400">{!nodes.length ? 'Привлечённых клиентов за этот период нет.' : 'Граф недоступен на этом устройстве. Клиенты доступны в списке ниже.'}</p>}
      <div className="absolute bottom-20 left-4 grid grid-cols-2 gap-x-5 gap-y-3 rounded-xl border border-dark-700/50 bg-dark-900/80 p-3 text-xs backdrop-blur-md sm:bottom-4"><div><p className="text-dark-400">Клиентов</p><p className="mt-1 text-lg font-semibold">{nodes.length}</p></div><div><p className="text-dark-400">Оплатили</p><p className="mt-1 text-lg font-semibold">{nodes.filter(item => item.purchases > 0).length}</p></div><div><p className="text-dark-400">Ссылок</p><p className="mt-1 text-lg font-semibold">{sources.length}</p></div><div><p className="text-dark-400">Покупки</p><p className="mt-1 text-lg font-semibold">{nodes.reduce((sum, item) => sum + item.purchases, 0)}</p></div></div>
      {(node || source) && <div className="absolute right-3 top-16 z-20 max-w-xs rounded-xl border border-dark-700 bg-dark-900 p-4 text-sm"><b>{node?.client || source?.name}</b>{node && <p className="mt-2 text-dark-400">Покупок: {node.purchases} · Оплачено: {(node.spent_cents / 100).toLocaleString('ru-RU')} ₽</p>}</div>}
    </div>
    <details className="absolute right-4 top-3 z-10 max-w-[65%] rounded-xl border border-dark-700/50 bg-dark-900/90 p-3 backdrop-blur-md"><summary className="cursor-pointer text-xs font-medium">Клиенты: {nodes.length} · Ссылки: {sources.length}</summary><ul className="mt-3 max-h-64 space-y-2 overflow-auto text-xs text-dark-300">{nodes.map(node => <li key={node.client}>{node.client} · {sources.find(source => source.id === node.source_id)?.name} · покупок: {node.purchases}{node.parent ? ` · приглашён ${node.parent}` : ''}</li>)}</ul></details>
  </section>;
}
