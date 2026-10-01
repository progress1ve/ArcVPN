import ArcFleetOverview from './ArcFleetOverview';
import { useState, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import ArcNodePreflight from './ArcNodePreflight';
import ArcBalancers from './ArcBalancers';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  adminRemnawaveApi,
  type NodeInfo,
  type NodeRealtimeStats,
  type AutoSyncStatus,
} from '../api/adminRemnawave';
import { usePlatform } from '../platform/hooks/usePlatform';
import { formatUptime } from '../utils/format';
import { getFlagEmoji } from '../utils/subscriptionHelpers';
import { StatCard } from '../components/stats';
import {
  ServerIcon,
  ChartIcon,
  GlobeIcon,
  HeartbeatIcon,
  PowerIcon,
  WarningCircleIcon,
  CpuIcon,
  MemoryIcon,
  StatUptimeIcon,
  UsersIcon,
  SyncIcon,
  RefreshIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  RemnawaveIcon,
  XrayIcon,
  DownloadIcon,
  UploadIcon,
  BackIcon,
  ChevronRightIcon,
  GeoCheckIcon,
  RadarIcon,
} from '../components/icons';
import { GeoCheckModal } from '../components/admin/remnawave/GeoCheckModal';
import { buildReachabilityLink } from '../components/admin/reachability/deepLink';
import { useReachabilityAvailable } from '../components/admin/reachability/useReachabilityStatus';
import { usePermissionStore } from '../store/permissions';
import { supportsGeoCheck } from '../utils/nodeVersion';
import { Skeleton, SkeletonGroup } from '../components/ui/skeleton';
import { getJson } from '@/arcvpn/api';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return parseFloat((bytes / k ** i).toFixed(2)) + ' ' + sizes[i];
};

// Алгоритмический ISO 3166-1 alpha-2 → regional indicator. Глобус-fallback
// сохранён для случая пустого кода (важно для UI-плейсхолдеров).
const getCountryFlag = (code: string | null | undefined): string => getFlagEmoji(code) || '🌍';

// The panel's provider.faviconLink is the provider's site URL (e.g.
// "https://waicore.com/"), not an image. Resolve it to an actual favicon
// image via Google's favicon service, the same way the panel renders it.
const providerFaviconUrl = (link: string | null | undefined): string | null => {
  if (!link) return null;
  try {
    const host = new URL(link).hostname;
    return host ? `https://www.google.com/s2/favicons?domain=${host}&sz=64` : null;
  } catch {
    return null;
  }
};

// Realtime interface throughput (bytes/s) → network-style speed, matching the
// panel exactly: the unit step is by 1024 bytes, but the value is shown in bits
// (×8 / 1000), e.g. 341 KB/s → "2728 Kb/s", 1.34 MB/s → "10.72 Mb/s".
const formatSpeed = (bytesPerSec: number): string => {
  const bps = bytesPerSec || 0;
  const bits = bps * 8;
  if (bps < 1024) return `${bits.toFixed(0)} b/s`;
  if (bps < 1024 ** 2) return `${(bits / 1000).toFixed(2)} Kb/s`;
  if (bps < 1024 ** 3) return `${(bits / 1e6).toFixed(2)} Mb/s`;
  return `${(bits / 1e9).toFixed(2)} Gb/s`;
};

function NodeTrafficBreakdown({
  title,
  items,
}: {
  title: string;
  items: { tag: string; downloadBytes: number; uploadBytes: number; totalBytes: number }[];
}) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-medium uppercase tracking-wide text-dark-500">{title}</p>
      {[...items]
        .sort((a, b) => b.totalBytes - a.totalBytes)
        .map((it) => (
          <div
            key={it.tag}
            className="flex items-center justify-between gap-3 rounded-lg bg-dark-900/50 px-2.5 py-1.5"
          >
            <span className="min-w-0 flex-1 truncate text-xs text-dark-200">{it.tag}</span>
            <div className="flex shrink-0 gap-2.5 font-mono text-[11px] text-dark-400">
              <span>↓ {formatBytes(it.downloadBytes)}</span>
              <span>↑ {formatBytes(it.uploadBytes)}</span>
              <span className="font-medium text-dark-300">{formatBytes(it.totalBytes)}</span>
            </div>
          </div>
        ))}
    </div>
  );
}

interface NodeCardProps {
  node: NodeInfo;
  registryState?: string;
  providerName?: string;
  realtime?: NodeRealtimeStats;
  onAction: (uuid: string, action: 'enable' | 'disable' | 'restart') => void;
  isLoading?: boolean;
}

function NodeCard({ node, registryState, providerName, realtime, onAction, isLoading }: NodeCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [geoCheckOpen, setGeoCheckOpen] = useState(false);

  // GeoCheck умеет только узел 3.3.0+; на старом узле кнопку не показываем,
  // чтобы админ не упирался в ошибку панели.
  const canGeoCheck = supportsGeoCheck(node.versions);
  // Ярлык в BSCHEKER: только с правом запуска и при включённой интеграции.
  // Оба хука вызываются безусловно — правило хуков, объединяем результат после.
  const navigate = useNavigate();
  const canRunReachability = usePermissionStore((s) => s.hasPermission('reachability:run'));
  const canManageNodes = usePermissionStore((s) => s.hasPermission('remnawave:write'));
  const reachabilityAvailable = useReachabilityAvailable();
  const canReach = canRunReachability && reachabilityAvailable;

  const isUp = node.is_connected && node.is_node_online && !node.is_disabled;
  const dotColor = node.is_disabled ? 'bg-dark-500' : isUp ? 'bg-success-400' : 'bg-error-400';
  const statusText = node.is_disabled
    ? t('admin.remnawave.nodes.disabled', 'Disabled')
    : isUp
      ? t('admin.remnawave.nodes.online', 'Online')
      : t('admin.remnawave.nodes.offline', 'Offline');

  const s = node.system?.stats;
  const memTotal = s ? s.memoryUsed + s.memoryFree : 0;
  const ramPct = memTotal > 0 && s ? Math.round((s.memoryUsed / memTotal) * 100) : null;
  const loadAvg = s?.loadAvg?.length
    ? s.loadAvg
        .slice(0, 3)
        .map((n) => n.toFixed(2))
        .join('  ')
    : null;
  const rx = s?.interface?.rxBytesPerSec ?? 0;
  const tx = s?.interface?.txBytesPerSec ?? 0;

  const used = node.traffic_used_bytes ?? 0;
  const limit = node.traffic_limit_bytes ?? 0;
  const trafficPct = limit > 0 ? Math.min(100, (used / limit) * 100) : null;

  // Provider name: realtime metrics first, fall back to the node's own provider.
  const providerLabel = providerName || node.provider_name;
  const providerFavicon = providerFaviconUrl(node.provider_favicon);

  // Per-node traffic breakdown (merged from the former Traffic tab) — shown in
  // an accordion that toggles when the card is clicked.
  const inbounds = realtime?.inbounds ?? [];
  const outbounds = realtime?.outbounds ?? [];
  const hasBreakdown = inbounds.length + outbounds.length > 0;

  const ramColorClass =
    ramPct === null
      ? ''
      : ramPct > 85
        ? 'text-error-400'
        : ramPct > 65
          ? 'text-warning-400'
          : 'text-dark-400';

  // Модалка — сосед кликабельного блока, а не его потомок: портал уносит её
  // в document.body только по DOM, а события React прогоняет по дереву
  // компонентов, и клики внутри неё всплывали бы в onClick карточки.
  return (
    <>
      <div
        className={`rounded-xl border border-dark-700 bg-dark-800/50 p-3.5 transition-colors hover:border-dark-600 ${
          hasBreakdown ? 'cursor-pointer' : ''
        }`}
        onClick={hasBreakdown ? () => setExpanded((v) => !v) : undefined}
      >
        {/* Identity + actions */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${dotColor} ${isUp ? 'animate-pulse' : ''}`}
              title={statusText}
            />
            <span className="flex shrink-0 items-center gap-1 rounded-md bg-dark-700/60 px-1.5 py-0.5 text-[11px] text-dark-300">
              <UsersIcon className="h-3 w-3" />
              {node.users_online ?? 0}
            </span>
            <span className="shrink-0 text-base leading-none">
              {getCountryFlag(node.country_code)}
            </span>
            <h3 className="truncate font-semibold text-dark-100">{node.name}</h3>
            {registryState && !registryState.startsWith('active') && <span className="max-w-24 truncate rounded bg-warning-500/15 px-1.5 py-0.5 text-[10px] text-warning-400" title={`Реестр ArcVPN: ${registryState}`}>{registryState.includes('retired') ? 'Выведена' : 'Подготовка'}</span>}
            {(providerLabel || providerFavicon) && (
              <span className="flex min-w-0 max-w-[7rem] shrink items-center gap-1 rounded-md bg-accent-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-accent-300">
                {providerFavicon && (
                  <img
                    src={providerFavicon}
                    alt=""
                    className="h-3 w-3 shrink-0 rounded-[2px]"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                )}
                {providerLabel && <span className="truncate">{providerLabel}</span>}
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <Link to={`/admin/remnawave/nodes/${encodeURIComponent(node.address)}`} onClick={(event) => event.stopPropagation()} className="rounded-lg bg-accent-500/15 px-2.5 py-1.5 text-xs font-medium text-accent-300 hover:bg-accent-500/25" aria-label={`Открыть статистику ${node.name}`}>Статистика ↗</Link>
            {canReach && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(buildReachabilityLink({ targets: [{ kind: 'node', ref: node.uuid }] }));
                }}
                className="rounded-lg bg-dark-700 p-1.5 text-dark-300 transition-colors hover:bg-dark-600 hover:text-dark-100"
                title={t('admin.reachability.shortcuts.checkNode')}
                aria-label={t('admin.reachability.shortcuts.checkNode')}
              >
                <RadarIcon className="h-3.5 w-3.5" />
              </button>
            )}
            {canGeoCheck && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setGeoCheckOpen(true);
                }}
                disabled={node.is_disabled || !node.is_connected}
                className="rounded-lg bg-dark-700 p-1.5 text-dark-300 transition-colors hover:bg-dark-600 hover:text-dark-100 disabled:cursor-not-allowed disabled:opacity-50"
                title={t('admin.remnawave.geoCheck.title', 'GeoCheck')}
                aria-label={t('admin.remnawave.geoCheck.title', 'GeoCheck')}
              >
                <GeoCheckIcon className="h-3.5 w-3.5" />
              </button>
            )}
            {canManageNodes && <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(node.uuid, 'restart');
              }}
              disabled={isLoading || node.is_disabled}
              className="rounded-lg bg-dark-700 p-1.5 text-dark-300 transition-colors hover:bg-dark-600 hover:text-dark-100 disabled:cursor-not-allowed disabled:opacity-50"
              title={t('admin.remnawave.nodes.restart', 'Restart')}
            >
              <ArrowPathIcon className="h-3.5 w-3.5" />
            </button>}
            {canManageNodes && <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(node.uuid, node.is_disabled ? 'enable' : 'disable');
              }}
              disabled={isLoading}
              className={`rounded-lg p-1.5 transition-colors disabled:opacity-50 ${
                node.is_disabled
                  ? 'bg-success-500/20 text-success-400 hover:bg-success-500/30'
                  : 'bg-error-500/20 text-error-400 hover:bg-error-500/30'
              }`}
              title={
                node.is_disabled
                  ? t('admin.remnawave.nodes.enable', 'Enable')
                  : t('admin.remnawave.nodes.disable', 'Disable')
              }
            >
              {node.is_disabled ? (
                <PlayIcon className="h-3.5 w-3.5" />
              ) : (
                <StopIcon className="h-3.5 w-3.5" />
              )}
            </button>}
            {hasBreakdown && (
              <ChevronRightIcon
                className={`h-4 w-4 text-dark-500 transition-transform ${
                  expanded ? 'rotate-90' : ''
                }`}
              />
            )}
          </div>
        </div>

        {/* Address + traffic + uptime */}
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-dark-400">
          <span className="flex min-w-0 max-w-full items-center gap-1 font-mono text-dark-500">
            <GlobeIcon className="h-3 w-3 shrink-0" />
            <span className="truncate">{node.address}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="text-dark-300">{formatBytes(used)}</span>
            {trafficPct !== null && (
              <span className="h-1 w-16 overflow-hidden rounded-full bg-dark-700">
                <span
                  className="block h-full rounded-full bg-accent-500"
                  style={{ width: `${trafficPct}%` }}
                />
              </span>
            )}
            <span className="text-dark-500">/ {limit > 0 ? formatBytes(limit) : '∞'}</span>
          </span>
          {node.xray_uptime > 0 && (
            <span className="flex items-center gap-1 text-dark-500">
              <StatUptimeIcon className="h-3 w-3" />
              {formatUptime(node.xray_uptime)}
            </span>
          )}
        </div>

        {/* Live metrics — mobile: 3 fixed rows so wrapping speeds don't reflow;
          desktop (sm+): the original single wrap row, wide enough not to jump. */}
        {(ramPct !== null || loadAvg || rx > 0 || tx > 0 || node.versions) && (
          <>
            {/* Mobile: processor · traffic · versions */}
            <div className="mt-2 space-y-1 border-t border-dark-700/60 pt-2 font-mono text-[10.5px] tabular-nums text-dark-500 sm:hidden">
              {(loadAvg || ramPct !== null) && (
                <div className="flex items-center gap-3">
                  {loadAvg && (
                    <span className="flex items-center gap-1" title="load average 1 / 5 / 15 min">
                      <CpuIcon className="h-3 w-3 shrink-0 text-dark-500" />
                      {loadAvg}
                    </span>
                  )}
                  {ramPct !== null && (
                    <span className="flex items-center gap-1.5" title="RAM">
                      <MemoryIcon className="h-3 w-3 shrink-0 text-dark-500" />
                      <span className={ramColorClass}>{ramPct}%</span>
                      <span className="h-1 w-10 overflow-hidden rounded-full bg-dark-700">
                        <span
                          className="block h-full rounded-full bg-dark-400"
                          style={{ width: `${ramPct}%` }}
                        />
                      </span>
                    </span>
                  )}
                </div>
              )}
              {(rx > 0 || tx > 0) && (
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <DownloadIcon className="h-3 w-3 shrink-0 text-success-400" />
                    {formatSpeed(rx)}
                  </span>
                  <span className="flex items-center gap-1">
                    <UploadIcon className="h-3 w-3 shrink-0 text-accent-400" />
                    {formatSpeed(tx)}
                  </span>
                </div>
              )}
              {(node.versions?.node || node.versions?.xray) && (
                <div className="flex items-center gap-3 text-dark-600">
                  {node.versions?.node && (
                    <span className="flex items-center gap-1" title="remnanode">
                      <RemnawaveIcon className="h-3 w-3 shrink-0" />
                      {node.versions.node}
                    </span>
                  )}
                  {node.versions?.xray && (
                    <span className="flex items-center gap-1" title="xray core">
                      <XrayIcon className="h-3 w-3 shrink-0" />
                      {node.versions.xray}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Desktop: single wrap row (original) */}
            <div className="mt-2 hidden flex-wrap items-center gap-x-3 gap-y-1 border-t border-dark-700/60 pt-2 font-mono text-[10.5px] tabular-nums text-dark-500 sm:flex">
              {ramPct !== null && (
                <span className="flex items-center gap-1.5" title="RAM">
                  <MemoryIcon className="h-3 w-3 text-dark-500" />
                  <span className={ramColorClass}>{ramPct}%</span>
                  <span className="h-1 w-10 overflow-hidden rounded-full bg-dark-700">
                    <span
                      className="block h-full rounded-full bg-dark-400"
                      style={{ width: `${ramPct}%` }}
                    />
                  </span>
                </span>
              )}
              {loadAvg && (
                <span className="flex items-center gap-1" title="load average 1 / 5 / 15 min">
                  <CpuIcon className="h-3 w-3 text-dark-500" />
                  {loadAvg}
                </span>
              )}
              <span className="flex items-center gap-2">
                <span className="flex items-center gap-0.5">
                  <DownloadIcon className="h-3 w-3 text-success-400" />
                  {formatSpeed(rx)}
                </span>
                <span className="flex items-center gap-0.5">
                  <UploadIcon className="h-3 w-3 text-accent-400" />
                  {formatSpeed(tx)}
                </span>
              </span>
              {(node.versions?.node || node.versions?.xray) && (
                <span className="ml-auto flex items-center gap-2.5 text-dark-600">
                  {node.versions?.node && (
                    <span className="flex items-center gap-1" title="remnanode">
                      <RemnawaveIcon className="h-3 w-3" />
                      {node.versions.node}
                    </span>
                  )}
                  {node.versions?.xray && (
                    <span className="flex items-center gap-1" title="xray core">
                      <XrayIcon className="h-3 w-3" />
                      {node.versions.xray}
                    </span>
                  )}
                </span>
              )}
            </div>
          </>
        )}

        {/* Per-node traffic accordion (merged from the former Traffic tab) */}
        {expanded && hasBreakdown && (
          <div
            className="mt-3 space-y-3 border-t border-dark-700/60 pt-3"
            onClick={(e) => e.stopPropagation()}
          >
            {inbounds.length > 0 && (
              <NodeTrafficBreakdown
                title={t('admin.remnawave.traffic.inbounds', 'Inbounds')}
                items={inbounds}
              />
            )}
            {outbounds.length > 0 && (
              <NodeTrafficBreakdown
                title={t('admin.remnawave.traffic.outbounds', 'Outbounds')}
                items={outbounds}
              />
            )}
          </div>
        )}
      </div>

      {geoCheckOpen && <GeoCheckModal node={node} onClose={() => setGeoCheckOpen(false)} />}
    </>
  );
}

interface SyncCardProps {
  title: string;
  description: string;
  onAction: () => void;
  isLoading?: boolean;
  lastResult?: { success: boolean; message?: string } | null;
}

function SyncCard({ title, description, onAction, isLoading, lastResult }: SyncCardProps) {
  const { t } = useTranslation();

  return (
    <div className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-dark-100">{title}</h3>
          <p className="mt-1 text-xs text-dark-400">{description}</p>
          {lastResult && (
            <p
              className={`mt-2 text-xs ${lastResult.success ? 'text-success-400' : 'text-error-400'}`}
            >
              {lastResult.message}
            </p>
          )}
        </div>
        <button
          onClick={onAction}
          disabled={isLoading}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-accent-500/20 px-3 py-1.5 text-accent-400 transition-colors hover:bg-accent-500/30 disabled:opacity-50"
        >
          <RefreshIcon spinning={isLoading} />
          {isLoading
            ? t('admin.remnawave.sync.running', 'Running...')
            : t('admin.remnawave.sync.run', 'Run')}
        </button>
      </div>
    </div>
  );
}

interface NodesTabProps {
  nodes: NodeInfo[];
  providerByUuid: Record<string, string>;
  realtimeByUuid: Record<string, NodeRealtimeStats>;
  isLoading: boolean;
  onAction: (uuid: string, action: 'enable' | 'disable' | 'restart') => void;
  isActionLoading: boolean;
}

function NodesTab({
  nodes,
  providerByUuid,
  realtimeByUuid,
  isLoading,
  onAction,
  isActionLoading,
}: NodesTabProps) {
  const { t } = useTranslation();
  const canManage = usePermissionStore((s) => s.hasPermission('remnawave:write'));
  const currentHosts = new Set(['87.251.19.197', '151.241.137.174']);
  const visibleNodes = nodes.filter((node) => currentHosts.has(node.address));
  const { data: registry } = useQuery({ queryKey: ['arcvpn-node-registry'], queryFn: () => import.meta.env.DEV ? Promise.resolve({ nodes: [] }) : getJson('/api/admin/nodes/registry') });
  const documentedNodes = (registry?.nodes || []) as Array<{ host: string; alias: string; role: string; location?: string; status?: string }>;
  const registryOnly = documentedNodes.filter((server) => currentHosts.has(server.host) && !visibleNodes.some((node) => node.address === server.host));

  const stats = useMemo(() => {
    const total = visibleNodes.length;
    const online = visibleNodes.filter((n) => n.is_connected && n.is_node_online && !n.is_disabled).length;
    const offline = visibleNodes.filter(
      (n) => (!n.is_connected || !n.is_node_online) && !n.is_disabled,
    ).length;
    const disabled = visibleNodes.filter((n) => n.is_disabled).length;
    const totalUsers = visibleNodes.reduce((acc, n) => acc + (n.users_online ?? 0), 0);
    return { total, online, offline, disabled, totalUsers };
  }, [visibleNodes]);

  const traffic = useMemo(() => {
    const vals = visibleNodes.map((node) => realtimeByUuid[node.uuid]).filter(Boolean);
    const download = vals.reduce((a, n) => a + (n.downloadBytes ?? 0), 0);
    const upload = vals.reduce((a, n) => a + (n.uploadBytes ?? 0), 0);
    return { download, upload, total: download + upload };
  }, [realtimeByUuid, visibleNodes]);

  if (isLoading) {
    return (
      <SkeletonGroup className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatCard loading />
          <StatCard loading />
          <StatCard loading />
          <StatCard loading />
          <StatCard loading />
        </div>
        <div className="flex gap-2">
          <Skeleton count={3} className="h-9 w-24 shrink-0 rounded-lg" />
        </div>
        <Skeleton variant="card" count={2} className="h-32" />
      </SkeletonGroup>
    );
  }

  return (
    <div className="space-y-4">
      {canManage && <ArcNodePreflight />}
      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5 max-lg:[&>*:last-child:nth-child(odd)]:col-span-2">
        <StatCard
          label={t('admin.remnawave.nodes.stats.total', 'Total')}
          value={stats.total}
          icon={<ServerIcon />}
          tone="accent"
        />
        <StatCard
          label={t('admin.remnawave.nodes.stats.online', 'Online')}
          value={stats.online}
          icon={<HeartbeatIcon />}
          tone="success"
        />
        <StatCard
          label={t('admin.remnawave.nodes.stats.offline', 'Offline')}
          value={stats.offline}
          icon={<WarningCircleIcon />}
          tone="error"
        />
        <StatCard
          label={t('admin.remnawave.nodes.stats.disabled', 'Disabled')}
          value={stats.disabled}
          icon={<PowerIcon />}
          tone="accent"
        />
        <StatCard
          label={t('admin.remnawave.nodes.stats.users', 'Users')}
          value={stats.totalUsers}
          icon={<UsersIcon />}
          tone="accent"
        />
      </div>

      {/* Realtime traffic totals (merged from the former Traffic tab) */}
      {traffic.total > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-xs text-dark-400">
          <span className="font-medium text-dark-300">
            {t('admin.remnawave.traffic.realtimeTitle', 'Realtime traffic')}
          </span>
          <span className="flex items-center gap-1">
            <DownloadIcon className="h-3 w-3 text-success-400" />
            {formatBytes(traffic.download)}
          </span>
          <span className="flex items-center gap-1">
            <UploadIcon className="h-3 w-3 text-accent-400" />
            {formatBytes(traffic.upload)}
          </span>
          <span className="text-dark-300">
            {'Σ'} {formatBytes(traffic.total)}
          </span>
        </div>
      )}

      {/* Nodes List */}
      <div className="space-y-3">
        {visibleNodes.length === 0 ? (
          <p className="py-8 text-center text-dark-400">
            {t('admin.remnawave.nodes.noNodes', 'No nodes found')}
          </p>
        ) : (
          visibleNodes.map((node) => (
            <NodeCard
              key={node.uuid}
              node={node}
              registryState={documentedNodes.find((server) => server.host === node.address)?.status}
              providerName={node.address === '87.251.19.197' || node.address === '151.241.137.174' ? 'One Cent Host' : providerByUuid[node.uuid]}
              realtime={realtimeByUuid[node.uuid]}
              onAction={onAction}
              isLoading={isActionLoading}
            />
          ))
        )}
      </div>
      {registryOnly.length > 0 && <section className="rounded-xl border border-warning-500/25 bg-warning-500/5 p-4"><h3 className="font-semibold text-dark-100">Ноды вне списка Remnawave</h3><p className="mt-1 text-xs text-dark-400">Показаны записи документального реестра. Их актуальность и связность требуют проверки.</p><div className="mt-3 grid gap-2">{registryOnly.map((server) => <Link key={server.host} to={`/admin/remnawave/nodes/${encodeURIComponent(server.host)}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-dark-800 px-3 py-2 text-sm text-dark-200 hover:text-accent-300"><span>{server.alias || server.host} · {server.location || server.host}</span><span className="text-xs text-warning-400">{server.status || 'статус не указан'} · открыть ↗</span></Link>)}</div></section>}
    </div>
  );
}

interface SyncTabProps {
  autoSyncStatus: AutoSyncStatus | undefined;
  isLoading: boolean;
  onRunAutoSync: () => void;
  onSyncFromPanel: () => void;
  onSyncToPanel: () => void;
  syncResults: Record<string, { success: boolean; message?: string } | null>;
  loadingStates: Record<string, boolean>;
}

function SyncTab({
  autoSyncStatus,
  isLoading,
  onRunAutoSync,
  onSyncFromPanel,
  onSyncToPanel,
  syncResults,
  loadingStates,
}: SyncTabProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <SkeletonGroup className="space-y-6">
        <Skeleton variant="card" count={2} className="h-40" />
      </SkeletonGroup>
    );
  }

  return (
    <div className="space-y-6">
      {/* Auto Sync Status */}
      {autoSyncStatus && (
        <div className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-medium text-dark-100">
              <SyncIcon />
              {t('admin.remnawave.sync.autoSync', 'Auto Sync')}
            </h3>
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${
                autoSyncStatus.enabled
                  ? 'bg-success-500/20 text-success-400'
                  : 'bg-dark-600 text-dark-400'
              }`}
            >
              {autoSyncStatus.enabled
                ? t('admin.remnawave.sync.enabled', 'Enabled')
                : t('admin.remnawave.sync.disabled', 'Disabled')}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-dark-700/50 p-3">
              <p className="text-xs text-dark-500">
                {t('admin.remnawave.sync.schedule', 'Schedule')}
              </p>
              <p className="mt-1 text-dark-200">
                {autoSyncStatus.times.length > 0 ? autoSyncStatus.times.join(', ') : '—'}
              </p>
            </div>
            <div className="rounded-lg bg-dark-700/50 p-3">
              <p className="text-xs text-dark-500">{t('admin.remnawave.sync.status', 'Status')}</p>
              <p
                className={`mt-1 ${
                  autoSyncStatus.is_running
                    ? 'text-warning-400'
                    : autoSyncStatus.last_run_success
                      ? 'text-success-400'
                      : 'text-dark-200'
                }`}
              >
                {autoSyncStatus.is_running
                  ? t('admin.remnawave.sync.running', 'Running...')
                  : autoSyncStatus.last_run_success
                    ? t('admin.remnawave.sync.success', 'Success')
                    : autoSyncStatus.last_run_error || '—'}
              </p>
            </div>
            <div className="rounded-lg bg-dark-700/50 p-3">
              <p className="text-xs text-dark-500">
                {t('admin.remnawave.sync.lastRun', 'Last Run')}
              </p>
              <p className="mt-1 text-dark-200">
                {autoSyncStatus.last_run_finished_at
                  ? new Date(autoSyncStatus.last_run_finished_at).toLocaleString()
                  : '—'}
              </p>
            </div>
            <div className="rounded-lg bg-dark-700/50 p-3">
              <p className="text-xs text-dark-500">
                {t('admin.remnawave.sync.nextRun', 'Next Run')}
              </p>
              <p className="mt-1 text-dark-200">
                {autoSyncStatus.next_run ? new Date(autoSyncStatus.next_run).toLocaleString() : '—'}
              </p>
            </div>
          </div>

          <button
            onClick={onRunAutoSync}
            disabled={loadingStates.autoSync || autoSyncStatus.is_running}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500/20 px-4 py-2.5 text-sm font-medium text-accent-400 transition-colors hover:bg-accent-500/30 disabled:opacity-50"
          >
            <RefreshIcon spinning={loadingStates.autoSync || autoSyncStatus.is_running} />
            {autoSyncStatus.is_running
              ? t('admin.remnawave.sync.running', 'Running...')
              : t('admin.remnawave.sync.runAutoSyncNow', 'Run Auto Sync Now')}
          </button>
        </div>
      )}

      {/* Manual Sync */}
      <div className="grid gap-3 sm:grid-cols-2">
        <SyncCard
          title={t('admin.remnawave.sync.fromPanel', 'Sync from Panel')}
          description={t(
            'admin.remnawave.sync.fromPanelDesc',
            'Import users from Remnawave panel to bot',
          )}
          onAction={onSyncFromPanel}
          isLoading={loadingStates.fromPanel}
          lastResult={syncResults.fromPanel}
        />
        <SyncCard
          title={t('admin.remnawave.sync.toPanel', 'Sync to Panel')}
          description={t(
            'admin.remnawave.sync.toPanelDesc',
            'Export users from bot to Remnawave panel',
          )}
          onAction={onSyncToPanel}
          isLoading={loadingStates.toPanel}
          lastResult={syncResults.toPanel}
        />
      </div>
    </div>
  );
}

type TabType = 'overview' | 'nodes' | 'balancers' | 'sync';

export default function AdminRemnawave() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { capabilities } = usePlatform();

  // State
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<TabType>(searchParams.get('tab') === 'nodes' ? 'nodes' : searchParams.get('tab') === 'balancers' ? 'balancers' : 'overview');
  const [syncResults, setSyncResults] = useState<
    Record<string, { success: boolean; message?: string } | null>
  >({});
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});

  // Queries
  const { data: status } = useQuery({
    queryKey: ['admin-remnawave-status'],
    queryFn: adminRemnawaveApi.getStatus,
  });

  const {
    data: nodesData,
    isLoading: isLoadingNodes,
  } = useQuery({
    queryKey: ['admin-remnawave-nodes'],
    queryFn: adminRemnawaveApi.getNodes,
    enabled: activeTab === 'nodes',
    // Fast poll so realtime metrics (RAM, load, speeds) stay live like the panel.
    refetchInterval: 5000,
  });

  const { data: realtimeData } = useQuery({
    queryKey: ['admin-remnawave-realtime'],
    queryFn: adminRemnawaveApi.getNodesRealtime,
    // Realtime carries the provider name + per-node inbound/outbound breakdown
    // that the Nodes tab shows (provider badge + the per-node traffic accordion).
    enabled: activeTab === 'nodes',
    refetchInterval: 10000,
  });

  // Provider name (e.g. "WAICORE") only comes through the realtime stats; map it
  // by node uuid so the Nodes tab can show the provider badge like the panel.
  const providerByUuid = useMemo(() => {
    const map: Record<string, string> = {};
    for (const r of realtimeData ?? []) {
      if (r.providerName) map[r.nodeUuid] = r.providerName;
    }
    return map;
  }, [realtimeData]);

  // Full realtime stats by node uuid — feeds the per-node traffic accordion
  // (inbounds/outbounds) merged into the Nodes tab.
  const realtimeByUuid = useMemo(() => {
    const map: Record<string, NodeRealtimeStats> = {};
    for (const r of realtimeData ?? []) map[r.nodeUuid] = r;
    return map;
  }, [realtimeData]);

  const { data: autoSyncStatus, isLoading: isLoadingAutoSync } = useQuery({
    queryKey: ['admin-remnawave-autosync'],
    queryFn: adminRemnawaveApi.getAutoSyncStatus,
    enabled: activeTab === 'sync',
    refetchInterval: 10000,
  });

  // Mutations
  const nodeActionMutation = useMutation({
    mutationFn: ({ uuid, action }: { uuid: string; action: 'enable' | 'disable' | 'restart' }) =>
      adminRemnawaveApi.nodeAction(uuid, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-remnawave-nodes'] });
    },
  });

  // Handlers
  const handleNodeAction = (uuid: string, action: 'enable' | 'disable' | 'restart') => {
    nodeActionMutation.mutate({ uuid, action });
  };

  const handleSyncAction = async (
    key: string,
    action: () => Promise<{ success?: boolean; started?: boolean; message?: string }>,
  ) => {
    setLoadingStates((prev) => ({ ...prev, [key]: true }));
    try {
      const result = await action();
      setSyncResults((prev) => ({
        ...prev,
        [key]: { success: result.success ?? result.started ?? false, message: result.message },
      }));
    } catch {
      setSyncResults((prev) => ({ ...prev, [key]: { success: false, message: 'Failed' } }));
    } finally {
      setLoadingStates((prev) => ({ ...prev, [key]: false }));
    }
  };

  const tabs = [
    {
      id: 'overview' as const,
      label: t('admin.remnawave.tabs.overview', 'Overview'),
      icon: <ChartIcon />,
    },
    { id: 'nodes' as const, label: t('admin.remnawave.tabs.nodes', 'Nodes'), icon: <GlobeIcon /> },
    {
      id: 'balancers' as const,
      label: 'Балансировщики',
      icon: <ServerIcon className="h-5 w-5" />,
    },
  ];

  const isConfigured = status?.is_configured;

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Show back button only on web, not in Telegram Mini App */}
          {!capabilities.hasBackButton && (
            <button
              onClick={() => navigate('/admin')}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-dark-700 bg-dark-800 transition-colors hover:border-dark-600"
            >
              <BackIcon className="text-dark-400" />
            </button>
          )}
          <div className="rounded-lg bg-accent-500/20 p-2">
            <RemnawaveIcon className="h-6 w-6 text-accent-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-dark-100">
              {t('admin.remnawave.title', 'Remnawave')}
            </h1>
            <p className="text-sm text-dark-400">
              {t('admin.remnawave.subtitle', 'Panel management and statistics')}
            </p>
          </div>
        </div>

        {/* Connection Status Badge */}
        <div
          className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs ${
            isConfigured ? 'bg-success-500/20 text-success-400' : 'bg-error-500/20 text-error-400'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${isConfigured ? 'bg-success-400' : 'bg-error-400'}`}
          />
          {isConfigured
            ? t('admin.remnawave.connected', 'Connected')
            : t('admin.remnawave.disconnected', 'Not configured')}
        </div>
      </div>

      {/* Configuration Error */}
      {status?.configuration_error && (
        <div className="mb-4 rounded-xl border border-error-500/30 bg-error-500/10 p-4">
          <p className="text-sm text-error-400">{status.configuration_error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 flex gap-1 overflow-x-auto rounded-xl bg-dark-800/50 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setSearchParams({ tab: tab.id }, { replace: true }); }}
            className={`flex min-w-[80px] flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-accent-500/20 text-accent-400'
                : 'text-dark-400 hover:bg-dark-700/50 hover:text-dark-200'
            }`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <ArcFleetOverview />
      )}

      {activeTab === 'nodes' && (
        <NodesTab
          nodes={nodesData?.items || []}
          providerByUuid={providerByUuid}
          realtimeByUuid={realtimeByUuid}
          isLoading={isLoadingNodes}
          onAction={handleNodeAction}
          isActionLoading={nodeActionMutation.isPending}
        />
      )}

      {activeTab === 'balancers' && <ArcBalancers />}

      {activeTab === 'sync' && (
        <SyncTab
          autoSyncStatus={autoSyncStatus}
          isLoading={isLoadingAutoSync}
          onRunAutoSync={() => handleSyncAction('autoSync', adminRemnawaveApi.runAutoSync)}
          onSyncFromPanel={() =>
            handleSyncAction('fromPanel', () => adminRemnawaveApi.syncFromPanel('all'))
          }
          onSyncToPanel={() => handleSyncAction('toPanel', adminRemnawaveApi.syncToPanel)}
          syncResults={syncResults}
          loadingStates={loadingStates}
        />
      )}
    </div>
  );
}
