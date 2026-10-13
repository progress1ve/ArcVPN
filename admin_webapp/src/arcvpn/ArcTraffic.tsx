import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { getJson } from './api';
import { adminDate, gigabytes } from './profileFormat';

const control =
  'rounded-lg border border-dark-700 bg-dark-900 px-3 py-2 text-sm text-dark-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400 disabled:opacity-40';
export default function ArcTraffic() {
  const [period, setPeriod] = useState(7),
    [search, setSearch] = useState(''),
    [offset, setOffset] = useState(0),
    [sort, setSort] = useState('total_bytes'),
    [descending, setDescending] = useState(true),
    [start, setStart] = useState(''),
    [end, setEnd] = useState(''),
    [custom, setCustom] = useState(false);
  const valid = !custom || Boolean(start && end && start <= end);
  const query = useQuery({
    queryKey: ['arc-traffic', period, search, offset, sort, descending, custom, start, end],
    queryFn: () => {
      const params = new URLSearchParams({
        search,
        offset: String(offset),
        limit: '25',
        sort_by: sort,
        sort_desc: String(descending),
      });
      if (custom) {
        params.set('start_date', start);
        params.set('end_date', end);
      } else params.set('period', String(period));
      return getJson(`/api/admin/traffic/period?${params}`);
    },
    enabled: valid,
    staleTime: 60000,
  });
  const data = query.data;
  const sortBy = (column: string) => {
    setDescending(sort === column ? !descending : true);
    setSort(column);
    setOffset(0);
  };
  return (
    <main className="min-w-0 space-y-5 pb-12">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link className="text-sm text-accent-400" to="/admin">
            ← Админка
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-dark-50">Расход трафика</h1>
          <p className="mt-1 text-sm text-dark-400">Обычные ноды и LTE-обход за выбранные даты</p>
        </div>
        <button
          className={control}
          disabled={query.isFetching || !valid}
          onClick={() => query.refetch()}
        >
          Обновить
        </button>
      </header>
      <div className="flex flex-wrap items-center gap-2">
        {[1, 7, 30].map((days) => (
          <button
            key={days}
            aria-pressed={!custom && period === days}
            className={`${control} ${!custom && period === days ? 'border-accent-500 text-accent-300' : ''}`}
            onClick={() => {
              setPeriod(days);
              setCustom(false);
              setOffset(0);
            }}
          >
            {days === 1 ? 'Сегодня' : `${days} дней`}
          </button>
        ))}
        <button
          className={control}
          aria-pressed={custom}
          onClick={() => {
            setCustom(!custom);
            setOffset(0);
          }}
        >
          Свои даты
        </button>
        <input
          className={`${control} min-w-0 flex-1 sm:max-w-sm`}
          aria-label="Поиск в расходе трафика"
          placeholder="Имя, @username или Telegram ID"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      {custom && (
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-dark-400">
            С{' '}
            <input
              type="date"
              aria-label="Начало периода"
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setOffset(0);
              }}
              className={control}
            />
          </label>
          <label className="text-sm text-dark-400">
            По{' '}
            <input
              type="date"
              aria-label="Конец периода"
              value={end}
              onChange={(e) => {
                setEnd(e.target.value);
                setOffset(0);
              }}
              className={control}
            />
          </label>
          {!valid && (
            <p className="self-center text-xs text-warning-400">Укажите даты по порядку.</p>
          )}
        </div>
      )}
      {query.isError && (
        <div role="alert" className="rounded-xl border border-error-500/30 p-4 text-error-400">
          Не удалось получить расход за эти даты.{' '}
          <button className={control} onClick={() => query.refetch()}>
            Повторить
          </button>
        </div>
      )}
      {query.isLoading && valid && (
        <p role="status" className="p-5 text-dark-400">
          Получаем статистику панели…
        </p>
      )}
      {data && (
        <>
          <p className="text-xs text-dark-400">
            {data.start_date} — {data.end_date} включительно · дни UTC · Обновлено{' '}
            {adminDate(data.as_of)} МСК
          </p>
          <section
            className="grid gap-3 sm:grid-cols-3"
            aria-label="Расход всех пользователей за период"
          >
            {[
              ['main', 'Обычные ноды'],
              ['lte', 'LTE-ноды'],
            ].map(([key, label]) => (
              <div key={key} className="rounded-xl border border-dark-700 bg-dark-900/50 p-4">
                <p className="text-xs text-dark-400">{label} · все пользователи</p>
                <p className="mt-1 text-2xl font-semibold text-dark-100">
                  {gigabytes(data.groups[key].bytes)}
                </p>
                {data.groups[key].unmapped_bytes > 0 && (
                  <p className="mt-1 text-xs text-warning-400">
                    {gigabytes(data.groups[key].unmapped_bytes)} без сопоставленного пользователя
                  </p>
                )}
              </div>
            ))}
            <div className="rounded-xl border border-dark-700 bg-dark-900/50 p-4">
              <p className="text-xs text-dark-400">Всего · все пользователи</p>
              <p className="mt-1 text-2xl font-semibold text-dark-100">
                {gigabytes(data.groups.main.bytes + data.groups.lte.bytes)}
              </p>
            </div>
          </section>
          <section className="overflow-hidden rounded-xl border border-dark-700 bg-dark-900/50">
            <div className="hidden grid-cols-[minmax(0,1fr)_130px_130px_130px] gap-4 border-b border-dark-700 px-5 py-3 text-xs text-dark-400 sm:grid">
              <span>Пользователь · {data.total}</span>
              {[
                ['main_bytes', 'Обычный'],
                ['lte_bytes', 'LTE'],
                ['total_bytes', 'Всего'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  aria-label={`Сортировать: ${label}`}
                  aria-pressed={sort === key}
                  className="text-right text-dark-300 hover:text-accent-300"
                  onClick={() => sortBy(key)}
                >
                  {label} {sort === key ? (descending ? '↓' : '↑') : '↕'}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 p-3 sm:hidden">
              <select
                aria-label="Сортировка расхода трафика"
                value={sort}
                onChange={(e) => sortBy(e.target.value)}
                className={control}
              >
                <option value="total_bytes">По общему расходу</option>
                <option value="main_bytes">По обычному трафику</option>
                <option value="lte_bytes">По LTE-трафику</option>
              </select>
              <button className={control} onClick={() => setDescending(!descending)}>
                {descending ? 'По убыванию ↓' : 'По возрастанию ↑'}
              </button>
            </div>
            {data.items.length === 0 && (
              <p className="p-5 text-sm text-dark-400">Пользователей по этому запросу нет.</p>
            )}
            {data.items.map((row: Record<string, any>) => (
              <article
                key={row.user_id}
                className="grid min-w-0 gap-3 border-b border-dark-700/70 px-4 py-4 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_130px_130px_130px] sm:gap-4 sm:px-5"
              >
                <Link className="min-w-0" to={`/admin/users/${row.telegram_id}`}>
                  <b className="break-words text-sm text-dark-100 hover:text-accent-300">
                    {row.first_name || row.username || 'Без имени'}
                  </b>
                  <small className="mt-1 block break-words text-xs text-dark-400">
                    {row.username ? `@${row.username} · ` : ''}
                    {row.telegram_id}
                  </small>
                </Link>
                <div className="grid grid-cols-3 gap-2 sm:contents">
                  {[
                    ['main_bytes', 'Обычный'],
                    ['lte_bytes', 'LTE'],
                    ['total_bytes', 'Всего'],
                  ].map(([key, label]) => (
                    <div key={key} className="text-sm tabular-nums text-dark-200 sm:text-right">
                      <small className="mb-1 block text-xs text-dark-400 sm:hidden">{label}</small>
                      <span className={key === 'total_bytes' ? 'font-semibold' : ''}>
                        {gigabytes(row[key])}
                      </span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-dark-400">
              {data.total
                ? `${offset + 1}–${Math.min(offset + 25, data.total)} из ${data.total}`
                : '0 пользователей'}
            </p>
            <div className="flex gap-2">
              <button
                className={control}
                disabled={!offset || query.isFetching}
                onClick={() => setOffset(Math.max(0, offset - 25))}
              >
                Назад
              </button>
              <button
                className={control}
                disabled={offset + 25 >= data.total || query.isFetching}
                onClick={() => setOffset(offset + 25)}
              >
                Далее
              </button>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
