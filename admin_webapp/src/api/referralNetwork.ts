import { getReferralNetwork } from '@/arcvpn/api';
import type {
  NetworkGraphData,
  NetworkUserDetail,
  NetworkCampaignDetail,
  NetworkSearchResult,
  ScopeOptionsData,
  ScopeSelection,
} from '@/types/referralNetwork';

export const referralNetworkApi = {
  getScopeOptions: async (): Promise<ScopeOptionsData> => {
    return { campaigns: [], partners: [] };
  },

  getFullGraph: async (): Promise<NetworkGraphData> => {
    return getReferralNetwork() as Promise<NetworkGraphData>;
  },

  getScopedGraph: async (selections: ScopeSelection[]): Promise<NetworkGraphData> => {
    const userIds = selections.filter((s) => s.type === 'user').map((s) => s.id);
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    if (userIds.length === 0) return graph;
    const keep = new Set<number>(userIds);
    let changed = true;
    while (changed) {
      changed = false;
      for (const user of graph.users) {
        if (user.referrer_id && keep.has(user.referrer_id) && !keep.has(user.id)) {
          keep.add(user.id); changed = true;
        }
      }
    }
    const users = graph.users.filter((user) => keep.has(user.id));
    return { ...graph, users, campaigns: [], edges: graph.edges.filter((edge) => keep.has(Number(edge.source.replace('user_', ''))) && keep.has(Number(edge.target.replace('user_', '')))), total_users: users.length, total_referrers: users.filter((user) => user.direct_referrals > 0).length };
  },

  getUserDetail: async (userId: number): Promise<NetworkUserDetail> => {
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    const user = graph.users.find((item) => item.id === userId);
    if (!user) throw new Error('Referral user not found');
    const referrer = graph.users.find((item) => item.id === user.referrer_id);
    return { ...user, referrer_display_name: referrer?.display_name ?? null, campaign_name: null };
  },

  getCampaignDetail: async (campaignId: number): Promise<NetworkCampaignDetail> => {
    throw new Error(`Campaign ${campaignId} is not available in ArcVPN`);
  },

  search: async (query: string): Promise<NetworkSearchResult> => {
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    const needle = query.trim().toLowerCase();
    return { users: graph.users.filter((user) => `${user.display_name} ${user.username || ''} ${user.tg_id || ''}`.toLowerCase().includes(needle)).slice(0, 30), campaigns: [] };
  },
};
