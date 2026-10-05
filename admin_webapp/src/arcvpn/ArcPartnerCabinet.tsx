import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ArcVpnLogo } from '@/components/ArcVpnLogo';
import { StatCard } from '@/components/stats/StatCard';
import { Button } from '@/components/primitives/Button';

type Tab = 'purchases' | 'clients' | 'journal' | 'payouts';
type Filters = { source: string; from: string; to: string };
type Source = { id: number; name: string; url: string; active: boolean; enabled: boolean };
type Purchase = { id: number; client: string; purchase_at: string; purchase_kind: string; purchase_cents: number; rate_bps: number; amount_cents: number };
type Client = { client: string; bound_at: string; source_name: string; rate_bps: number; purchases: number };
type Entry = { id: number; occurred_at: string; kind: string; amount_cents: number; method: string; note: string };
type Report = {
  partner: { name: string };
  sources: Source[];
  balance: { accrued: number; adjustments: number; paid: number; available: number; debt: number };
  stats: { clients: number; paying_clients: number; purchases: number; renewals: number };
  purchases: Purchase[]; clients: Client[]; journal: Entry[]; payouts: Entry[];
  page: number; has_more: Record<Tab, boolean>;
};
const emptyFilters: Filters = { source: '', from: '', to: '' };
const money = (value: number) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format((value || 0) / 100);
const stamp = (value: string) => value ? new Date(value.includes('T') ? value : value.replace(' ', 'T') + 'Z').toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) : '—';
const labels: Record<string, string> = { new: 'Покупка', renew: 'Продление', upgrade: 'Смена тарифа', addon_device: 'Устройства', addon_lte: 'Трафик', addon_combined: 'Устройства и трафик', accrual: 'Начисление', adjustment: 'Корректировка', refund: 'Возврат', reversal: 'Отмена', payout: 'Ручная выплата' };
const tabs: [Tab, string][] = [['purchases', 'Покупки'], ['clients', 'Клиенты'], ['journal', 'Журнал'], ['payouts', 'Выплаты']];
const messages: Record<string, string> = { invalid_credentials: 'Неверный логин или пароль либо доступ отозван.', login_rate_limited: 'Слишком много попыток. Повторите через 15 минут.', unauthorized: 'Сессия завершилась. Войдите снова.' };
const field = 'min-h-11 w-full rounded-xl border border-dark-700 bg-dark-800 px-3 py-2.5 text-sm text-dark-100 outline-none focus-visible:ring-2 focus-visible:ring-accent-500';
const panel = 'rounded-2xl border border-dark-700 bg-dark-900 p-4 sm:p-6';

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

export default function ArcPartnerCabinet() {
  const [data, setData] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [draft, setDraft] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const [tab, setTab] = useState<Tab>('purchases');
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
      setDraft(emptyFilters); setFilters(emptyFilters); setTab('purchases'); setCopied('');
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

  return <div className="min-h-dvh bg-dark-950 text-dark-100">
    <header className="border-b border-dark-700 bg-dark-900">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <a href="/partner" className="flex items-center gap-3 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500">
          <ArcVpnLogo className="h-9 w-9 text-accent-400" /><span className="font-semibold">ArcVPN<span className="ml-3 hidden text-sm font-normal text-dark-400 sm:inline">Партнёры</span></span>
        </a>
        {data && <Button variant="secondary" disabled={busy} onClick={() => void signOut()}>Выйти</Button>}
      </div>
    </header>
    {!data ? <main className="mx-auto flex min-h-[75dvh] max-w-md items-center px-4 py-8">
      {loading ? <p role="status" className="w-full text-center text-dark-400">Проверяем сессию…</p> :
        <form className={panel + ' w-full space-y-5'} onSubmit={signIn}>
          <ArcVpnLogo className="h-12 w-12 text-accent-400" />
          <div><p className="text-sm text-accent-400">Партнёрский кабинет</p><h1 className="mt-2 text-2xl font-semibold">Вход в ArcVPN</h1><p className="mt-2 text-sm text-dark-400">Логин и пароль предоставляет владелец сервиса.</p></div>
          <label className="block space-y-2 text-sm text-dark-300"><span>Логин</span><input className={field} value={login} onChange={e => setLogin(e.target.value)} autoComplete="username" maxLength={64} required /></label>
          <label className="block space-y-2 text-sm text-dark-300"><span>Пароль</span><input className={field} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" maxLength={256} required /></label>
          {error && <p role="alert" className="rounded-xl bg-error-500/10 p-3 text-sm text-error-400">{error}</p>}
          <Button type="submit" fullWidth loading={busy} disabled={!login || !password}>Войти</Button>
        </form>}
    </main> : <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 sm:py-8" aria-busy={loading}>
      <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm text-accent-400">Партнёрский кабинет</p><h1 className="mt-1 break-words text-2xl font-semibold sm:text-3xl">{data.partner.name}</h1><p className="mt-2 text-sm text-dark-400">Закреплённые клиенты и вознаграждения</p></div><Button variant="secondary" loading={loading} disabled={busy} onClick={() => void load()}>Обновить</Button></div>
      {error && <p role="alert" className="rounded-xl border border-error-500/30 bg-error-500/10 p-4 text-sm text-error-400">{error}</p>}
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Все начисления">
        <StatCard label="Начислено" value={money(data.balance.accrued)} />
        <StatCard label="Корректировки" value={money(data.balance.adjustments)} />
        <StatCard label="Выплачено" value={money(data.balance.paid)} />
        <StatCard label="Доступно к выплате" value={money(data.balance.available)} tone="accent" />
      </section>
      <p className="text-sm text-dark-400">Остаток за всё время. Выплаты переводит владелец вручную.{data.balance.debt > 0 && ` Задолженность по корректировкам: ${money(data.balance.debt)}.`}</p>
      <section className={panel} aria-labelledby="partner-links"><h2 id="partner-links" className="mb-4 text-lg font-semibold">Назначенные ссылки</h2>
        {data.sources.length ? <div className="divide-y divide-dark-700">{data.sources.map(link => <div key={link.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0"><p className="break-words font-medium">{link.name}</p><p className="mt-1 text-xs text-dark-400">{link.active && link.enabled ? 'Активна' : 'Отключена · история сохранена'}</p><a className="mt-2 block break-all text-sm text-accent-400 hover:underline focus-visible:outline focus-visible:outline-accent-500" href={link.url} target="_blank" rel="noreferrer">{link.url}</a></div>
          <Button className="shrink-0 self-start sm:self-auto" variant="secondary" onClick={() => void copy(link.url)}>{copied === link.url ? 'Скопировано' : 'Копировать'}</Button>
        </div>)}</div> : <p className="text-sm text-dark-400">Ссылки ещё не назначены.</p>}
        <span className="sr-only" role="status">{copied ? 'Ссылка скопирована' : ''}</span>
      </section>
      <section className={panel + ' space-y-5'} aria-labelledby="partner-statistics">
        <div><h2 id="partner-statistics" className="text-lg font-semibold">Статистика</h2><p className="mt-2 text-sm text-dark-400">Период — по московскому времени. Привлечённые считаются по дате закрепления, покупки — по дате оплаты.</p></div>
        <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_auto] lg:items-end" onSubmit={e => { e.preventDefault(); setFilters(draft); void load(draft, 1); }}>
          <label className="space-y-2 text-sm text-dark-300"><span>Ссылка</span><select className={field} value={draft.source} onChange={e => setDraft({ ...draft, source: e.target.value })}><option value="">Все ссылки</option>{data.sources.map(link => <option key={link.id} value={link.id}>{link.name}</option>)}</select></label>
          <label className="space-y-2 text-sm text-dark-300"><span>С даты</span><input className={field} type="date" value={draft.from} onChange={e => setDraft({ ...draft, from: e.target.value })} /></label>
          <label className="space-y-2 text-sm text-dark-300"><span>По дату</span><input className={field} type="date" value={draft.to} onChange={e => setDraft({ ...draft, to: e.target.value })} /></label>
          <Button type="submit" disabled={loading || busy}>Применить</Button>
        </form>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Показатели за выбранный период">
          <StatCard label="Привлечено" value={data.stats.clients} />
          <StatCard label="Оплативших клиентов" value={data.stats.paying_clients} />
          <StatCard label="Покупки" value={data.stats.purchases} />
          <StatCard label="Продления" value={data.stats.renewals} />
        </div>
        <nav className="flex flex-wrap gap-2" aria-label="Разделы кабинета">{tabs.map(([value, name]) => <Button key={value} variant={tab === value ? 'primary' : 'secondary'} aria-current={tab === value ? 'page' : undefined} disabled={loading || busy} onClick={() => { setTab(value); void load(filters, 1); }}>{name}</Button>)}</nav>
        {tab === 'purchases' ? <Table columns={['Клиент', 'Дата', 'Покупка', 'Оплачено', 'Ставка', 'Вознаграждение']} count={data.purchases.length} empty="Подтверждённых покупок за этот период нет.">
          {data.purchases.map(row => <tr key={row.id}><td className="whitespace-nowrap">{row.client}</td><td className="whitespace-nowrap">{stamp(row.purchase_at)}</td><td>{labels[row.purchase_kind] || row.purchase_kind}</td><td className="whitespace-nowrap">{money(row.purchase_cents)}</td><td>{row.rate_bps / 100}%</td><td className="whitespace-nowrap text-accent-400">{money(row.amount_cents)}</td></tr>)}
        </Table> : tab === 'clients' ? <Table columns={['Клиент', 'Закреплён', 'Ссылка', 'Ставка', 'Покупки']} count={data.clients.length} empty="Привлечённых клиентов за этот период нет.">
          {data.clients.map(row => <tr key={row.client}><td className="whitespace-nowrap">{row.client}</td><td className="whitespace-nowrap">{stamp(row.bound_at)}</td><td className="min-w-40 break-words">{row.source_name}</td><td>{row.rate_bps / 100}%</td><td>{row.purchases}</td></tr>)}
        </Table> : <Table columns={['Дата', 'Операция', 'Сумма', 'Способ', 'Примечание']} count={(tab === 'payouts' ? data.payouts : data.journal).length} empty="Операций за этот период нет.">
          {(tab === 'payouts' ? data.payouts : data.journal).map(row => <tr key={row.id}><td className="whitespace-nowrap">{stamp(row.occurred_at)}</td><td className="min-w-36">{labels[row.kind] || row.kind}</td><td className="whitespace-nowrap">{money(row.amount_cents)}</td><td className="min-w-28 break-words">{row.method || '—'}</td><td className="min-w-48 break-all">{row.note || '—'}</td></tr>)}
        </Table>}
        <div className="flex items-center justify-between gap-2"><Button variant="secondary" disabled={loading || busy || data.page <= 1} onClick={() => void load(filters, data.page - 1)}>Назад</Button><span className="text-sm text-dark-400" role="status">{loading ? 'Обновляем…' : `Страница ${data.page}`}</span><Button variant="secondary" disabled={loading || busy || !data.has_more[tab]} onClick={() => void load(filters, data.page + 1)}>Далее</Button></div>
      </section>
      <p className="text-sm text-dark-400">Пробные периоды не участвуют в начислениях. Ставка закрепляется за клиентом и сохраняется для следующих покупок.</p>
    </main>}
  </div>;
}
