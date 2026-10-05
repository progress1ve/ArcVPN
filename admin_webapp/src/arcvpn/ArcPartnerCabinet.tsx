import { lazy, Suspense, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { HashRouter, useLocation, useNavigate } from 'react-router';
import { AdminNavSection } from '@/components/admin/AdminNavSection';
import { ShellHeader } from '@/components/layout/AppShell/ShellHeader';
import AuroraBackground from '@/components/ui/backgrounds/aurora-background';
import { ChartBarIcon, CreditCardIcon, UsersIcon, ShareIcon, MegaphoneIcon, WalletIcon, BackIcon, LogoutIcon } from '@/components/icons';
import type { PartnerNode } from './PartnerNetwork';
const PartnerNetwork = lazy(() => import('./PartnerNetwork'));
const SimpleAreaChart = lazy(() => import('@/components/sales-stats/SimpleAreaChart').then(m => ({ default: m.SimpleAreaChart })));

import { ArcVpnLogo } from '@/components/ArcVpnLogo';
import { StatCard } from '@/components/stats/StatCard';
import { Button } from '@/components/primitives/Button';

type Tab = 'purchases' | 'clients' | 'payouts';
type Screen = 'home' | 'statistics' | 'network' | 'links' | Tab;
type Filters = { source: string; from: string; to: string };
type Source = { id: number; name: string; url: string; active: boolean; enabled: boolean };
type Purchase = { id: number; client: string; purchase_at: string; purchase_kind: string; purchase_description: string | null; purchase_cents: number; rate_bps: number; amount_cents: number };
type Client = { client: string; bound_at: string; source_name: string; rate_bps: number; purchases: number };
type Entry = { id: number; occurred_at: string; kind: string; amount_cents: number; method: string; note: string };
type Report = {
  partner: { name: string };
  sources: Source[];
  balance: { earned: number; accrued: number; adjustments: number; paid: number; available: number; debt: number };
  stats: { clients: number; paying_clients: number; purchases: number; renewals: number; cohort_paying_clients: number; conversion_percent: number; revenue_cents: number; avg_purchase_cents: number; repeat_clients: number };
  series: { day: string; purchases: number; revenue_cents: number; reward_cents: number }[];
  network: PartnerNode[]; network_truncated: boolean;
  purchases: Purchase[]; clients: Client[]; journal: Entry[]; payouts: Entry[];
  page: number; has_more: Record<Tab, boolean>;
};
const emptyFilters: Filters = { source: '', from: '', to: '' };
const money = (value: number) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format((value || 0) / 100);
const stamp = (value: string) => value ? new Date(value.includes('T') ? value : value.replace(' ', 'T') + 'Z').toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) : '—';
const labels: Record<string, string> = { new: 'Покупка', renew: 'Продление', upgrade: 'Смена тарифа', addon_device: 'Устройства', addon_lte: 'Трафик', addon_combined: 'Устройства и трафик', accrual: 'Начисление', adjustment: 'Корректировка', refund: 'Возврат', reversal: 'Отмена', payout: 'Ручная выплата' };
const sections = [
  { title: 'Аналитика', gradient: 'linear-gradient(135deg, #34d399, #3b82f6)', items: [['statistics', 'Статистика', ChartBarIcon], ['purchases', 'Покупки', CreditCardIcon], ['payouts', 'Выплаты', WalletIcon]] },
  { title: 'Маркетинг', gradient: 'linear-gradient(135deg, #93c5fd, #3b82f6)', items: [['links', 'Реферальные ссылки', MegaphoneIcon], ['clients', 'Клиенты', UsersIcon], ['network', 'Реферальная сеть', ShareIcon]] },
] as const;
const screenNames: Record<Screen, string> = { home: 'Партнёрская панель', statistics: 'Статистика', purchases: 'Покупки', clients: 'Клиенты', payouts: 'Выплаты', links: 'Реферальные ссылки', network: 'Реферальная сеть' };
const messages: Record<string, string> = { invalid_credentials: 'Неверный логин или пароль либо доступ отозван.', login_rate_limited: 'Слишком много попыток. Повторите через 15 минут.', unauthorized: 'Сессия завершилась. Войдите снова.' };
const field = 'min-h-11 w-full rounded-xl border border-dark-700 bg-dark-800 px-3 py-2.5 text-sm text-dark-100 outline-none focus-visible:ring-2 focus-visible:ring-accent-500';
const panel = 'rounded-2xl border border-dark-700/50 bg-dark-800/30 p-4 backdrop-blur-xl sm:p-5';

class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function api(path: string, body?: Record<string, string>): Promise<Report> {
  const response = await fetch('/api/partners/' + path, {
    credentials: 'same-origin', cache: 'no-store',
    ...(body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
  });
  const value = await response.json();
  if (!response.ok) throw new ApiError(response.status, messages[value.error] || 'Не удалось выполнить запрос. Повторите позже.');
  return value;
}

function Table({ columns, children, empty, count }: { columns: string[]; children: ReactNode; empty: string; count: number }) {
  return <div className="overflow-x-auto rounded-xl border border-dark-700" tabIndex={0} aria-label="Таблица статистики">
    <table className="w-full text-left text-sm [&_td]:border-t [&_td]:border-dark-700 [&_td]:px-4 [&_td]:py-3 [&_td]:align-top [&_td]:tabular-nums [&_th]:whitespace-nowrap [&_th]:px-4 [&_th]:py-3 [&_th]:font-medium [&_th]:text-dark-400">
      <thead className="bg-dark-800/50"><tr>{columns.map(column => <th scope="col" key={column}>{column}</th>)}</tr></thead>
      <tbody>{count ? children : <tr><td colSpan={columns.length} className="text-dark-400">{empty}</td></tr>}</tbody>
    </table>
  </div>;
}

export default function ArcPartnerCabinet() { return <HashRouter><PartnerPanel /></HashRouter>; }

function PartnerPanel() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname.slice(1);
  const screen: Screen = Object.prototype.hasOwnProperty.call(screenNames, path) ? path as Screen : 'home';
  const [data, setData] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [draft, setDraft] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const tab: Tab = screen === 'clients' || screen === 'payouts' ? screen : 'purchases';
  const [copied, setCopied] = useState('');
  const sequence = useRef(0);
  const authenticated = useRef(false);

  async function load(selected: Filters = filters, page = data?.page || 1) {
    const request = ++sequence.current;
    setLoading(true); setError('');
    try {
      const report = await api('cabinet?' + new URLSearchParams({ ...selected, page: String(page) }));
      if (request === sequence.current) { setData(report); authenticated.current = true; }
    } catch (e) {
      if (request !== sequence.current) return;
      if (e instanceof ApiError && e.status === 401) {
        setData(null);
        if (authenticated.current) setError(e.message);
        authenticated.current = false;
      } else setError(e instanceof Error ? e.message : 'Ошибка подключения.');
    } finally { if (request === sequence.current) setLoading(false); }
  }
  useEffect(() => { void load(emptyFilters, 1); return () => { sequence.current++; }; }, []);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try {
      await api('login', { login, password }); setPassword('');
      setDraft(emptyFilters); setFilters(emptyFilters); navigate('/'); setCopied('');
      await load(emptyFilters, 1);
    } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка входа.'); }
    finally { setBusy(false); }
  }
  async function signOut() {
    if (busy) return;
    setBusy(true); setError('');
    try { await api('logout', {}); sequence.current++; authenticated.current = false; setData(null); setPassword(''); setLoading(false); }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось выйти.'); }
    finally { setBusy(false); }
  }
  async function copy(url: string) {
    try { await navigator.clipboard.writeText(url); setCopied(url); }
    catch { setError('Не удалось скопировать. Выделите ссылку вручную.'); }
  }

  function go(next: Screen) { navigate(next === 'home' ? '/' : '/' + next); if (next === 'home') { setFilters(emptyFilters); setDraft(emptyFilters); void load(emptyFilters, 1); } else void load(filters, 1); }
  const dateFilters = data && !['home', 'links'].includes(screen);
  return <div className="relative isolate min-h-dvh bg-dark-950 text-dark-100">
    <div className="pointer-events-none fixed inset-0 -z-10 bg-dark-950"><div className="absolute inset-0 opacity-30 motion-reduce:hidden"><AuroraBackground settings={{ firstColor: '#64748b', secondColor: '#94a3b8', thirdColor: '#334155', speed: 'slow' }} /></div></div>
    <ShellHeader className="sticky inset-x-0 top-0 z-50 border-b border-dark-800/50 bg-dark-950/95">
      <a href="#/" className="flex items-center gap-2.5 justify-self-start" aria-label="ArcVPN — главная"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-dark-800"><ArcVpnLogo className="h-6 w-6 text-white" /></span><span className="text-base font-semibold">ArcVPN</span></a>
      <span className="hidden text-xs text-dark-500 sm:block">Партнёрский кабинет</span>
      <div className="justify-self-end">{data && <Button variant="ghost" size="icon" aria-label="Выйти" disabled={busy} onClick={() => void signOut()}><LogoutIcon className="h-5 w-5" /></Button>}</div>
    </ShellHeader>
    {!data ? <main className="mx-auto flex min-h-[75dvh] max-w-md items-center px-4 py-8">
      {loading ? <p role="status" className="w-full text-center text-dark-400">Проверяем сессию…</p> : <form className={panel + ' w-full space-y-5'} onSubmit={signIn}>
        <ArcVpnLogo className="h-12 w-12 text-white" /><div><h1 className="text-2xl font-semibold">Вход в ArcVPN</h1><p className="mt-2 text-sm text-dark-400">Партнёрский кабинет</p></div>
        <label className="block space-y-2 text-sm text-dark-300"><span>Логин</span><input className={field} value={login} onChange={e => setLogin(e.target.value)} autoComplete="username" maxLength={64} required /></label>
        <label className="block space-y-2 text-sm text-dark-300"><span>Пароль</span><input className={field} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" maxLength={256} required /></label>
        {error && <p role="alert" className="rounded-xl bg-error-500/10 p-3 text-sm text-error-400">{error}</p>}
        <Button type="submit" fullWidth loading={busy} disabled={!login || !password}>Войти</Button>
      </form>}
    </main> : <main className="mx-auto max-w-6xl space-y-5 px-4 py-5 sm:px-6 sm:py-6" aria-busy={loading}>
      <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex min-w-0 items-center gap-3">{screen !== 'home' && <Button variant="secondary" size="icon" aria-label="Назад в панель" onClick={() => go('home')}><BackIcon className="h-5 w-5" /></Button>}<div><h1 className="text-lg font-semibold">{screenNames[screen]}</h1><p className="mt-1 text-xs text-dark-400">{data.partner.name}</p></div></div><Button variant="secondary" size="sm" loading={loading} disabled={busy} onClick={() => void load()}>Обновить</Button></div>
      {error && <p role="alert" className="rounded-xl border border-error-500/30 bg-error-500/10 p-4 text-sm text-error-400">{error}</p>}
      <section className="grid gap-3 sm:grid-cols-3" aria-label="Доход партнёра за всё время">
        <StatCard label="Заработано за всё время" value={money(data.balance.earned)} icon={<WalletIcon />} />
        <StatCard label="Выплачено" value={money(data.balance.paid)} icon={<CreditCardIcon />} />
        <StatCard label="К выплате" value={money(data.balance.available)} icon={<WalletIcon />} tone="success" />
      </section>
      {screen === 'home' && <>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><StatCard label="Привлечено клиентов" value={data.stats.clients} /><StatCard label="Оплативших клиентов" value={data.stats.cohort_paying_clients} /><StatCard label="Конверсия в оплату" value={data.stats.conversion_percent + '%'} /><StatCard label="Покупки" value={data.stats.purchases} /></div>
        <div className="grid gap-4 sm:grid-cols-2">{sections.map(section => <AdminNavSection key={section.title} title={section.title} count={section.items.length} gradient={section.gradient}><div className="flex flex-col gap-px p-1.5">{section.items.map(([value, name, Icon]) => <button key={value} className="group/item flex items-center gap-2.5 rounded-xl border border-transparent px-2 py-2 text-left transition-colors hover:border-dark-600/50 hover:bg-dark-700/30 focus-visible:outline focus-visible:outline-accent-500" onClick={() => go(value)}><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-dark-700/40 bg-dark-800/40 text-accent-400"><Icon className="h-[13px] w-[13px]" /></span><span className="text-xs font-medium text-dark-200">{name}</span></button>)}</div></AdminNavSection>)}</div>
      </>}
      {dateFilters && <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_auto] lg:items-end" onSubmit={e => { e.preventDefault(); setFilters(draft); void load(draft, 1); }}>
        <label className="space-y-2 text-xs text-dark-300"><span>Ссылка</span><select className={field} value={draft.source} onChange={e => setDraft({ ...draft, source: e.target.value })}><option value="">Все ссылки</option>{data.sources.map(link => <option key={link.id} value={link.id}>{link.name}</option>)}</select></label>
        <label className="space-y-2 text-xs text-dark-300"><span>С даты</span><input className={field} type="date" value={draft.from} onChange={e => setDraft({ ...draft, from: e.target.value })} /></label>
        <label className="space-y-2 text-xs text-dark-300"><span>По дату</span><input className={field} type="date" value={draft.to} onChange={e => setDraft({ ...draft, to: e.target.value })} /></label>
        <Button type="submit" disabled={loading || busy}>Применить</Button>
      </form>}
      {screen === 'statistics' && <>
        <p className="text-xs text-dark-400">Конверсия: доля привлечённых за выбранный период клиентов с подтверждённой покупкой, участвующей в вознаграждении. Оплаты учитываются по текущий момент. Выручка и покупки ниже — по дате оплаты, время московское.</p>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><StatCard label="Привлечено" value={data.stats.clients} /><StatCard label="Оплатили из привлечённых" value={data.stats.cohort_paying_clients} /><StatCard label="Конверсия в оплату" value={data.stats.conversion_percent + '%'} tone="success" /><StatCard label="Покупки" value={data.stats.purchases} /><StatCard label="Выручка клиентов" value={money(data.stats.revenue_cents)} /><StatCard label="Средний чек" value={money(data.stats.avg_purchase_cents)} /><StatCard label="Продления" value={data.stats.renewals} /><StatCard label="Клиенты с повторными покупками" value={data.stats.repeat_clients} /></div>
        {data.series.length ? <Suspense fallback={<p className="text-sm text-dark-400">Загружаем график…</p>}><SimpleAreaChart title="Покупки по дням" valueLabel="Покупки" chartId="partner-sales" data={data.series.map(row => ({ date: row.day, value: row.purchases }))} /></Suspense> : <p className={panel + ' text-sm text-dark-400'}>Покупок за выбранный период нет.</p>}
      </>}
      {screen === 'links' && <section className={panel}><h2 className="mb-4 text-sm font-semibold">Назначенные ссылки</h2>{data.sources.length ? <div className="divide-y divide-dark-700/50">{data.sources.map(link => <div key={link.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="text-sm font-medium">{link.name}</p><p className="mt-1 text-xs text-dark-400">{link.active && link.enabled ? 'Активна' : 'Отключена'}</p><a className="mt-2 block break-all text-xs text-accent-400 hover:underline" href={link.url} target="_blank" rel="noreferrer">{link.url}</a></div><Button className="shrink-0 self-start" variant="secondary" size="sm" onClick={() => void copy(link.url)}>{copied === link.url ? 'Скопировано' : 'Копировать'}</Button></div>)}</div> : <p className="text-sm text-dark-400">Ссылки ещё не назначены.</p>}<span role="status" className="sr-only">{copied ? 'Ссылка скопирована' : ''}</span></section>}
      {screen === 'network' && <Suspense fallback={<p className="text-sm text-dark-400">Загружаем сеть…</p>}><PartnerNetwork nodes={data.network} sources={data.sources.filter(source => !filters.source || source.id === Number(filters.source))} truncated={data.network_truncated} /></Suspense>}
      {['purchases', 'clients', 'payouts'].includes(screen) && <section className={panel + ' space-y-4'}>
        {screen === 'purchases' ? <Table columns={['Клиент', 'Дата', 'Что купили', 'Оплачено', 'Ставка', 'Ваш доход']} count={data.purchases.length} empty="Подтверждённых покупок за этот период нет.">{data.purchases.map(row => <tr key={row.id}><td className="whitespace-nowrap">{row.client}</td><td className="whitespace-nowrap">{stamp(row.purchase_at)}</td><td className="min-w-56"><div className="font-medium">{row.purchase_description || labels[row.purchase_kind]}</div><div className="mt-1 text-xs text-dark-400">{labels[row.purchase_kind]}</div></td><td className="whitespace-nowrap">{money(row.purchase_cents)}</td><td>{row.rate_bps / 100}%</td><td className="whitespace-nowrap text-success-400">{money(row.amount_cents)}</td></tr>)}</Table> : screen === 'clients' ? <Table columns={['Клиент', 'Привлечён', 'Ссылка', 'Ставка', 'Покупки']} count={data.clients.length} empty="Привлечённых клиентов за этот период нет.">{data.clients.map(row => <tr key={row.client}><td className="whitespace-nowrap">{row.client}</td><td className="whitespace-nowrap">{stamp(row.bound_at)}</td><td className="min-w-40 break-words">{row.source_name}</td><td>{row.rate_bps / 100}%</td><td>{row.purchases}</td></tr>)}</Table> : <><p className="text-xs text-dark-400">Владелец переводит деньги вручную. Здесь указаны выполненные выплаты и отмены выплат.</p><Table columns={['Дата', 'Операция', 'Сумма', 'Способ', 'Примечание']} count={data.payouts.length} empty="Выплат за этот период нет.">{data.payouts.map(row => <tr key={row.id}><td className="whitespace-nowrap">{stamp(row.occurred_at)}</td><td>{row.kind === 'reversal' ? 'Отмена выплаты' : 'Выплата'}</td><td className="whitespace-nowrap">{money(Math.abs(row.amount_cents))}</td><td className="min-w-28 break-words">{row.method || '—'}</td><td className="min-w-48 break-all">{row.note || '—'}</td></tr>)}</Table></>}
        <div className="flex items-center justify-between gap-2"><Button variant="secondary" disabled={loading || busy || data.page <= 1} onClick={() => void load(filters, data.page - 1)}>Назад</Button><span className="text-xs text-dark-400" role="status">{loading ? 'Обновляем…' : `Страница ${data.page}`}</span><Button variant="secondary" disabled={loading || busy || !data.has_more[tab]} onClick={() => void load(filters, data.page + 1)}>Далее</Button></div>
      </section>}
    </main>}
  </div>;
}
