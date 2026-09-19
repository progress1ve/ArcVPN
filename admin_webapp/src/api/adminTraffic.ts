import { adminModuleJson } from '@/arcvpn/api';

export interface TrafficNodeInfo {
  node_uuid: string;
  node_name: string;
  country_code: string;
}

export interface UserTrafficItem {
  user_id: number;
  telegram_id: number | null;
  username: string | null;
  email: string | null;
  full_name: string;
  tariff_name: string | null;
  subscription_status: string | null;
  traffic_limit_gb: number;
  device_limit: number;
  node_traffic: Record<string, number>;
  total_bytes: number;
}

export interface TrafficUsageResponse {
  items: UserTrafficItem[];
  nodes: TrafficNodeInfo[];
  total: number;
  offset: number;
  limit: number;
  period_days: number;
  available_tariffs: string[];
  available_statuses: string[];
}

export interface ExportCsvResponse {
  success: boolean;
  message: string;
}

export interface TrafficEnrichmentData {
  devices_connected: number;
  total_spent_kopeks: number;
  subscription_start_date: string | null;
  subscription_end_date: string | null;
  last_node_name: string | null;
}

export interface TrafficEnrichmentResponse {
  data: Record<number, TrafficEnrichmentData>;
}

export type TrafficParams = {
  period?: number;
  limit?: number;
  offset?: number;
  search?: string;
  sort_by?: string;
  sort_desc?: boolean;
  tariffs?: string;
  statuses?: string;
  nodes?: string;
  start_date?: string;
  end_date?: string;
};

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const MAX_CACHE_ENTRIES = 20;

const trafficCache = new Map<string, { data: TrafficUsageResponse; timestamp: number }>();

function buildCacheKey(params: TrafficParams): string {
  return JSON.stringify({
    period: params.period ?? 30,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    search: params.search ?? '',
    sort_by: params.sort_by ?? 'total_bytes',
    sort_desc: params.sort_desc ?? true,
    tariffs: params.tariffs ?? '',
    statuses: params.statuses ?? '',
    nodes: params.nodes ?? '',
    start_date: params.start_date ?? '',
    end_date: params.end_date ?? '',
  });
}

const enrichmentCache: { data: TrafficEnrichmentResponse | null; timestamp: number } = {
  data: null,
  timestamp: 0,
};

export const adminTrafficApi = {
  getTrafficUsage: async (
    params: TrafficParams,
    options?: { skipCache?: boolean },
  ): Promise<TrafficUsageResponse> => {
    const key = buildCacheKey(params);

    if (!options?.skipCache) {
      const cached = trafficCache.get(key);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
      }
    }

    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== '') query.set(key, String(value));
    const raw = await adminModuleJson(`/api/admin/traffic?${query}`, { items: [{ user_id:1,telegram_id:700001,username:'alex',first_name:'Алексей',main_bytes:197568495616,lte_bytes:31138512896,traffic_limit_bytes:322122547200,device_limit:2,subscription_end:'2026-10-20',total_bytes:228707008512 }], total:1,offset:0,limit:50 });
    const data: TrafficUsageResponse = {
      items: (raw.items || []).map((row: Record<string, unknown>) => ({ user_id:Number(row.user_id),telegram_id:Number(row.telegram_id),username:row.username?String(row.username):null,email:null,full_name:String(row.first_name||row.username||`ID ${row.telegram_id}`),tariff_name:'ArcVPN',subscription_status:row.subscription_end && String(row.subscription_end)>new Date().toISOString()?'active':'expired',traffic_limit_gb:Number(row.traffic_limit_bytes||0)/1024**3,device_limit:Number(row.device_limit||2),node_traffic:{main:Number(row.main_bytes||0),lte:Number(row.lte_bytes||0)},total_bytes:Number(row.total_bytes||0) })),
      nodes:[{node_uuid:'main',node_name:'Основной трафик',country_code:''},{node_uuid:'lte',node_name:'LTE-трафик',country_code:''}], total:Number(raw.total||0),offset:Number(raw.offset||0),limit:Number(raw.limit||50),period_days:Number(params.period||30),available_tariffs:['ArcVPN'],available_statuses:['active','expired'],
    };

    trafficCache.set(key, { data, timestamp: Date.now() });

    // Evict oldest entries to prevent unbounded memory growth
    if (trafficCache.size > MAX_CACHE_ENTRIES) {
      const iterator = trafficCache.keys();
      while (trafficCache.size > MAX_CACHE_ENTRIES) {
        const oldest = iterator.next();
        if (oldest.done) break;
        trafficCache.delete(oldest.value);
      }
    }

    return data;
  },

  getCached: (params: TrafficParams): TrafficUsageResponse | null => {
    const key = buildCacheKey(params);
    const cached = trafficCache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.data;
    }
    return null;
  },

  invalidateCache: () => {
    trafficCache.clear();
  },

  getEnrichment: async (options?: { skipCache?: boolean }): Promise<TrafficEnrichmentResponse> => {
    if (
      !options?.skipCache &&
      enrichmentCache.data &&
      Date.now() - enrichmentCache.timestamp < CACHE_TTL
    ) {
      return enrichmentCache.data;
    }

    const raw = await adminModuleJson('/api/admin/traffic?limit=100&offset=0', { items: [] });
    const data: TrafficEnrichmentResponse = { data: Object.fromEntries((raw.items || []).map((row: Record<string, unknown>) => [Number(row.user_id), { devices_connected:0,total_spent_kopeks:0,subscription_start_date:null,subscription_end_date:row.subscription_end?String(row.subscription_end):null,last_node_name:null }])) };
    enrichmentCache.data = data;
    enrichmentCache.timestamp = Date.now();
    return data;
  },

  exportCsv: async (data: {
    period: number;
    start_date?: string;
    end_date?: string;
    tariffs?: string;
    statuses?: string;
    nodes?: string;
    total_threshold_gb?: number;
    node_threshold_gb?: number;
  }): Promise<ExportCsvResponse> => {
    const rows: UserTrafficItem[] = [];
    let offset = 0;
    const limit = 100;
    while (true) {
      const page = await adminTrafficApi.getTrafficUsage({
        ...data,
        limit,
        offset,
      }, { skipCache: true });
      rows.push(...page.items);
      offset += page.items.length;
      if (!page.items.length || offset >= page.total) break;
    }
    const quote = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const csv = [
      ['Telegram ID', 'Username', 'Имя', 'Статус', 'Основной байт', 'LTE байт', 'Всего байт', 'Лимит ГБ'],
      ...rows.map((row) => [row.telegram_id, row.username, row.full_name, row.subscription_status,
        row.node_traffic.main || 0, row.node_traffic.lte || 0, row.total_bytes, row.traffic_limit_gb]),
    ].map((line) => line.map(quote).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `arcvpn-traffic-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    return { success: true, message: `Выгружено строк: ${rows.length}` };
  },
};
