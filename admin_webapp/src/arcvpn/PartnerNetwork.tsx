import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import type { NetworkGraphData } from '@/types/referralNetwork';
import { useReferralNetworkStore } from '@/store/referralNetwork';

const NetworkGraph = lazy(() => import('@/pages/ReferralNetwork/components/NetworkGraph').then(m => ({ default: m.NetworkGraph })));
const NetworkControls = lazy(() => import('@/pages/ReferralNetwork/components/NetworkControls').then(m => ({ default: m.NetworkControls })));
export type PartnerNode = { client: string; parent: string | null; source_id: number; purchases: number; spent_cents: number; bound_at: string };
type Source = { id: number; name: string; active: boolean; enabled: boolean };

export function partnerGraph(nodes: PartnerNode[], sources: Source[]): NetworkGraphData {
  // IDs are local display indexes, never database or Telegram customer IDs.
  const ids = new Map(nodes.map((node, index) => [node.client, index + 1]));
  const children = new Map<string, number>();
  nodes.forEach(node => { if (node.parent && ids.has(node.parent)) children.set(node.parent, (children.get(node.parent) || 0) + 1); });
  const sourceIds = new Set(sources.map(source => source.id));
  const users = nodes.map(node => ({
    id: ids.get(node.client)!, tg_id: null, username: null, email: null, display_name: node.client, is_partner: false,
    referrer_id: node.parent ? ids.get(node.parent) || null : null, campaign_id: sourceIds.has(node.source_id) ? node.source_id : null,
    direct_referrals: children.get(node.client) || 0, total_branch_users: 0, branch_revenue_kopeks: 0,
    personal_revenue_kopeks: node.spent_cents, personal_spent_kopeks: node.spent_cents,
    subscription_name: null, subscription_end: null, subscription_status: null, registered_at: node.bound_at,
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
  return <section className="space-y-4">
    <p className="text-xs text-dark-400">Ссылки и закреплённые клиенты. Связи показаны только между клиентами вашей сети; данные чужих клиентов скрыты.</p>
    {truncated && <p role="status" className="text-sm text-warning-400">На графе показаны первые 2 000 клиентов. Используйте фильтр ссылки и периода или полный список клиентов.</p>}
    <div id="referral-network-container" className="relative h-[60dvh] min-h-80 overflow-hidden rounded-2xl border border-dark-700/50 bg-[#0a0a0f]">
      {webgl && (nodes.length || sources.length) ? <Suspense fallback={<p className="p-5 text-sm text-dark-400">Загружаем сеть…</p>}><NetworkGraph data={graph} className="h-full w-full" /><NetworkControls className="absolute bottom-4 left-4" /></Suspense> : <p className="p-5 text-sm text-dark-400">{!nodes.length ? 'Привлечённых клиентов за этот период нет.' : 'Граф недоступен на этом устройстве. Клиенты доступны в списке ниже.'}</p>}
      {(node || source) && <div className="absolute right-3 top-3 max-w-xs rounded-xl border border-dark-700 bg-dark-900 p-4 text-sm"><b>{node?.client || source?.name}</b>{node && <p className="mt-2 text-dark-400">Покупок: {node.purchases} · Оплачено: {(node.spent_cents / 100).toLocaleString('ru-RU')} ₽</p>}</div>}
    </div>
    <details className="rounded-xl border border-dark-700/50 bg-dark-800/30 p-4"><summary className="cursor-pointer text-sm font-medium">Клиенты на графе ({nodes.length})</summary><ul className="mt-3 max-h-64 space-y-2 overflow-auto text-xs text-dark-300">{nodes.map(node => <li key={node.client}>{node.client} · {sources.find(source => source.id === node.source_id)?.name} · покупок: {node.purchases}{node.parent ? ` · приглашён ${node.parent}` : ''}</li>)}</ul></details>
  </section>;
}
