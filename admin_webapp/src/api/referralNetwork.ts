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
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    return { campaigns: graph.campaigns, partners: [] };
  },

  getFullGraph: async (): Promise<NetworkGraphData> => {
    return getReferralNetwork() as Promise<NetworkGraphData>;
  },

  getScopedGraph: async (selections: ScopeSelection[]): Promise<NetworkGraphData> => {
    const userIds = selections.filter((s) => s.type === 'user').map((s) => s.id);
    const campaignIds = selections.filter((s) => s.type === 'campaign').map((s) => s.id);
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    if (userIds.length === 0 && campaignIds.length === 0) return graph;
    const keep = new Set<number>(userIds);
    for (const user of graph.users) {
      if (user.campaign_id !== null && campaignIds.includes(user.campaign_id)) keep.add(user.id);
    }
    let changed = true;
    while (changed) {
      changed = false;
      for (const user of graph.users) {
        if (user.referrer_id && keep.has(user.referrer_id) && !keep.has(user.id)) {
          keep.add(user.id);
          changed = true;
        }
      }
    }
    const users = graph.users.filter((user) => keep.has(user.id));
    const campaigns = graph.campaigns.filter((item) => campaignIds.includes(item.id));
    return {
      ...graph,
      users,
      campaigns,
      edges: graph.edges.filter((edge) => {
        const sourceUser = edge.source.startsWith('user_')
          ? Number(edge.source.replace('user_', ''))
          : null;
        const sourceCampaign = edge.source.startsWith('campaign_')
          ? Number(edge.source.replace('campaign_', ''))
          : null;
        const targetUser = Number(edge.target.replace('user_', ''));
        return (
          keep.has(targetUser) &&
          (sourceUser === null
            ? sourceCampaign !== null && campaignIds.includes(sourceCampaign)
            : keep.has(sourceUser))
        );
      }),
      total_users: users.length,
      total_referrers: users.filter((user) => user.direct_referrals > 0).length,
      total_campaigns: campaigns.length,
    };
  },

  getUserDetail: async (userId: number): Promise<NetworkUserDetail> => {
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    const user = graph.users.find((item) => item.id === userId);
    if (!user) throw new Error('Referral user not found');
    const referrer = graph.users.find((item) => item.id === user.referrer_id);
    return { ...user, referrer_display_name: referrer?.display_name ?? null, campaign_name: null };
  },

  getCampaignDetail: async (campaignId: number): Promise<NetworkCampaignDetail> => {
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    const campaign = graph.campaigns.find((item) => item.id === campaignId);
    if (!campaign) throw new Error(`Campaign ${campaignId} not found`);
    return campaign;
  },

  search: async (query: string): Promise<NetworkSearchResult> => {
    const graph = (await getReferralNetwork()) as NetworkGraphData;
    const needle = query.trim().toLowerCase();
    return {
      users: graph.users
        .filter((user) =>
          `${user.display_name} ${user.username || ''} ${user.tg_id || ''}`
            .toLowerCase()
            .includes(needle),
        )
        .slice(0, 30),
      campaigns: graph.campaigns
        .filter((campaign) =>
          `${campaign.name} ${campaign.start_parameter}`.toLowerCase().includes(needle),
        )
        .slice(0, 30),
    };
  },
};
