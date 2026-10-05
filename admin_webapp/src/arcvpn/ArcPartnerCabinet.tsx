import { lazy, Suspense, useEffect, useRef, useState, type FormEvent } from 'react';
import { HashRouter, useLocation, useNavigate } from 'react-router';
import { AdminNavSection } from '@/components/admin/AdminNavSection';
import { ShellHeader } from '@/components/layout/AppShell/ShellHeader';
import { RenderBackground } from '@/components/backgrounds/BackgroundCanvas';
import { DEFAULT_ANIMATION_CONFIG } from '@/components/ui/backgrounds/types';
import { ChartBarIcon, CreditCardIcon, UsersIcon, ShareIcon, MegaphoneIcon, WalletIcon, BackIcon, LogoutIcon } from '@/components/icons';
import type { PartnerNode } from './PartnerNetwork';
const PartnerNetwork = lazy(() => import('./PartnerNetwork'));


import { ArcVpnLogo } from '@/components/ArcVpnLogo';
import { PartnerContent } from './PartnerContent';
import { PeriodPicker, periodDates, type Period } from '@/components/admin/PeriodPicker';
import { StatCard } from '@/components/stats/StatCard';
import { Button } from '@/components/primitives/Button';

type Tab = 'purchases' | 'clients' | 'payouts';
type Screen = 'home' | 'statistics' | 'network' | 'links' | Tab;
export type Filters = { source: string; from: string; to: string; kind:string; search:string };
type Source = { id: number; name: string; url: string; active: boolean; enabled: boolean };
type Purchase = { id: number; client: string; purchase_at: string; purchase_kind: string; purchase_description: string | null; purchase_cents: number; rate_bps: number; amount_cents: number };
type Client = { client: string; bound_at: string; source_name: string; rate_bps: number; purchases: number };
type Entry = { id: number; occurred_at: string; kind: string; amount_cents: number; method: string; note: string };
export type Report = {
  partner: { name: string };
  sources: Source[];
  balance: { earned: number; accrued: number; adjustments: number; paid: number; available: number; debt: number };
  stats: { clients: number; paying_clients: number; purchases: number; renewals: number; cohort_paying_clients: number; conversion_percent: number; revenue_cents: number; avg_purchase_cents: number; repeat_clients: number; trials:number; paid:number; expired:number; without_subscription:number; reward_cents:number };
  series: { day: string; purchases: number; revenue_cents: number; reward_cents: number }[];
  client_series: {day:string; clients:number}[];
  network: PartnerNode[]; network_truncated: boolean;
  purchases: Purchase[]; clients: Client[]; journal: Entry[]; payouts: Entry[];
  payout_stats?: {count:number; paid_cents:number};
  page: number; has_more: Record<Tab, boolean>;
};
const emptyFilters: Filters = { source: '', from: '', to: '', kind:'', search:'' };
export const money = (value: number) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format((value || 0) / 100);
export const stamp = (value: string) => value ? new Date(value.includes('T') ? value : value.replace(' ', 'T') + 'Z').toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) : '—';
export const labels: Record<string, string> = { new: 'Покупка', renew: 'Продление', upgrade: 'Смена тарифа', addon_device: 'Устройства', addon_lte: 'Трафик', addon_combined: 'Устройства и трафик', accrual: 'Начисление', adjustment: 'Корректировка', refund: 'Возврат', reversal: 'Отмена', payout: 'Ручная выплата' };
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
  const [filters, setFilters] = useState(emptyFilters);
  const [period,setPeriod] = useState<Period>('month');
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
  useEffect(() => { const selected = ['statistics','purchases','payouts'].includes(screen) ? { ...emptyFilters, ...periodDates('month') } : emptyFilters; setFilters(selected);setPeriod(['statistics','purchases','payouts'].includes(screen)?'month':'all');void load(selected,1); return () => { sequence.current++; }; }, [screen]);

  useEffect(() => { const timer = window.setInterval(() => {if(authenticated.current && document.visibilityState === 'visible') void load(filters,data?.page||1);},60000);return ()=>window.clearInterval(timer);},[filters,data?.page,screen]);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try {
      await api('login', { login, password }); setPassword('');
      setFilters(emptyFilters); navigate('/'); setCopied('');
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

  function go(next: Screen) { navigate(next === 'home' ? '/' : '/' + next); }
  function change(selected: Filters) {setFilters(selected);void load(selected,1);}
  return <div className="relative min-h-dvh text-dark-100">
    <RenderBackground config={{...DEFAULT_ANIMATION_CONFIG,blur:32,opacity:0.8}} />
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 md:hidden" style={{zIndex:-1,background:'radial-gradient(ellipse at 50% 0%, rgba(60,80,120,.32), transparent 60%), #0b101a'}} />
    <ShellHeader className="sticky inset-x-0 top-0 z-50 border-b border-dark-800/50 bg-dark-950/95">
      <a href="#/" onClick={e=>{e.preventDefault();go('home');}} className="flex items-center gap-2.5 justify-self-start" aria-label="ArcVPN — главная"><ArcVpnLogo className="h-7 w-7 text-white" /><span className="text-base font-semibold">ArcVPN</span></a>
      <span className="hidden text-xs text-dark-500 sm:block">Партнёрский кабинет</span>
      <div className="col-start-3 justify-self-end">{data && <Button variant="ghost" size="icon" aria-label="Выйти" disabled={busy} onClick={() => void signOut()}><LogoutIcon className="h-5 w-5" /></Button>}</div>
    </ShellHeader>
    {!data ? <main className="mx-auto flex min-h-[75dvh] max-w-md items-center px-4 py-8">
      {loading ? <p role="status" className="w-full text-center text-dark-400">Проверяем сессию…</p> : <form className={panel + ' w-full space-y-5'} onSubmit={signIn}>
        <ArcVpnLogo className="h-12 w-12 text-white" /><div><h1 className="text-2xl font-semibold">Вход в ArcVPN</h1><p className="mt-2 text-sm text-dark-400">Партнёрский кабинет</p></div>
        <label className="block space-y-2 text-sm text-dark-300"><span>Логин</span><input className={field} value={login} onChange={e => setLogin(e.target.value)} autoComplete="username" maxLength={64} required /></label>
        <label className="block space-y-2 text-sm text-dark-300"><span>Пароль</span><input className={field} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" maxLength={256} required /></label>
        {error && <p role="alert" className="rounded-xl bg-error-500/10 p-3 text-sm text-error-400">{error}</p>}
        <Button type="submit" fullWidth loading={busy} disabled={!login || !password}>Войти</Button>
      </form>}
    </main> : <main className={screen === 'network' ? 'fixed inset-x-0 bottom-0 top-14 flex flex-col bg-dark-950' : 'mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6'} aria-busy={loading}>
      <div className={screen === 'network' ? 'flex items-center gap-3 border-b border-dark-800 px-4 py-3' : 'flex items-center gap-3'}>{screen !== 'home' && <button className="btn-secondary flex h-12 w-12 shrink-0 items-center justify-center" aria-label="Назад в панель" onClick={()=>go('home')}><BackIcon className="h-5 w-5"/></button>}<div><h1 className={screen==='network'?'text-xl font-bold':'text-2xl font-bold sm:text-3xl'}>{screenNames[screen]}</h1><p className="mt-1 text-sm text-dark-400">{screen==='home'?data.partner.name:screen==='purchases'?'Подтверждённые покупки и ваш доход':screen==='payouts'?'Переводы, выполненные владельцем':screen==='statistics'?'Клиенты, подписки и продажи':screen==='network'?'Ваша сеть клиентов':'Ваши ссылки и закреплённые клиенты'}</p></div></div>
      {error && <p role="alert" className="rounded-xl border border-error-500/30 bg-error-500/10 p-4 text-sm text-error-400">{error}</p>}
      {screen === 'home' && <>
        <section className="grid gap-3 sm:grid-cols-3" aria-label="Доход партнёра за всё время"><StatCard label="Заработано за всё время" value={money(data.balance.earned)} icon={<WalletIcon/>}/><StatCard label="Выплачено" value={money(data.balance.paid)} icon={<CreditCardIcon/>}/><StatCard label="К выплате" value={money(data.balance.available)} tone="success" icon={<WalletIcon/>}/></section>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><StatCard label="Привлечено клиентов" value={data.stats.clients}/><StatCard label="Триалы" value={data.stats.trials||0}/><StatCard label="Платные" value={data.stats.paid||0}/><StatCard label="Конверсия в оплату" value={data.stats.conversion_percent+'%'}/></div>
        <div className="grid gap-4 sm:grid-cols-2">{sections.map((section,index)=><AdminNavSection key={section.title} title={section.title} count={index+1} gradient={section.gradient}><div className="flex flex-col gap-px p-1.5">{section.items.map(([value,name,Icon])=><button key={value} className="group/item flex items-center gap-2.5 rounded-xl border border-transparent px-2 py-2 text-left transition-colors hover:border-dark-600/50 hover:bg-dark-700/30 focus-visible:outline focus-visible:outline-accent-500" onClick={()=>go(value)}><span className={`flex h-6 w-6 items-center justify-center rounded-lg border border-dark-700/40 bg-dark-800/40 ${index===0?'text-success-400':'text-accent-400'}`}><Icon className="h-[13px] w-[13px]"/></span><span className="text-xs font-medium text-dark-200">{name}</span></button>)}</div></AdminNavSection>)}</div>
      </>}
      {screen !== 'home' && screen !== 'links' && <div className={screen==='network'?'border-b border-dark-800 px-4 py-2':'space-y-3'}><PeriodPicker value={period} dates={filters} onChange={(next,dates)=>{setPeriod(next);change({...filters,...dates});}}/>{screen!=='payouts'&&<select aria-label="Ссылка" className="mt-2 rounded-lg border border-dark-700 bg-dark-800 px-3 py-2 text-sm" value={filters.source} onChange={e=>change({...filters,source:e.target.value})}><option value="">Все ссылки</option>{data.sources.map(source=><option value={source.id} key={source.id}>{source.name}</option>)}</select>}</div>}
      {screen === 'links' && <section className={panel}><h2 className="mb-4 font-semibold">Назначенные ссылки</h2>{data.sources.map(link=><div key={link.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700/50 py-4"><div className="min-w-0"><p className="font-semibold">{link.name} <span className="ml-2 rounded-full bg-success-500/15 px-2 py-1 text-xs text-success-400">{link.active&&link.enabled?'Активна':'Отключена'}</span></p><a className="mt-2 block break-all text-sm text-accent-400" href={link.url} target="_blank" rel="noreferrer">{link.url}</a></div><Button variant="secondary" size="sm" onClick={()=>void copy(link.url)}>{copied===link.url?'Скопировано':'Копировать'}</Button></div>)}{!data.sources.length&&<p className="text-dark-400">Ссылки ещё не назначены.</p>}</section>}
      {screen === 'network' && <Suspense fallback={<p className="p-4 text-dark-400">Загружаем сеть…</p>}><PartnerNetwork nodes={data.network} sources={data.sources.filter(source=>!filters.source||source.id===Number(filters.source))} truncated={data.network_truncated}/></Suspense>}
      {['statistics','purchases','clients','payouts'].includes(screen)&&<PartnerContent screen={screen as 'statistics'|'purchases'|'clients'|'payouts'} data={data} filters={filters} onFilter={change}/>}
      {['purchases','clients','payouts'].includes(screen)&&data.has_more&&(data.page>1||data.has_more[tab])&&<div className="flex items-center justify-between gap-2"><Button variant="secondary" disabled={loading||data.page<=1} onClick={()=>void load(filters,data.page-1)}>Назад</Button><span className="text-xs text-dark-400" role="status">Страница {data.page}</span><Button variant="secondary" disabled={loading||!data.has_more[tab]} onClick={()=>void load(filters,data.page+1)}>Далее</Button></div>}
    </main>}
  </div>;
}
