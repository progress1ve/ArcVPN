import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { getJson } from './api';
import { adminDate, answerNames, parseAnswer, surveyName } from './profileFormat';

const control =
  'rounded-lg border border-dark-700 bg-dark-900 px-3 py-2 text-sm text-dark-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400 disabled:opacity-40';
export default function ArcFeedback() {
  const [event, setEvent] = useState('all'),
    [answer, setAnswer] = useState('all'),
    [paid, setPaid] = useState('all'),
    [search, setSearch] = useState(''),
    [cursor, setCursor] = useState(0);
  const query = useQuery({
    queryKey: ['arc-feedback', event, answer, paid, search, cursor],
    queryFn: () =>
      getJson(
        `/api/admin/feedback?${new URLSearchParams({ event, answer, paid, q: search, cursor: String(cursor), limit: '25' })}`,
      ),
  });
  const data = query.data;
  const summary: Record<string, any>[] = data?.summary || [];
  const count = (kind: string) =>
    summary
      .filter((row) =>
        kind === 'unanswered'
          ? row.answer === 'unanswered'
          : kind === 'replied'
            ? row.answer !== 'unanswered'
            : kind === 'problems'
              ? ['connection', 'speed', 'service', 'setup', 'quality'].includes(row.answer)
              : false,
      )
      .reduce((sum, row) => sum + Number(row.count), 0);
  return (
    <main className="min-w-0 space-y-5 pb-12">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/admin" className="text-sm text-accent-400">
            ← Админка
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-dark-50">Ответы пользователей</h1>
          <p className="mt-1 text-sm text-dark-400">
            Что понравилось, что не работало и почему не продлили
          </p>
        </div>
        <button className={control} disabled={query.isFetching} onClick={() => query.refetch()}>
          Обновить
        </button>
      </header>
      {data && (
        <section className="grid gap-3 sm:grid-cols-3" aria-label="Сводка опросов">
          {[
            ['replied', 'Получено ответов', 'all'],
            ['problems', 'Сообщили о проблеме', 'problems'],
            ['unanswered', 'Опрос без ответа', 'unanswered'],
          ].map(([kind, label, filter]) => (
            <button
              key={kind}
              className="rounded-xl border border-dark-700 bg-dark-900/50 p-4 text-left hover:border-accent-400"
              onClick={() => {
                setAnswer(filter);
                setCursor(0);
              }}
            >
              <p className="text-xs text-dark-400">{label}</p>
              <p className="mt-1 text-2xl font-semibold text-dark-100">{count(kind)}</p>
              <p className="mt-1 text-xs text-dark-400">Все отправленные опросы · показать →</p>
            </button>
          ))}
        </section>
      )}
      <div className="flex flex-wrap gap-2">
        <input
          className={`${control} min-w-0 flex-1`}
          aria-label="Поиск ответов"
          placeholder="Пользователь или текст комментария"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setCursor(0);
          }}
        />
        <select
          aria-label="Опрос"
          className={control}
          value={event}
          onChange={(e) => {
            setEvent(e.target.value);
            setCursor(0);
          }}
        >
          <option value="all">Все опросы</option>
          <option value="trial">Оценка VPN</option>
          <option value="winback">Почему не продлил</option>
        </select>
        <select
          aria-label="Ответ"
          className={control}
          value={answer}
          onChange={(e) => {
            setAnswer(e.target.value);
            setCursor(0);
          }}
        >
          <option value="all">Все ответы</option>
          <option value="problems">Проблемы с VPN</option>
          <option value="unanswered">Не ответили</option>
          {Object.entries(answerNames).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <select
          aria-label="Покупка после регистрации"
          className={control}
          value={paid}
          onChange={(e) => {
            setPaid(e.target.value);
            setCursor(0);
          }}
        >
          <option value="all">Любая оплата</option>
          <option value="yes">Была покупка</option>
          <option value="no">Без покупки</option>
        </select>
      </div>
      {query.isError && (
        <div role="alert" className="p-4 text-error-400">
          Не удалось загрузить ответы.{' '}
          <button className={control} onClick={() => query.refetch()}>
            Повторить
          </button>
        </div>
      )}
      {query.isLoading && (
        <p role="status" className="p-5 text-dark-400">
          Загружаем ответы…
        </p>
      )}
      {data && (
        <section
          className="overflow-hidden rounded-xl border border-dark-700 bg-dark-900/50"
          aria-label="Ответы и комментарии"
        >
          {!data.items.length && (
            <p className="p-5 text-sm text-dark-400">По этим фильтрам записей нет.</p>
          )}
          {data.items.map((row: Record<string, any>, index: number) => {
            const parsed = row.answer ? parseAnswer(row.answer) : null;
            return (
              <article
                className="grid min-w-0 gap-3 border-b border-dark-700 p-4 last:border-b-0 md:grid-cols-[180px_minmax(0,1fr)_130px]"
                key={`${row.telegram_id}-${index}`}
              >
                <div>
                  <Link
                    className="break-words text-sm font-semibold text-accent-400"
                    to={`/admin/users/${row.telegram_id}`}
                  >
                    {row.first_name || row.username || `ID ${row.telegram_id}`}
                  </Link>
                  <p className="mt-1 break-words text-xs text-dark-400">
                    {row.username ? `@${row.username}` : row.telegram_id}
                  </p>
                  <p className="mt-2 text-xs text-dark-400">
                    {row.has_paid ? 'Была покупка' : 'Без покупки'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-dark-400">{surveyName(row.event_key)}</p>
                  <h2
                    className={`mt-1 text-sm font-medium ${parsed ? 'text-dark-100' : 'text-dark-400'}`}
                  >
                    {parsed?.label || 'Не ответил'}
                  </h2>
                  {parsed?.comment && (
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-dark-200">
                      {parsed.comment}
                    </p>
                  )}
                </div>
                <time className="text-xs text-dark-400">
                  {row.answered_at ? 'Ответил' : 'Опрос отправлен'}
                  <span className="mt-1 block">
                    {adminDate(row.answered_at || row.sent_at)} МСК
                  </span>
                </time>
              </article>
            );
          })}
        </section>
      )}
      {data && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-dark-400">
            {data.total
              ? `${cursor + 1}–${Math.min(cursor + 25, data.total)} из ${data.total}`
              : '0 записей'}
          </p>
          <div className="flex gap-2">
            <button
              className={control}
              disabled={!cursor || query.isFetching}
              onClick={() => setCursor(Math.max(0, cursor - 25))}
            >
              Назад
            </button>
            <button
              className={control}
              disabled={data.next_cursor == null || query.isFetching}
              onClick={() => setCursor(data.next_cursor)}
            >
              Далее
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
