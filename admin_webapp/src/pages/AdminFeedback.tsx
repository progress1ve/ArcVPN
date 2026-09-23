import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { BackIcon } from '@/components/icons';
import { getJson } from '@/arcvpn/api';

type FeedbackEvent = 'trial' | 'winback';
type FeedbackRow = {
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  event_key: string;
  answer: string;
  answered_at: string | null;
  has_paid: number;
};
type FeedbackSummary = { event: FeedbackEvent; answer: string; count: number; paid_count: number };
type FeedbackResponse = {
  summary: FeedbackSummary[];
  items: FeedbackRow[];
  total: number;
  next_cursor: number | null;
};

const names: Record<string, string> = {
  great: 'Всё отлично', connection: 'Проблема подключения', speed: 'Низкая скорость',
  service: 'Не работал нужный сервис', setup: 'Сложно настроить', other: 'Другое',
  expensive: 'Дорого', quality: 'Качество', competitor: 'Другой VPN',
  '1': 'Оценка 1', '3': 'Оценка 3', '5': 'Оценка 5',
};

function answerParts(raw: string) {
  const separator = raw.indexOf(':');
  const code = separator < 0 ? raw.trim() : raw.slice(0, separator).trim();
  return { label: names[code] || code, detail: separator < 0 ? '' : raw.slice(separator + 1).trim() };
}

const time = (value: string | null) => value
  ? new Date(value.includes('T') ? value : `${value.replace(' ', 'T')}Z`).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' }) + ' МСК'
  : '—';

export default function AdminFeedback() {
  const [event, setEvent] = useState<'all' | FeedbackEvent>('all');
  const [answer, setAnswer] = useState('all');
  const [paid, setPaid] = useState('all');
  const [cursor, setCursor] = useState(0);
  const query = useQuery<FeedbackResponse>({
    queryKey: ['admin-feedback', event, answer, paid, cursor],
    queryFn: async () => {
      const params = new URLSearchParams({ event, answer, paid, cursor: String(cursor), limit: '25' });
      return getJson(`/api/admin/feedback?${params}`) as Promise<FeedbackResponse>;
    },
  });
  const data = query.data;
  const overview = data?.summary || [];
  const count = (selected: FeedbackEvent, code?: string) => overview
    .filter((row) => row.event === selected && (!code || row.answer === code))
    .reduce((sum, row) => sum + row.count, 0);
  const filter = (kind: 'event' | 'answer' | 'paid', value: string) => {
    if (kind === 'event') { setEvent(value as 'all' | FeedbackEvent); setAnswer('all'); }
    if (kind === 'answer') setAnswer(value);
    if (kind === 'paid') setPaid(value);
    setCursor(0);
  };
  return <main className="space-y-5 pb-12">
    <header className="flex items-center gap-3">
      <Link to="/admin" aria-label="Вернуться" className="flex h-10 w-10 items-center justify-center rounded-xl border border-dark-700 bg-dark-800"><BackIcon /></Link>
      <div><h1 className="text-2xl font-semibold text-dark-50">Ответы пользователей</h1>
        <p className="text-sm text-dark-400">Оценка триала и причины отказа от продления</p></div>
    </header>
    {query.isError && <div role="alert" className="rounded-xl border border-error-500/30 p-4 text-error-400">Не удалось загрузить ответы. <button onClick={() => query.refetch()} className="underline">Повторить</button></div>}
    <section className="grid gap-3 sm:grid-cols-3" aria-label="Сводка ответов">
      {(['trial', 'winback'] as const).map((kind) => {
        const sent = count(kind);
        const replied = sent - count(kind, 'unanswered');
        return <div key={kind} className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
          <p className="text-sm text-dark-400">{kind === 'trial' ? 'Опрос после триала' : 'Причина ухода'}</p>
          <p className="mt-1 text-2xl font-semibold text-dark-50">{replied} <span className="text-sm font-normal text-dark-400">из {sent} ответили</span></p>
          <p className="mt-1 text-xs text-dark-400">Ответили {sent ? Math.round(replied / sent * 100) : 0}%</p>
        </div>;
      })}
      <div className="rounded-xl border border-dark-700 bg-dark-800/50 p-4">
        <p className="text-sm text-dark-400">Жалобы на скорость</p>
        <p className="mt-1 text-2xl font-semibold text-dark-50">{count('trial', 'speed')}</p>
        <p className="mt-1 text-xs text-dark-400">Кнопка «Низкая скорость»; дальнейшая покупка показана отдельно</p>
      </div>
    </section>
    <section className="rounded-xl border border-dark-700 bg-dark-800/40 p-4">
      <h2 className="mb-3 text-base font-semibold text-dark-100">Распределение ответов</h2>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {overview.filter((row) => row.answer !== 'unanswered').map((row) =>
          <button key={`${row.event}-${row.answer}`} onClick={() => { filter('event', row.event); setAnswer(row.answer); }}
            className="flex items-center justify-between gap-3 rounded-lg border border-dark-700 px-3 py-2 text-left hover:border-accent-500 focus-visible:outline-accent-400">
            <span className="text-sm text-dark-200">{row.event === 'trial' ? 'Триал · ' : 'Уход · '}{names[row.answer] || row.answer}</span>
            <span className="text-sm font-semibold text-dark-50">{row.count} <small className="font-normal text-dark-400">({row.paid_count} с оплатой)</small></span>
          </button>)}
        {!overview.some((row) => row.answer !== 'unanswered') && <p className="text-sm text-dark-400">Ответов пока нет.</p>}
      </div>
    </section>
    <section className="rounded-xl border border-dark-700 bg-dark-800/40 p-4">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-base font-semibold text-dark-100">Кто и что ответил <span className="text-sm font-normal text-dark-400">{data?.total ?? 0}</span></h2>
        <div className="flex flex-wrap gap-2">
          <label className="text-xs text-dark-400">Опрос<select aria-label="Опрос" value={event} onChange={(e) => filter('event', e.target.value)} className="ml-2 rounded-lg border border-dark-700 bg-dark-900 p-2 text-sm text-dark-100"><option value="all">Все</option><option value="trial">Триал</option><option value="winback">Уход</option></select></label>
          <label className="text-xs text-dark-400">Ответ<select aria-label="Ответ" value={answer} onChange={(e) => filter('answer', e.target.value)} className="ml-2 rounded-lg border border-dark-700 bg-dark-900 p-2 text-sm text-dark-100"><option value="all">Все</option>{Object.entries(names).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="text-xs text-dark-400">Оплата<select aria-label="Оплата" value={paid} onChange={(e) => filter('paid', e.target.value)} className="ml-2 rounded-lg border border-dark-700 bg-dark-900 p-2 text-sm text-dark-100"><option value="all">Любая</option><option value="yes">Была</option><option value="no">Не было</option></select></label>
        </div>
      </div>
      {query.isLoading && <p className="py-8 text-center text-sm text-dark-400">Загрузка…</p>}
      {!query.isLoading && !query.isError && !data?.items.length && <p className="py-8 text-center text-sm text-dark-400">По этим фильтрам ответов нет.</p>}
      <div className="divide-y divide-dark-700">{data?.items.map((row, index) => {
        const parsed = answerParts(row.answer);
        return <Link key={`${row.telegram_id}-${row.event_key}-${index}`} to={`/admin/users/${row.telegram_id}`} className="flex flex-wrap items-center gap-3 py-3 hover:bg-dark-700/30 focus-visible:outline-accent-400">
          <span className="min-w-44 flex-1 font-medium text-dark-100">{row.first_name || row.username || 'Пользователь'} {row.username && <small className="text-dark-400">@{row.username}</small>}</span>
          <span className="min-w-48 flex-[2] text-sm text-dark-200">{parsed.label}{parsed.detail && <small className="ml-2 text-dark-400">{parsed.detail}</small>}</span>
          <span className={row.has_paid ? 'text-xs text-success-400' : 'text-xs text-dark-400'}>{row.has_paid ? 'Была оплата' : 'Без оплаты'}</span>
          <time className="text-xs text-dark-400">{time(row.answered_at)}</time>
        </Link>;
      })}</div>
      <div className="mt-4 flex justify-end gap-2">
        <button disabled={!cursor || query.isFetching} onClick={() => setCursor(Math.max(0, cursor - 25))} className="rounded-lg border border-dark-700 px-3 py-2 text-sm text-dark-200 disabled:opacity-40">Назад</button>
        <button disabled={data?.next_cursor == null || query.isFetching} onClick={() => setCursor(data!.next_cursor!)} className="rounded-lg border border-dark-700 px-3 py-2 text-sm text-dark-200 disabled:opacity-40">Далее</button>
      </div>
    </section>
  </main>;
}
