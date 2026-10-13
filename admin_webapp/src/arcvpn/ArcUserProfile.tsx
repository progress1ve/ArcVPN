import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { getJson } from './api';
import {
  adminDate,
  gigabytes,
  parseAnswer,
  rubles,
  supportStatus,
  surveyName,
} from './profileFormat';

type Row = Record<string, any>;
const tabs = [
  'Сводка',
  'Покупки',
  'Трафик',
  'Устройства',
  'Рефералы',
  'Ответы',
  'Поддержка',
  'История',
];
const panel = 'rounded-xl border border-dark-700 bg-dark-900/50 p-4 sm:p-5';
const button =
  'rounded-lg border border-dark-700 px-3 py-2 text-sm text-dark-200 hover:border-accent-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400 disabled:opacity-40';

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 py-3">
      <dt className="text-xs text-dark-400">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-dark-100">{children}</dd>
    </div>
  );
}
function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-5 text-sm text-dark-400">{children}</p>;
}
function Amount({ payment }: { payment: Row }) {
  return (
    <>
      {payment.amount_rub > 0
        ? rubles(payment.amount_rub)
        : payment.amount_usd > 0
          ? `${payment.amount_usd} USD`
          : payment.amount_stars > 0
            ? `${payment.amount_stars} Stars`
            : 'Бесплатно'}
    </>
  );
}

export default function ArcUserProfile() {
  const { id } = useParams();
  const [tab, setTab] = useState('Сводка');
  const [period, setPeriod] = useState(7);
  const [paymentCursor, setPaymentCursor] = useState(0);
  useEffect(() => {
    setPaymentCursor(0);
    setTab('Сводка');
  }, [id]);
  const query = useQuery({
    queryKey: ['arc-user-profile', id, paymentCursor],
    queryFn: () => getJson(`/api/admin/users/${id}/profile?payment_cursor=${paymentCursor}`),
    enabled: !!id,
    refetchInterval: 30000,
  });
  const traffic = useQuery({
    queryKey: ['arc-user-traffic', id, period],
    queryFn: () =>
      getJson(`/api/admin/traffic/period?telegram_id=${encodeURIComponent(id || '')}&period=${period}`),
    enabled: tab === 'Трафик' && !!id,
    staleTime: 60000,
  });
  if (query.isLoading)
    return (
      <p role="status" className="p-8 text-dark-300">
        Загружаем данные пользователя…
      </p>
    );
  if (query.isError || !query.data)
    return (
      <div role="alert" className={panel}>
        <p>Не удалось загрузить карточку.</p>
        <button className={button} onClick={() => query.refetch()}>
          Повторить
        </button>
      </div>
    );
  const data = query.data,
    user = data.user,
    summary = data.summary,
    presence = data.presence;
  const subscriptions: Row[] = data.subscriptions || [],
    payments: Row[] = data.payments || [],
    devices: Row[] = data.devices || [];
  const current = subscriptions.find((sub) => sub.active) || subscriptions[0];
  const active = Boolean(current?.active);
  const replies: Row[] = data.lifecycle_answers || [];
  const support: Row[] | null = data.support;
  const name =
    user.first_name ||
    user.username ||
    (user.telegram_id > 0 ? 'Пользователь без имени' : 'Клиент сайта');
  const total = summary.purchase_totals;
  const spent =
    [
      total.rub > 0 ? rubles(total.rub) : '',
      total.usd > 0 ? `${total.usd} USD` : '',
      total.stars > 0 ? `${total.stars} Stars` : '',
    ]
      .filter(Boolean)
      .join(' + ') || rubles(0);
  const onTab = (next: string) => setTab(next);
  return (
    <main className="min-w-0 space-y-5 pb-12">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link className="text-sm text-accent-400 hover:underline" to="/admin/users">
            ← Пользователи
          </Link>
          <h1 className="mt-2 break-words text-2xl font-semibold text-dark-50">{name}</h1>
          <p className="mt-1 text-sm text-dark-400">
            {user.username && `@${user.username} · `}
            {user.telegram_id > 0
              ? `Telegram ID ${user.telegram_id}`
              : `Клиент сайта · ID ${user.id}`}
          </p>
        </div>
        <button className={button} disabled={query.isFetching} onClick={() => query.refetch()}>
          {query.isFetching ? 'Обновляем…' : 'Обновить'}
        </button>
      </header>
      <section className={panel} aria-label="Главное о пользователе">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <strong className={active ? 'text-success-400' : 'text-warning-400'}>
            {current?.panel_disabled_at
              ? 'Доступ отключён'
              : active
                ? 'Подписка действует'
                : current
                  ? 'Подписка истекла'
                  : 'Подписки нет'}
          </strong>
          <span className="text-dark-500">·</span>
          <span className={presence.online ? 'text-success-400' : 'text-dark-300'}>
            {presence.online === null
              ? 'Онлайн неизвестен'
              : presence.online
                ? 'Сейчас онлайн'
                : 'Сейчас не в сети'}
          </span>
        </div>
        <dl className="mt-2 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-4">
          <Fact label="Тариф">
            {current?.plan_name || 'Подписки нет'}
            {current && (
              <small className="mt-1 block font-normal text-dark-400">
                {user.device_limit} устройств · {user.lte_quota_gb} ГБ LTE
              </small>
            )}
          </Fact>
          <Fact label="Первая подписка">{adminDate(summary.first_subscription_at)}</Fact>
          <Fact label="Действует до">{adminDate(current?.expires_at)}</Fact>
          <Fact label="Покупки за всё время">
            {spent}
            <small className="mt-1 block font-normal text-dark-400">
              {total.count} оплаченных покупок
            </small>
          </Fact>
        </dl>
      </section>
      <nav aria-label="Разделы карточки" className="flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button
            key={item}
            className={`${button} ${tab === item ? 'border-accent-500 bg-accent-500/10 text-accent-300' : ''}`}
            aria-pressed={tab === item}
            onClick={() => onTab(item)}
          >
            {item}
            {item === 'Ответы' && replies.length > 0
              ? ` · ${replies.length}`
              : item === 'Поддержка' && support?.length
                ? ` · ${support.length}`
                : ''}
          </button>
        ))}
      </nav>
      <section className={panel} aria-label={tab}>
        {tab === 'Сводка' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">Подписка и использование</h2>
            <dl className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
              <Fact label="Основной трафик · текущий счётчик">
                {gigabytes(
                  subscriptions.reduce((sum, sub) => sum + Number(sub.traffic_used || 0), 0),
                )}
              </Fact>
              <Fact label="LTE-трафик · текущий цикл">
                {gigabytes(user.lte_used_bytes)} / {user.lte_quota_gb} ГБ
              </Fact>
              <Fact label="Зарегистрированные устройства">
                {devices.filter((device) => device.active).length} / {user.device_limit}
              </Fact>
              <Fact label="Последний раз онлайн">{adminDate(presence.last_online_at)}</Fact>
              <Fact label="Последняя наблюдаемая нода">
                {presence.last_node || 'Нет достоверных данных'}
              </Fact>
              <Fact label="Зарегистрирован">{adminDate(user.created_at)}</Fact>
            </dl>
            <p className="mt-2 text-xs leading-relaxed text-dark-400">
              Время — МСК. Онлайн: {presence.source}, наблюдение за последние 3 минуты. Первая
              подписка — самая ранняя запись среди сохранённых подписок. Счётчики могут
              сбрасываться; расход за выбранные даты — во вкладке «Трафик».
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {[
                ['Устройства', `${devices.filter((d) => d.active).length} активных`],
                ['Ответы', replies.length ? `${replies.length} ответов` : 'Ещё не отвечал'],
                [
                  'Поддержка',
                  support === null
                    ? 'Доступ ограничен'
                    : support.some((t) => t.user_messages > 0)
                      ? 'Писал в поддержку'
                      : 'Обращений нет',
                ],
              ].map(([target, label]) => (
                <button
                  className={`${button} text-left`}
                  key={target}
                  onClick={() => onTab(target)}
                >
                  <b className="block">{target}</b>
                  <span className="mt-1 block text-dark-400">{label} →</span>
                </button>
              ))}
            </div>
            {subscriptions.length > 1 && (
              <div className="mt-6">
                <h3 className="font-medium text-dark-100">Все подписки</h3>
                {subscriptions.map((sub) => (
                  <div
                    className="mt-3 flex flex-wrap justify-between gap-2 border-t border-dark-700 pt-3"
                    key={sub.id}
                  >
                    <span>{sub.plan_name}</span>
                    <span className="text-sm text-dark-400">
                      {sub.panel_disabled_at ? 'Отключена' : sub.active ? 'Действует' : 'Истекла'} ·
                      до {adminDate(sub.expires_at)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        {tab === 'Покупки' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">Что покупал пользователь</h2>
            <p className="mt-1 text-sm text-dark-400">
              Всего оплаченных покупок: {total.count} · {spent}. Пополнение баланса отдельно, без
              повторного учёта в расходах.
            </p>
            <p className="mt-2 text-xs text-dark-400">
              Баланс сейчас: {rubles(user.balance_rub || 0)}. Операции{' '}
              {payments.length ? `${paymentCursor + 1}–${paymentCursor + payments.length}` : '0'} из{' '}
              {data.payments_page?.total ?? payments.length}; итог рассчитан по всей истории.
            </p>
            {!payments.length && <Empty>Покупок пока нет.</Empty>}
            <div className="mt-4 divide-y divide-dark-700">
              {payments.map((payment, index) => (
                <article
                  key={payment.order_id || index}
                  className="grid gap-2 py-4 sm:grid-cols-[1fr_auto]"
                >
                  <div>
                    <h3 className="font-medium text-dark-100">
                      {payment.tariff_name || 'Покупка'}
                    </h3>
                    <p className="mt-1 text-xs text-dark-400">
                      {adminDate(payment.paid_at)} ·{' '}
                      {(
                        {
                          yookassa_qr: 'СБП',
                          yookassa_card: 'Карта',
                          balance: 'С баланса',
                          crypto: 'Криптовалюта',
                          stars: 'Telegram Stars',
                          trial: 'Триал',
                        } as Record<string, string>
                      )[payment.payment_type] || payment.payment_type}
                    </p>
                  </div>
                  <div className="sm:text-right">
                    <p className="font-semibold text-dark-100">
                      <Amount payment={payment} />
                    </p>
                    <p className="mt-1 text-xs text-dark-400">
                      {['paid', 'succeeded'].includes(payment.status)
                        ? 'Оплачено'
                        : payment.status === 'pending'
                          ? 'Ожидает оплаты'
                          : payment.status === 'canceled'
                            ? 'Отменено'
                            : payment.status}
                    </p>
                  </div>
                </article>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className={button}
                disabled={!paymentCursor || query.isFetching}
                onClick={() => setPaymentCursor(Math.max(0, paymentCursor - 100))}
              >
                Назад
              </button>
              <button
                className={button}
                disabled={data.payments_page?.next_cursor == null || query.isFetching}
                onClick={() => setPaymentCursor(data.payments_page.next_cursor)}
              >
                Далее
              </button>
            </div>
          </>
        )}
        {tab === 'Трафик' && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-dark-100">Расход за период</h2>
              <select
                aria-label="Период трафика пользователя"
                value={period}
                onChange={(e) => setPeriod(Number(e.target.value))}
                className={`${button} bg-dark-900`}
              >
                <option value="1">Сегодня</option>
                <option value="7">7 дней</option>
                <option value="30">30 дней</option>
              </select>
            </div>
            {traffic.isLoading && <Empty>Загружаем расход с панели…</Empty>}
            {traffic.isError && (
              <div role="alert" className="py-4 text-error-400">
                Расход за период недоступен.{' '}
                <button className={button} onClick={() => traffic.refetch()}>
                  Повторить
                </button>
              </div>
            )}
            {traffic.data &&
              (() => {
                const row = traffic.data.items.find(
                  (item: Row) => Number(item.telegram_id) === Number(id),
                );
                return (
                  <>
                    <p className="mt-2 text-xs text-dark-400">
                      {traffic.data.start_date} — {traffic.data.end_date}, включительно, дни UTC
                    </p>
                    <dl className="mt-3 grid sm:grid-cols-3">
                      <Fact label="Обычные ноды">{gigabytes(row?.main_bytes ?? 0)}</Fact>
                      <Fact label="LTE-ноды">{gigabytes(row?.lte_bytes ?? 0)}</Fact>
                      <Fact label="Всего за период">{gigabytes(row?.total_bytes ?? 0)}</Fact>
                    </dl>
                  </>
                );
              })()}
          </>
        )}
        {tab === 'Устройства' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">
              Устройства · {devices.filter((d) => d.active).length} / {user.device_limit}
            </h2>
            {!devices.length && <Empty>Устройства ещё не зарегистрированы.</Empty>}
            {devices.map((device) => (
              <article className="mt-4 border-t border-dark-700 pt-4" key={device.id}>
                <h3 className="font-medium text-dark-100">
                  {device.display_name || device.model || 'Без названия'}{' '}
                  <span
                    className={device.active ? 'text-xs text-success-400' : 'text-xs text-dark-400'}
                  >
                    {device.active ? 'Активно' : 'Отключено'}
                  </span>
                </h3>
                <p className="mt-1 text-sm text-dark-400">
                  {device.platform || 'Платформа неизвестна'}
                  {device.model ? ` · ${device.model}` : ''}
                </p>
                <p className="mt-2 text-xs text-dark-400">
                  Добавлено: {adminDate(device.imported_at)} · Последнее обновление:{' '}
                  {adminDate(device.last_seen_at)}
                </p>
              </article>
            ))}
          </>
        )}
        {tab === 'Рефералы' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">Приглашённые пользователи</h2>
            <p className="mt-2 text-sm text-dark-400">
              {data.referrals.invited_count} приглашённых · {data.referrals.paid_count} оплатили ·{' '}
              {data.referrals.earned_days} бонусных дней
            </p>
            {!(data.referrals.friends || []).length && <Empty>Рефералов пока нет.</Empty>}
            {data.referrals.friends.map((friend: Row) => (
              <Link
                key={friend.telegram_id}
                className="mt-4 flex flex-wrap justify-between gap-2 border-t border-dark-700 pt-4"
                to={`/admin/users/${friend.telegram_id}`}
              >
                <span className="text-accent-400">
                  {friend.first_name || friend.username || `ID ${friend.telegram_id}`}
                </span>
                <span className="text-sm text-dark-400">
                  {friend.has_paid ? 'Была покупка' : 'Пока без покупки'} · {friend.reward_days}{' '}
                  дней
                </span>
              </Link>
            ))}
          </>
        )}
        {tab === 'Ответы' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">Ответы на опросы</h2>
            {!replies.length && <Empty>Пользователь ещё не отвечал на опросы.</Empty>}
            {replies.map((reply, index) => {
              const parsed = parseAnswer(reply.answer);
              return (
                <article className="mt-4 border-t border-dark-700 pt-4" key={index}>
                  <p className="text-xs text-dark-400">
                    {surveyName(reply.event_key)} · {adminDate(reply.answered_at)}
                  </p>
                  <h3 className="mt-2 font-medium text-dark-100">{parsed.label}</h3>
                  {parsed.comment && (
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm text-dark-200">
                      {parsed.comment}
                    </p>
                  )}
                </article>
              );
            })}
          </>
        )}
        {tab === 'Поддержка' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">Обращения в поддержку</h2>
            {support === null ? (
              <Empty>Нет прав на просмотр поддержки.</Empty>
            ) : !support.length ? (
              <Empty>Пользователь ещё не писал в поддержку.</Empty>
            ) : (
              support.map((thread) => (
                <Link
                  className="mt-4 block rounded-lg border border-dark-700 p-4 hover:border-accent-400"
                  key={thread.id}
                  to={`/admin/tickets/${thread.id}`}
                >
                  <b className="text-accent-400">Открыть переписку →</b>
                  <p className="mt-2 text-sm text-dark-300">
                    {supportStatus[thread.status] || thread.status} · {thread.messages_count}{' '}
                    сообщений{thread.ai_handoff_reason ? ' · Нужен менеджер' : ''}
                  </p>
                  <p className="mt-1 text-xs text-dark-400">
                    Обновлено {adminDate(thread.updated_at)}
                  </p>
                </Link>
              ))
            )}
          </>
        )}
        {tab === 'История' && (
          <>
            <h2 className="text-lg font-semibold text-dark-100">История действий</h2>
            {!(data.timeline || []).length && <Empty>Событий пока нет.</Empty>}
            {data.timeline.map((event: Row, index: number) => (
              <article className="mt-4 border-t border-dark-700 pt-4" key={index}>
                <time className="text-xs text-dark-400">{adminDate(event.at)}</time>
                <h3 className="mt-1 font-medium text-dark-100">{event.title}</h3>
                <p className="mt-1 break-words text-sm text-dark-300">{event.detail}</p>
              </article>
            ))}
          </>
        )}
      </section>
    </main>
  );
}
