import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import ArcBenchmarks from './ArcBenchmarks';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getJson, getOverview } from '@/arcvpn/api';
import {
  ChartIcon,
  HeartbeatIcon,
  ServerIcon,
  HistoryIcon,
  BoltIcon,
  GlobeIcon,
  BackIcon,
} from '../components/icons';

type Sample = {
  sampled_at: string;
  state?: string;
  cpu_pct?: number;
  mem_pct?: number;
  disk_used_pct?: number;
  net_rx_bps?: number;
  net_tx_bps?: number;
  load_1m?: number;
  packet_loss_pct?: number;
  latency_ms?: number;
  uptime_seconds?: number;
};
type OperatorProbe = {
  batch_id: string;
  operator: string;
  target_path: string;
  test_kind: string;
  restriction_state: string;
  region?: string;
  outcome: string;
  rtt_ms?: number;
  checked_at: string;
  reason?: string;
};
type NodeEvent = { action: string; outcome: string; created_at: string; summary?: string };
type AvailabilityPoint = {
  status: 'healthy' | 'server_down' | 'possible_ip_block' | 'unknown';
  checked_at: string;
};
type NodeInfo = {
  address: string;
  name?: string;
  country_code?: string;
  connected?: boolean;
  disabled?: boolean;
  users_online?: number;
  xray_uptime_seconds?: number;
  diagnostic?: { ok: boolean };
  inbounds?: { tag?: string; type?: string }[];
};
type EdgeInfo = {
  id: string;
  name: string;
  origin?: string;
  public_host: string;
  inbound_active: boolean;
};
type Overview = {
  remnawave?: { nodes?: NodeInfo[]; lte_edges?: EdgeInfo[] };
  servers?: {
    host: string;
    name?: string;
    provider?: string;
    location?: string;
    capacity_mbps?: number;
  }[];
};
type Capacity = {
  network_user_estimate?: {additional_users:number;assumed_mbps_per_user:number;reserve_pct:number;measured_floor_mbps:number} | null;
  coverage_ok: boolean;
  samples: number;
  network: {
    rx?: { confirmed_mbps: number | null; headroom_pct: number | null };
    tx?: { confirmed_mbps: number | null; headroom_pct: number | null };
  };
  warnings: string[];
};
type Period = '15m' | '1h' | '6h' | '24h' | '7d';
type NodeTab = 'overview' | 'metrics' | 'services' | 'logs' | 'performance' | 'availability';
const nodeTabs = [
  { key: 'overview', label: 'Обзор', icon: HeartbeatIcon },
  { key: 'metrics', label: 'Метрики', icon: ChartIcon },
  { key: 'services', label: 'Сервисы', icon: ServerIcon },
  { key: 'logs', label: 'Логи', icon: HistoryIcon },
  { key: 'performance', label: 'Нагрузка', icon: BoltIcon },
  { key: 'availability', label: 'Доступность CDN', icon: GlobeIcon },
] as const;
const periods: Period[] = ['15m', '1h', '6h', '24h', '7d'];
const finite = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;
const percent = (value: unknown) => (finite(value) === null ? '—' : `${Number(value).toFixed(1)}%`);
const speed = (value: unknown) =>
  finite(value) === null ? '—' : `${(Number(value) / 1_000_000).toFixed(1)} Мбит/с`;
const uptime = (value: unknown) =>
  finite(value) === null
    ? '—'
    : `${Math.floor(Number(value) / 86400)} д ${Math.floor((Number(value) % 86400) / 3600)} ч`;
const operatorTime = (value: string) => {
  const date = new Date(`${value.replace(' ', 'T')}Z`);
  return Number.isNaN(date.getTime())
    ? value
    : `${date.toLocaleString('ru-RU', { timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} МСК`;
};
const quantile = (items: number[], q: number) =>
  items.length ? [...items].sort((a, b) => a - b)[Math.floor((items.length - 1) * q)] : null;
const capacityWarningText: Record<string, string> = {
  rx_capacity_critical: 'запас загрузки ниже 15%',
  tx_capacity_critical: 'запас отдачи ниже 15%',
  rx_capacity_low: 'запас загрузки ниже 30%',
  tx_capacity_low: 'запас отдачи ниже 30%',
  cpu_sustained_high: 'CPU p95 выше 85%',
  memory_sustained_high: 'память p95 выше 90%',
};

function Chart({
  title,
  values,
  labels,
  suffix,
  tone,
}: {
  title: string;
  values: (number | null)[];
  labels: string[];
  suffix: string;
  tone: string;
}) {
  const valid = values.filter((n): n is number => n !== null);
  const data = values.map((value, index) => ({
    time: labels[index]?.slice(11, 16) || String(index),
    value,
  }));
  return (
    <article className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-semibold text-dark-100">{title}</h3>
        <strong className="font-mono text-sm text-dark-200">
          {valid.length ? `${valid[valid.length - 1].toFixed(1)}${suffix}` : 'Нет данных'}
        </strong>
      </div>
      {valid.length > 1 ? (
        <div className="mt-4 h-48" role="img" aria-label={`${title}: ${valid.length} измерений`}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -24 }}>
              <CartesianGrid stroke="#263243" strokeDasharray="3 5" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: '#8190a3', fontSize: 10 }}
                minTickGap={36}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={suffix === '%' ? [0, 100] : [0, 'auto']}
                tick={{ fill: '#8190a3', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: '#121a29',
                  border: '1px solid #334155',
                  borderRadius: 12,
                  color: '#e8f0fa',
                }}
                formatter={(value) => [`${Number(value).toFixed(1)}${suffix}`, title]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={tone}
                fill={tone}
                fillOpacity={0.12}
                strokeWidth={2}
                connectNulls={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="mt-4 flex h-40 items-center justify-center text-sm text-dark-400">
          Нет ряда измерений
        </p>
      )}
    </article>
  );
}

function OperatorMark({ code, name }: { code: string; name: string }) {
  return <img src={`/admin/operators/${code}.svg`} alt={name}
    className="h-7 max-w-[120px] object-contain" />;
}

export default function ArcNodeDetail() {
  const { host = '' } = useParams();
  const [period, setPeriod] = useState<Period>('1h');
  const [tab, setTab] = useState<NodeTab>('overview');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [operatorProbes, setOperatorProbes] = useState<OperatorProbe[]>([]);
  const [operatorNetwork, setOperatorNetwork] = useState<{operators: {id: string; online: boolean}[]; regions: {id: string; name: string}[]} | null>(null);
  const [operatorRunMessage, setOperatorRunMessage] = useState('');
  const [operatorRunBaseline, setOperatorRunBaseline] = useState<string | null>(null);
  const [events, setEvents] = useState<NodeEvent[]>([]);
  const [availability, setAvailability] = useState<AvailabilityPoint[]>([]);
  const [documentedNodes, setDocumentedNodes] = useState<
    Array<{ host: string; role?: string; location?: string; status?: string }>
  >([]);
  const [capacity, setCapacity] = useState<Capacity | null>(null);
  const [demandMbps,setDemandMbps] = useState(10);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (import.meta.env.DEV) return;
    let active = true;
    getJson('/api/admin/nodes/operator-network-status').then((data) => {
      if (active) setOperatorNetwork(data as typeof operatorNetwork);
    }).catch(() => { if (active) setOperatorNetwork(null); });
    return () => { active = false; };
  }, [host]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setSamples([]);
    setOperatorProbes([]);
    setEvents([]);
    setAvailability([]);
    setCapacity(null);
    const metricsRequest = import.meta.env.DEV
      ? Promise.resolve({
          samples: Array.from({ length: 60 }, (_, i) => ({
            sampled_at: new Date(Date.now() - (59 - i) * 60_000)
              .toISOString()
              .replace('T', ' ')
              .slice(0, 19),
            state: 'healthy',
            cpu_pct: 18 + Math.sin(i / 6) * 8,
            mem_pct: 42 + Math.sin(i / 13) * 2,
            disk_used_pct: 37,
            net_rx_bps: 12_000_000 + Math.sin(i / 4) * 4_000_000,
            net_tx_bps: 7_000_000 + Math.sin(i / 8) * 3_000_000,
          })),
        })
      : getJson(`/api/admin/nodes/metrics?host=${encodeURIComponent(host)}&range=${period}`);
    const operatorRequest = import.meta.env.DEV
      ? Promise.resolve({ results: [] })
      : getJson(`/api/admin/nodes/operator-probes?host=${encodeURIComponent(host)}`);
    const registryRequest = import.meta.env.DEV
      ? Promise.resolve({ nodes: [] })
      : getJson('/api/admin/nodes/registry');
    const capacityRequest = import.meta.env.DEV
      ? Promise.resolve(null)
      : getJson(`/api/admin/nodes/capacity?host=${encodeURIComponent(host)}&range=${period}&demand_mbps=${demandMbps}`);
    const eventsRequest = import.meta.env.DEV
      ? Promise.resolve({ events: [] })
      : getJson(`/api/admin/nodes/events?host=${encodeURIComponent(host)}`);
    const availabilityRequest = import.meta.env.DEV
      ? Promise.resolve({ samples: [] })
      : getJson(`/api/admin/nodes/uptime-history?host=${encodeURIComponent(host)}`);
    Promise.allSettled([
      getOverview(),
      metricsRequest,
      operatorRequest,
      registryRequest,
      capacityRequest,
      eventsRequest,
      availabilityRequest,
    ])
      .then(
        ([
          data,
          metrics,
          operatorResult,
          registry,
          capacityResult,
          eventsResult,
          availabilityResult,
        ]) => {
          if (!active) return;
          if (data.status === 'fulfilled') setOverview(data.value as Overview);
          else setError('Сводка ноды недоступна');
          if (metrics.status === 'fulfilled') setSamples(metrics.value.samples || []);
          else setError('История телеметрии недоступна');
          if (operatorResult.status === 'fulfilled')
            setOperatorProbes(operatorResult.value.results || []);
          if (registry.status === 'fulfilled') setDocumentedNodes(registry.value.nodes || []);
          if (capacityResult.status === 'fulfilled')
            setCapacity(capacityResult.value as Capacity | null);
          if (eventsResult.status === 'fulfilled') setEvents(eventsResult.value.events || []);
          if (availabilityResult.status === 'fulfilled')
            setAvailability(availabilityResult.value.samples || []);
        },
      )
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [host, period, demandMbps]);
  useEffect(() => {
    if (operatorRunBaseline === null) return;
    let polls = 0;
    const interval = window.setInterval(async () => {
      polls += 1;
      try {
        const result = await getJson(`/api/admin/nodes/operator-probes?host=${encodeURIComponent(host)}`);
        const rows = (result.results || []) as OperatorProbe[];
        if (rows[0]?.batch_id && rows[0].batch_id !== operatorRunBaseline) {
          setOperatorProbes(rows);
          setOperatorRunMessage('Проверка завершена. Результаты обновлены.');
          setOperatorRunBaseline(null);
          return;
        }
      } catch {
        // Retry while the bounded worker is running.
      }
      if (polls >= 36) {
        setOperatorRunMessage('Проверка ещё выполняется. Результат появится в истории.');
        setOperatorRunBaseline(null);
      }
    }, 10_000);
    return () => window.clearInterval(interval);
  }, [host, operatorRunBaseline]);
  const runAllOperators = async () => {
    setOperatorRunMessage('Запускаем проверку…');
    try {
      await getJson('/api/admin/nodes/operator-probes/run', { method: 'POST', body: '{}' });
      setOperatorRunMessage('Проверяем все доступные сети и обе LTE-ноды…');
      setOperatorRunBaseline(operatorProbes[0]?.batch_id || 'none');
    } catch (failure) {
      const code = failure instanceof Error ? failure.message : '';
      setOperatorRunMessage(code.includes('429')
        ? 'Повторный запуск доступен через 15 минут после предыдущей проверки.'
        : code.includes('409') ? 'Проверка уже выполняется.' : 'Не удалось запустить проверку.');
    }
  };
  const node = overview?.remnawave?.nodes?.find((item) => item.address === host);
  const server = overview?.servers?.find((item) => item.host === host);
  const documented = documentedNodes.find((item) => item.host === host);
  const latest = samples[samples.length - 1];
  const fresh = latest && Date.now() - new Date(`${latest.sampled_at}Z`).getTime() < 180_000;
  const rx95 = useMemo(
    () =>
      quantile(
        samples.map((s) => finite(s.net_rx_bps)).filter((n): n is number => n !== null),
        0.95,
      ),
    [samples],
  );
  const tx95 = useMemo(
    () =>
      quantile(
        samples.map((s) => finite(s.net_tx_bps)).filter((n): n is number => n !== null),
        0.95,
      ),
    [samples],
  );
  const configuredMbps = finite(server?.capacity_mbps);
  const verifiedRx = capacity?.network?.rx?.confirmed_mbps;
  const verifiedTx = capacity?.network?.tx?.confirmed_mbps;
  const headroom = [
    capacity?.network?.rx?.headroom_pct,
    capacity?.network?.tx?.headroom_pct,
  ].filter((item): item is number => typeof item === 'number');
  const confirmedHeadroom = headroom.length === 2 ? Math.min(...headroom) : null;
  const stale = !fresh && samples.length > 0;
  const availabilityBins = useMemo(() => {
    const end = Date.now();
    const width = 30 * 60_000;
    const bins: AvailabilityPoint['status'][][] = Array.from({ length: 48 }, () => []);
    for (const point of availability) {
      const parsed = Date.parse(
        point.checked_at.includes('T')
          ? point.checked_at
          : `${point.checked_at.replace(' ', 'T')}Z`,
      );
      if (!Number.isFinite(parsed)) continue;
      const index = Math.floor((parsed - (end - 48 * width)) / width);
      if (index >= 0 && index < bins.length) bins[index].push(point.status);
    }
    return bins.map((statuses) =>
      statuses.includes('server_down')
        ? 'server_down'
        : statuses.includes('possible_ip_block')
          ? 'possible_ip_block'
          : statuses.length && statuses.every((status) => status === 'healthy')
            ? 'healthy'
            : 'unknown',
    ).filter((status) => status !== 'unknown');
  }, [availability]);
  const measuredBins = availabilityBins;
  const availabilityPercent = measuredBins.length
    ? Math.round(
        (100 * measuredBins.filter((status) => status === 'healthy').length) / measuredBins.length,
      )
    : null;
  const status = documented?.status?.includes('retired')
    ? 'Выведена из эксплуатации (по реестру)'
    : !node
      ? 'Нет записи Remnawave'
      : node.disabled
        ? 'Выключена в Remnawave'
        : node.connected
          ? 'В сети Remnawave'
          : 'Нет связи Remnawave';
  const operatorNames: Record<string, string> = {
    t2: 'T2',
    t_mobile: 'Т-Мобайл',
    megafon: 'МегаФон',
    beeline: 'Билайн',
    mts: 'МТС',
  };
  const isLte =
    /lte|cdn|xhttp/i.test(`${node?.name || ''} ${server?.name || ''}`) ||
    (overview?.remnawave?.lte_edges || []).some((edge) => edge.origin === host) ||
    operatorProbes.length > 0;
  return (
    <div className="space-y-6 p-4 pb-24 md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/admin/remnawave?tab=nodes" className="inline-flex items-center gap-2 rounded-xl border border-dark-700 px-3 py-2 text-sm text-accent-300 hover:bg-dark-800">
            <BackIcon className="h-4 w-4" /> К списку нод
          </Link>
          <h1 className="mt-2 text-3xl font-semibold text-dark-100">
            {node?.name || server?.name || host}
          </h1>
          <p className="mt-2 text-sm text-dark-400">
            {server?.location || documented?.location || node?.country_code || 'Расположение не подтверждено'} ·{' '}
            {server?.provider || (['87.251.19.197', '151.241.137.174'].includes(host) ? 'One Cent Host' : 'Провайдер не указан')} · {host}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-dark-700 px-3 py-1.5 text-dark-200">{status}</span>
        <span className="rounded-full bg-dark-700 px-3 py-1.5 text-dark-200">
          Роль: {documented?.role || 'Не указана'}
        </span>
        <span
          className={`rounded-full px-3 py-1.5 ${fresh ? 'bg-success-500/15 text-success-400' : 'bg-warning-500/15 text-warning-400'}`}
        >
          Агент: {fresh ? 'данные свежие' : 'нет свежих данных'}
        </span>
        <span className="px-2 py-1.5 text-dark-400">
          Последняя точка: {latest?.sampled_at || '—'}
        </span>
      </div>
      <nav
        aria-label="Разделы ноды"
        className="scrollbar-hide -mx-4 flex gap-1 overflow-x-auto border-b border-dark-700 px-4 md:mx-0 md:px-0"
      >
        {nodeTabs
          .filter(
            (item) =>
              (item.key !== 'availability' || (isLte && operatorProbes.length > 0)) &&
              (item.key !== 'logs' || events.length > 0),
          )
          .map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setTab(item.key)}
              aria-current={tab === item.key ? 'page' : undefined}
              className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm transition-colors ${tab === item.key ? 'border-accent-400 text-dark-100' : 'border-transparent text-dark-400 hover:text-dark-100'}`}
            >
              <item.icon className="h-4 w-4 text-accent-300" />
              {item.label}
            </button>
          ))}
      </nav>
      {error && (
        <p role="alert" className="rounded-xl border border-error-500/30 p-4 text-error-400">
          {error}
        </p>
      )}
      {loading ? (
        <p className="text-dark-400">Загружаем телеметрию…</p>
      ) : (
        <>
          {tab === 'overview' && (
            <>
              <section className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-dark-700 bg-dark-800/40 p-4">
                  <p className="text-xs text-dark-400">
                    {fresh && finite(latest?.uptime_seconds) !== null
                      ? 'Аптайм системы'
                      : 'Аптайм Xray'}
                  </p>
                  <strong className="mt-2 block text-xl text-dark-100">
                    {uptime(
                      fresh && finite(latest?.uptime_seconds) !== null
                        ? latest?.uptime_seconds
                        : node?.xray_uptime_seconds,
                    )}
                  </strong>
                </div>
                <div className="rounded-xl border border-dark-700 bg-dark-800/40 p-4">
                  <p className="text-xs text-dark-400">Remnawave</p>
                  <strong className="mt-2 block text-xl text-dark-100">
                    {!node
                      ? 'Нет записи'
                      : node.disabled
                        ? 'Выключена'
                        : node.connected
                          ? 'На связи'
                          : 'Нет связи'}
                  </strong>
                </div>
                <div className="rounded-xl border border-dark-700 bg-dark-800/40 p-4">
                  <p className="text-xs text-dark-400">Последний глубокий тест</p>
                  <strong className="mt-2 block text-xl text-dark-100">
                    {node?.diagnostic
                      ? node.diagnostic.ok
                        ? 'Пройден'
                        : 'Не пройден'
                      : 'Нет результата'}
                  </strong>
                </div>
              </section>
              <section className="grid items-start gap-4 xl:grid-cols-[2fr_1fr]">
                <div className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                  <h2 className="mb-4 font-semibold text-dark-100">Сейчас</h2>
                  <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    {[
                      ['CPU', percent(fresh && latest?.cpu_pct)],
                      ['Память', percent(fresh && latest?.mem_pct)],
                      ['Сеть ↓', speed(fresh && latest?.net_rx_bps)],
                      ['Сеть ↑', speed(fresh && latest?.net_tx_bps)],
                    ].map(([label, value]) => (
                      <div key={label} className="min-w-0 rounded-xl bg-dark-900/60 p-3.5">
                        <div className="text-xs text-dark-400">{label}</div>
                        <strong className="mt-2 block break-words font-mono text-base text-dark-100 2xl:text-lg">
                          {value}
                        </strong>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5">
                    <div className="mb-2 flex justify-between gap-3 text-xs text-dark-400">
                      <span>Доступность · последние 24 часа</span>
                      <span>
                        {availabilityPercent === null
                          ? 'Нет проверок'
                          : `${availabilityPercent}% · ${measuredBins.length} проверенных интервалов`}
                      </span>
                    </div>
                    <div className="flex min-w-0 gap-0.5">
                      {availabilityBins.map((state, i) => (
                        <span
                          key={i}
                          title={`Проверенный интервал ${i + 1}: ${state === 'healthy' ? 'доступна' : 'проверка не прошла'}`}
                          className={`h-8 min-w-0 flex-1 rounded ${state === 'healthy' ? 'bg-success-500/60' : state === 'possible_ip_block' ? 'bg-warning-500/70' : 'bg-dark-600/70'}`}
                        />
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-dark-500">
                      Показаны только проверенные интервалы. Серый — проверка не прошла.
                    </p>
                  </div>
                </div>
                <div className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                  <h2 className="mb-4 font-semibold text-dark-100">Сервисы и маршруты</h2>
                  <p className="text-sm text-dark-400">
                    Запись Remnawave: {node ? 'есть' : 'нет'}. Активных inbound:{' '}
                    {node?.inbounds?.length ?? '—'}.
                  </p>
                  <button
                    onClick={() => setTab('services')}
                    className="mt-4 text-sm text-accent-300 hover:underline"
                  >
                    Открыть сервисы →
                  </button>
                </div>
              </section>
              <section className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                <h2 className="font-semibold text-dark-100">Последние события</h2>
                {events.length ? (
                  events.slice(0, 3).map((event, i) => (
                    <p key={`${event.created_at}-${i}`} className="mt-2 text-sm text-dark-300">
                      {event.created_at} · {event.summary || `${event.action} · ${event.outcome}`}
                    </p>
                  ))
                ) : (
                  <p className="mt-2 text-sm text-dark-400">
                    Нет сохранённых событий для этой ноды.
                  </p>
                )}
                {events.length > 0 && (
                  <button
                    onClick={() => setTab('logs')}
                    className="mt-3 text-sm text-accent-300 hover:underline"
                  >
                    Открыть журнал →
                  </button>
                )}
              </section>
            </>
          )}
          {tab === 'performance' && (
            <>
            <section className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                <h2 className="mb-4 font-semibold text-dark-100">Нагрузка и запас</h2>
                <div className="mb-5 grid grid-cols-2 gap-4">
                  <div><p className="text-sm text-dark-400">Людей сейчас</p><p className="mt-2 text-3xl font-semibold text-dark-100">{node?.users_online ?? '—'}</p></div>
                  <div><p className="text-sm text-dark-400">Теоретически ещё по сети</p><p className="mt-2 text-xl font-semibold text-dark-100">{capacity?.network_user_estimate ? `${capacity.network_user_estimate.additional_users} чел.` : 'Оценка не готова'}</p></div>
                </div>
                <div className="mb-4 flex flex-wrap gap-4 text-sm"><label>Окно нагрузки <select className="rounded-lg bg-dark-900 p-2" value={period} onChange={e=>setPeriod(e.target.value as Period)}>{periods.map(p=><option key={p} value={p}>{p}</option>)}</select></label><label>На человека <select className="rounded-lg bg-dark-900 p-2" value={demandMbps} onChange={e=>setDemandMbps(Number(e.target.value))}>{[5,10,20].map(n=><option key={n} value={n}>{n} Мбит/с</option>)}</select></label></div>
                <p className="mb-4 text-sm text-dark-400">Расчёт по минимальной скорости пяти городов РФ, устойчивой нагрузке выбранного окна и запасу 30%. Это сценарий по сети, а не подтверждённая комфортная ёмкость: расход памяти и CPU на новых людей ещё не измерен. При высокой нагрузке CPU/RAM запас считается нулевым.</p>
                <details><summary className="mb-3 cursor-pointer text-sm text-primary-300">Как рассчитывается запас</summary>
                <dl className="space-y-3 text-sm">
                  {[
                    ['Наблюдаемый p95 сети ↓', speed(rx95)],
                    ['Наблюдаемый p95 сети ↑', speed(tx95)],
                    [
                      'Покрытие выбранного окна',
                      capacity?.coverage_ok ? `${capacity.samples} точек` : 'Недостаточно данных',
                    ],
                    [
                      'Проверенная ёмкость ↓ / ↑',
                      verifiedRx && verifiedTx
                        ? `${verifiedRx} / ${verifiedTx} Мбит/с`
                        : 'Не измерена',
                    ],
                    [
                      'Запас по p95 ↓ / ↑',
                      confirmedHeadroom === null
                        ? 'Недостаточно данных'
                        : `${capacity?.network?.rx?.headroom_pct}% / ${capacity?.network?.tx?.headroom_pct}%`,
                    ],
                    ['Дополнительных пользователей', 'Нет достоверной оценки'],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="flex justify-between gap-3 border-b border-dark-700 pb-2"
                    >
                      <dt className="text-dark-400">{label}</dt>
                      <dd className="text-right font-medium text-dark-100">{value}</dd>
                    </div>
                  ))}
                </dl></details>
                <p className="mt-4 text-xs text-dark-400">
                  Настроенный порт: {configuredMbps ? `${configuredMbps} Мбит/с` : 'не указан'}. Он
                  не заменяет проверенный замер. Подтверждённая комфортная ёмкость требует наблюдения за
                  нагрузкой на одного активного пользователя.
                </p>
                {stale && (
                  <p className="mt-3 text-sm text-warning-400">
                    Телеметрия устарела; текущее состояние неизвестно.
                  </p>
                )}
                {capacity?.warnings?.length ? (
                  <p className="mt-3 text-sm text-warning-400">
                    Устойчивый запас снижен:{' '}
                    {capacity.warnings
                      .map((warning) => capacityWarningText[warning] || warning)
                      .join(', ')}
                    . Стоит подготовить дополнительную ёмкость.
                  </p>
                ) : null}
              </div>
            </section>
            <ArcBenchmarks host={host} />
            </>
          )}
          {tab === 'metrics' && (
            <>
              <div className="flex flex-wrap gap-2" aria-label="Период метрик">
                {periods.map((p) => (
                  <button
                    key={p}
                    aria-pressed={period === p}
                    onClick={() => setPeriod(p)}
                    className={`rounded-xl px-4 py-2 text-sm ${period === p ? 'bg-accent-500/20 text-accent-300' : 'bg-dark-800 text-dark-400 hover:text-dark-100'}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <section className="grid gap-4 lg:grid-cols-2">
                <Chart
                  title="CPU"
                  labels={samples.map((s) => s.sampled_at)}
                  values={samples.map((s) => finite(s.cpu_pct))}
                  suffix="%"
                  tone="#ed9baa"
                />
                <Chart
                  title="Память"
                  labels={samples.map((s) => s.sampled_at)}
                  values={samples.map((s) => finite(s.mem_pct))}
                  suffix="%"
                  tone="#8bbdf3"
                />
                <Chart
                  title="Диск"
                  labels={samples.map((s) => s.sampled_at)}
                  values={samples.map((s) => finite(s.disk_used_pct))}
                  suffix="%"
                  tone="#ad9be8"
                />
                <Chart
                  title="Сеть ↓"
                  labels={samples.map((s) => s.sampled_at)}
                  values={samples.map((s) =>
                    finite(s.net_rx_bps) === null ? null : Number(s.net_rx_bps) / 1_000_000,
                  )}
                  suffix=" Мбит/с"
                  tone="#e9be70"
                />
                <Chart
                  title="Сеть ↑"
                  labels={samples.map((s) => s.sampled_at)}
                  values={samples.map((s) =>
                    finite(s.net_tx_bps) === null ? null : Number(s.net_tx_bps) / 1_000_000,
                  )}
                  suffix=" Мбит/с"
                  tone="#76cfaa"
                />
              </section>
            </>
          )}
          {tab === 'services' && (
            <section className="grid gap-4 lg:grid-cols-2">
              <article className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                <h2 className="font-semibold text-dark-100">Remnawave и подписка</h2>
                <p className="mt-2 text-sm text-dark-400">
                  Подключение:{' '}
                  {node
                    ? node.disabled
                      ? 'выключена'
                      : node.connected
                        ? 'в сети'
                        : 'не в сети'
                    : 'нет записи'}{' '}
                  · пользователей сейчас: {node?.users_online ?? '—'}
                </p>
                <div className="mt-4 space-y-2">
                  {node?.inbounds?.length ? (
                    node.inbounds.map((inbound: { tag?: string; type?: string }, i: number) => (
                      <div
                        key={`${inbound.tag}-${i}`}
                        className="rounded-lg bg-dark-900/60 p-3 text-sm text-dark-200"
                      >
                        {inbound.tag || inbound.type || 'Inbound без названия'}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-dark-400">Состав inbound не получен.</p>
                  )}
                </div>
              </article>
              <article className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
                <h2 className="font-semibold text-dark-100">Связанные профили</h2>
                <div className="mt-4 space-y-2">
                  {(overview?.remnawave?.lte_edges || [])
                    .filter((edge: { origin?: string }) => edge.origin === host)
                    .map(
                      (edge: {
                        id: string;
                        name: string;
                        public_host: string;
                        inbound_active: boolean;
                      }) => (
                        <div
                          key={edge.id}
                          className="rounded-lg bg-dark-900/60 p-3 text-sm text-dark-200"
                        >
                          <b>{edge.name}</b>
                          <span className="mt-1 block text-xs text-dark-400">
                            CDN: {edge.public_host} · inbound{' '}
                            {edge.inbound_active ? 'присутствует' : 'отсутствует'}
                          </span>
                        </div>
                      ),
                    )}
                  {!(overview?.remnawave?.lte_edges || []).some(
                    (edge: { origin?: string }) => edge.origin === host,
                  ) && <p className="text-sm text-dark-400">Связанные CDN-профили не найдены.</p>}
                </div>
              </article>
            </section>
          )}
          {tab === 'logs' && (
            <section className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
              <h2 className="font-semibold text-dark-100">Журнал ноды</h2>
              <p className="mt-1 text-xs text-dark-400">
                Сохранённые диагностики и административные действия
              </p>
              {events.length ? (
                <div className="mt-4 space-y-2">
                  {events.map((event, i) => (
                    <div
                      key={`${event.created_at}-${i}`}
                      className="flex flex-wrap justify-between gap-2 rounded-lg bg-dark-900/60 p-3 text-sm"
                    >
                      <span className="text-dark-200">
                        {event.summary || `${event.action} · ${event.outcome}`}
                      </span>
                      <time className="text-dark-400">{event.created_at}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-dark-400">Событий пока нет.</p>
              )}
            </section>
          )}
          {tab === 'availability' && isLte && (
            <section className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-dark-100">Доступность CDN · мобильные операторы</h2>
                {!import.meta.env.DEV && (
                  <button type="button" onClick={runAllOperators} disabled={operatorRunBaseline !== null}
                    className="inline-flex items-center gap-2 rounded-xl border border-primary-500/40 bg-primary-500/10 px-3 py-2 text-sm font-medium text-primary-300 transition hover:bg-primary-500/20 disabled:cursor-wait disabled:opacity-50">
                    <GlobeIcon className="h-4 w-4" /> Проверить все сети
                  </button>
                )}
              </div>
              {operatorRunMessage && <p role="status" className="mt-2 text-sm text-primary-300">{operatorRunMessage}</p>}
              <p className="mt-1 text-sm text-dark-400">
                Один автоматический запуск проверяет VPN-ключ во всех доступных сетях утром, днём и вечером.
                Контрольные TCP-цели помогают оценить условия сети, но сами по себе не подтверждают режим ограничений.
              </p>
              <p className="mt-2 text-xs text-dark-400">
                Точки LatencyLab: {operatorNetwork?.regions.map((region) => region.name).join(', ') || 'статус провайдера недоступен'}.
                {operatorNetwork?.regions.length === 1 && ' Других активных регионов у провайдера сейчас нет.'}
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                {Object.entries(operatorNames).map(([code, name]) => {
                  const latestProbe = operatorProbes.find((probe) => probe.operator === code);
                  const operatorOffline = operatorNetwork?.operators.find((item) => item.id === code)?.online === false;
                  const tunnel = latestProbe?.test_kind === 'client_tunnel';
                  return (
                    <article
                      key={code}
                      className="rounded-xl border border-dark-700 bg-dark-900/50 p-4"
                    >
                      <div className="inline-flex h-11 items-center rounded-lg bg-white px-3">
                        <OperatorMark code={code} name={name} />
                      </div>
                      <strong
                        className={`mt-3 block text-sm ${latestProbe?.outcome === 'ok' && tunnel && !operatorOffline ? 'text-success-400' : latestProbe?.outcome === 'failed' && tunnel && !operatorOffline ? 'text-error-400' : 'text-dark-400'}`}
                      >
                        {operatorOffline ? 'Оператор офлайн в LatencyLab' : latestProbe
                          ? tunnel
                            ? latestProbe.outcome === 'ok'
                              ? 'VPN подключился'
                              : latestProbe.outcome === 'failed'
                                ? 'VPN не подключился'
                                : latestProbe.reason === 'operator_offline' ? 'Оператор офлайн в LatencyLab' : 'Нет данных'
                            : 'Нет проверки VPN-ключа'
                          : 'Нет проверок'}
                      </strong>
                      <p className="mt-1 text-xs text-dark-400">
                        {operatorOffline ? 'Проверка недоступна у провайдера' : latestProbe
                          ? 'VPN-ключ · условия ограничений не подтверждены'
                          : 'Ожидаются данные оператора'}
                      </p>
                      {latestProbe && (
                        <p className="mt-2 text-[11px] text-dark-500">{operatorTime(latestProbe.checked_at)}</p>
                      )}
                    </article>
                  );
                })}
              </div>
              {operatorProbes.length > 0 && (
                <div className="mt-6 overflow-x-auto">
                  <h3 className="mb-2 text-sm font-semibold text-dark-100">Последние проверки</h3>
                  <table className="w-full text-left text-xs">
                    <thead className="text-dark-400">
                      <tr>
                        <th className="py-2">Время</th>
                        <th>Оператор</th>
                        <th>Результат</th>
                      </tr>
                    </thead>
                    <tbody>
                      {operatorProbes.slice(0, 30).map((probe, i) => (
                        <tr
                          key={`${probe.checked_at}-${probe.operator}-${i}`}
                          className="border-t border-dark-700"
                        >
                          <td className="py-2">{operatorTime(probe.checked_at)}</td>
                          <td>{operatorNames[probe.operator] || probe.operator}</td>
                          <td>
                            {probe.outcome === 'ok'
                              ? 'Успех'
                              : probe.outcome === 'failed'
                                ? 'Сбой'
                                : 'Неизвестно'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
