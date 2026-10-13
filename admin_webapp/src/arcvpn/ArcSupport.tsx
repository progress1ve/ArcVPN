import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { SectionHeading } from '@/components/admin/SectionHeading';
import { access, getJson } from './api';
import { adminDate, supportStatus, waitingDuration } from './profileFormat';

const control =
  'rounded-lg border border-dark-700 bg-dark-900 px-3 py-2 text-sm text-dark-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400 disabled:opacity-40';
const handoffReason: Record<string, string> = {
  spam: 'Много сообщений подряд',
  diagnosis: 'Не удалось решить проблему',
  payment: 'Вопрос оплаты',
  manager: 'Пользователь попросил менеджера',
};
export default function ArcSupport() {
  const navigate = useNavigate();
  const { ticketId } = useParams();
  const id = Number(ticketId) || null;
  const [status, setStatus] = useState(''),
    [order, setOrder] = useState('waiting'),
    [search, setSearch] = useState(''),
    [cursor, setCursor] = useState(0),
    [drafts, setDrafts] = useState<Record<number, string>>({}),
    [notice, setNotice] = useState('');
  const client = useQueryClient();
  const permissions = useQuery({ queryKey: ['arc-support-access'], queryFn: access });
  const canReply =
    permissions.data?.role === 'owner' ||
    permissions.data?.permissions?.includes('*') ||
    permissions.data?.permissions?.includes('support.reply');
  const listing = useQuery({
    queryKey: ['arc-support-list', status, order, search, cursor],
    queryFn: () =>
      getJson(
        `/api/admin/support/threads?${new URLSearchParams({ status, order, q: search, cursor: String(cursor), limit: '25' })}`,
      ),
    refetchInterval: 15000,
  });
  const detail = useQuery({
    queryKey: ['arc-support-thread', id],
    queryFn: () => getJson(`/api/admin/support/threads/${id}`),
    enabled: !!id,
    refetchInterval: 15000,
  });
  const refresh = () => {
    client.invalidateQueries({ queryKey: ['arc-support-unread'] });
    client.invalidateQueries({ queryKey: ['arc-support-list'] });
    client.invalidateQueries({ queryKey: ['arc-support-thread', id] });
    client.invalidateQueries({ queryKey: ['arc-user-profile'] });
  };
  const reply = useMutation({
    mutationFn: ({ threadId, body }: { threadId: number; body: string }) =>
      getJson(`/api/admin/support/threads/${threadId}`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      }),
    onSuccess: (_data, variables) => {
      setDrafts((prev) => ({ ...prev, [variables.threadId]: '' }));
      if (id === variables.threadId) setNotice('Ответ отправлен в диалог пользователя.');
      refresh();
    },
  });
  const changeStatus = useMutation({
    mutationFn: ({ threadId, value }: { threadId: number; value: string }) =>
      getJson(`/api/admin/support/threads/${threadId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: value }),
      }),
    onSuccess: () => {
      setNotice('Статус сохранён.');
      refresh();
    },
  });
  const thread = detail.data?.thread;
  useEffect(() => {
    if (thread?.id) {
      client.invalidateQueries({ queryKey: ['arc-support-unread'] });
      client.invalidateQueries({ queryKey: ['arc-support-list'] });
    }
  }, [thread?.id, detail.dataUpdatedAt, client]);
  const rows = listing.data?.threads || [];
  const draft = id ? drafts[id] || '' : '';
  return (
    <main className="min-w-0 space-y-5 pb-12">
      <SectionHeading
        title="Тикеты"
        description="Переписка пользователей, ответы ИИ и работа менеджера"
        backLabel="Вернуться в админку"
        onBack={() => navigate('/admin')}
      />
      <div className="flex flex-wrap gap-2">
        <input
          aria-label="Поиск обращений"
          className={`${control} min-w-0 flex-1`}
          placeholder="Имя, @username или Telegram ID"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setCursor(0);
          }}
        />
        <select
          aria-label="Фильтр обращений"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setCursor(0);
          }}
          className={control}
        >
          <option value="">Все обращения</option>
          <option value="waiting">Ждут ответа</option>
          <option value="handoff">Нужен менеджер</option>
          <option value="unread">Непрочитанные</option>
          {Object.entries(supportStatus).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <select
          aria-label="Порядок обращений"
          className={`${control} max-w-full`}
          value={order}
          onChange={(e) => {
            setOrder(e.target.value);
            setCursor(0);
          }}
        >
          <option value="waiting">Дольше ждут ответа</option>
          <option value="newest">Новые сообщения сначала</option>
          <option value="unreviewed">Дольше не прочитаны</option>
          <option value="created">Новые обращения сначала</option>
        </select>
      </div>
      <p className="text-xs text-dark-400">
        Ожидание считается от первого сообщения без ответа. Для переданных менеджеру обращений ответ
        ИИ не завершает ожидание. Список обновляется автоматически.
      </p>
      <div className="grid min-w-0 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section
          className={`${id ? 'hidden lg:block' : ''} min-w-0 overflow-hidden rounded-xl border border-dark-700 bg-dark-900/50`}
          aria-label="Список обращений"
        >
          {listing.isLoading && (
            <p role="status" className="p-4 text-dark-400">
              Загружаем обращения…
            </p>
          )}
          {listing.isError && (
            <p role="alert" className="p-4 text-error-400">
              Не удалось загрузить список.{' '}
              <button onClick={() => listing.refetch()}>Повторить</button>
            </p>
          )}
          {listing.data && !rows.length && (
            <p className="p-4 text-sm text-dark-400">Обращений по этому фильтру нет.</p>
          )}
          {rows.map((row: Record<string, any>) => (
            <Link
              key={row.id}
              onClick={() => setNotice('')}
              to={`/admin/tickets/${row.id}`}
              className={`block min-w-0 border-b border-dark-700 p-4 hover:bg-dark-800/60 ${id === row.id ? 'bg-accent-500/10' : ''}`}
              aria-current={id === row.id ? 'page' : undefined}
            >
              <div className="flex items-center justify-between gap-2">
                <b className="min-w-0 break-words text-sm text-dark-100">
                  {row.first_name || row.username || `ID ${row.telegram_id}`}
                </b>
                {row.unread > 0 && (
                  <span className="rounded bg-accent-500/20 px-2 py-1 text-xs text-accent-300">
                    {row.unread} новых
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-dark-400">
                {supportStatus[row.status]} · {row.messages_count} сообщений
              </p>
              {row.ai_handoff_reason && row.status !== 'closed' && (
                <p className="mt-2 text-xs text-warning-400">Нужен менеджер</p>
              )}
              {row.waiting_since && (
                <p
                  className="mt-2 text-xs text-warning-400"
                  title={`Ждёт с ${adminDate(row.waiting_since)} МСК`}
                >
                  Ждёт ответа · {waitingDuration(row.waiting_since)}
                </p>
              )}
              {row.unreviewed_since && (
                <p
                  className="mt-1 text-xs text-accent-300"
                  title={`Не прочитано с ${adminDate(row.unreviewed_since)} МСК`}
                >
                  Не прочитано · {waitingDuration(row.unreviewed_since)}
                </p>
              )}
              <p className="mt-2 line-clamp-2 break-words text-sm text-dark-300">
                {row.last_message
                  ? `${row.last_sender === 'user' ? 'Пользователь' : row.last_is_ai ? 'ИИ' : 'Менеджер'}: ${row.last_message}`
                  : 'Сообщений нет'}
              </p>
              <time className="mt-2 block text-xs text-dark-500">
                Последнее сообщение · {adminDate(row.last_message_at || row.updated_at)}
              </time>
            </Link>
          ))}
          {listing.data && (
            <div className="flex items-center justify-between gap-2 p-3">
              <span className="text-xs text-dark-400">{listing.data.total} обращений</span>
              <div className="flex gap-1">
                <button
                  className={control}
                  aria-label="Предыдущие обращения"
                  disabled={!cursor || listing.isFetching}
                  onClick={() => setCursor(Math.max(0, cursor - 25))}
                >
                  ←
                </button>
                <button
                  className={control}
                  aria-label="Следующие обращения"
                  disabled={listing.data.next_cursor == null || listing.isFetching}
                  onClick={() => setCursor(listing.data.next_cursor)}
                >
                  →
                </button>
              </div>
            </div>
          )}
        </section>
        <section
          className={`${!id ? 'hidden lg:block' : ''} min-w-0 rounded-xl border border-dark-700 bg-dark-900/50 p-4 sm:p-5`}
          aria-label="Диалог поддержки"
        >
          {!id && (
            <p className="py-12 text-center text-sm text-dark-400">Выберите обращение из списка.</p>
          )}
          {id && (
            <Link to="/admin/tickets" className="mb-4 block text-sm text-accent-400 lg:hidden">
              ← Все обращения
            </Link>
          )}
          {detail.isLoading && id && (
            <p role="status" className="p-4 text-dark-400">
              Загружаем переписку…
            </p>
          )}
          {detail.isError && id && (
            <p role="alert" className="p-4 text-error-400">
              Не удалось загрузить диалог.{' '}
              <button className={control} onClick={() => detail.refetch()}>
                Повторить
              </button>
            </p>
          )}
          {thread && (
            <>
              <header className="flex flex-wrap items-start justify-between gap-3 border-b border-dark-700 pb-4">
                <div>
                  <Link
                    className="break-words text-lg font-semibold text-accent-400"
                    to={`/admin/users/${thread.telegram_id}`}
                  >
                    {thread.first_name || thread.username || `ID ${thread.telegram_id}`} →
                  </Link>
                  <p className="mt-1 text-xs text-dark-400">
                    {thread.username ? `@${thread.username} · ` : ''}ID {thread.telegram_id} ·{' '}
                    {supportStatus[thread.status]}
                  </p>
                </div>
                <select
                  aria-label="Статус диалога"
                  className={control}
                  disabled={!canReply || changeStatus.isPending || reply.isPending}
                  value={thread.status}
                  onChange={(e) =>
                    changeStatus.mutate({ threadId: thread.id, value: e.target.value })
                  }
                >
                  {Object.entries(supportStatus).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </header>
              {thread.ai_handoff_reason && thread.status !== 'closed' && (
                <p className="mt-4 rounded-lg border border-warning-500/30 p-3 text-sm text-warning-400">
                  Нужен менеджер:{' '}
                  {handoffReason[thread.ai_handoff_reason] || 'ИИ передал обращение'}. ИИ
                  приостановлен.
                </p>
              )}
              <div
                className="my-5 max-h-[55vh] space-y-4 overflow-y-auto pr-1"
                aria-label="Сообщения"
              >
                {detail.data!.messages.map((message: Record<string, any>) => (
                  <article
                    key={message.id}
                    className={`max-w-full rounded-lg border p-3 ${message.sender === 'user' ? 'border-dark-700 bg-dark-800/40' : message.is_ai ? 'border-dark-700 bg-dark-950/30' : 'border-accent-500/25 bg-accent-500/5'}`}
                  >
                    <div className="flex flex-wrap justify-between gap-2 text-xs">
                      <b
                        className={
                          message.is_ai
                            ? 'text-dark-400'
                            : message.sender === 'user'
                              ? 'text-dark-200'
                              : 'text-accent-300'
                        }
                      >
                        {message.sender === 'user'
                          ? 'Пользователь'
                          : message.is_ai
                            ? 'ИИ-помощник'
                            : 'Менеджер'}
                      </b>
                      <time className="text-dark-500">{adminDate(message.created_at)} МСК</time>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-dark-100">
                      {message.body}
                    </p>
                  </article>
                ))}
              </div>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  if (id && canReply && draft.trim() && !reply.isPending) {
                    setNotice('');
                    reply.mutate({ threadId: id, body: draft.trim() });
                  }
                }}
              >
                <label htmlFor="manager-reply" className="text-sm font-medium text-dark-200">
                  Ответ менеджера
                </label>
                <textarea
                  id="manager-reply"
                  value={draft}
                  disabled={!canReply || reply.isPending || thread.status === 'closed'}
                  onChange={(e) => id && setDrafts((prev) => ({ ...prev, [id]: e.target.value }))}
                  maxLength={4000}
                  rows={4}
                  placeholder={
                    thread.status === 'closed'
                      ? 'Откройте обращение, чтобы ответить'
                      : 'Сообщение пользователю…'
                  }
                  className={`${control} mt-2 w-full resize-y`}
                />
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-dark-400">
                    {canReply
                      ? 'Ответ сохраняется в кабинете; для Telegram-аккаунта отправляется уведомление.'
                      : 'Для вашей роли доступны только чтение и просмотр.'}
                  </p>
                  <button
                    className={`${control} border-accent-500 text-accent-300`}
                    disabled={
                      !canReply || !draft.trim() || reply.isPending || thread.status === 'closed'
                    }
                  >
                    {reply.isPending ? 'Отправляем…' : 'Отправить ответ'}
                  </button>
                </div>
                {(reply.isError || changeStatus.isError) && (
                  <p role="alert" className="mt-3 text-sm text-error-400">
                    Действие не удалось. Текст ответа сохранён.
                  </p>
                )}
                {notice && (
                  <p role="status" className="mt-3 text-sm text-success-400">
                    {notice}
                  </p>
                )}
              </form>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
