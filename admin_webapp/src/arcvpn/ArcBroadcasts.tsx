import { useCallback, useEffect, useRef, useState } from 'react';
import DOMPurify from 'dompurify';
import { Link } from 'react-router';

// Matches the existing ArcVPN JSON adapter boundary. Server validates payloads.
// biome-ignore lint/suspicious/noExplicitAny: heterogeneous adapter responses are narrowed by endpoint
type Row = Record<string, any>;
const initial = (): Row => ({
  title: '',
  message_text: '',
  photo_file_id: '',
  buttons: [],
  audience: { segment: 'all', tariff_id: 0, expiring_days: 7, selected: [], excluded: [] },
  reward: {
    kind: 'none',
    days: 3,
    discount_type: 'percent',
    discount_value: 20,
    duration_days: 7,
    max_uses: 100,
    code: '',
    promo_id: 0,
  },
});
const status: Row = {
  draft: 'Черновик',
  queued: 'В очереди',
  running: 'Отправляется',
  completed: 'Завершена',
  stopped: 'Остановлена',
};
const demoUsers = [
  { telegram_id: 700001, first_name: 'Алексей', username: 'alex' },
  { telegram_id: 700002, first_name: 'Марина', username: 'marina' },
  { telegram_id: 700003, first_name: 'Никита', username: 'north' },
];
let demoCampaigns: Row[] = [];
async function call(path: string, method = 'GET', body?: Row): Promise<Row> {
  if (import.meta.env.DEV) {
    if (path === '/options')
      return {
        tariffs: [{ id: 1, name: 'Стандарт' }],
        promocodes: [{ id: 1, code: 'START20' }],
        test_admins: [{ id: 1, label: 'Демо-администратор' }],
      };
    if (path.startsWith('/users')) return { users: demoUsers };
    if (path === '/preview')
      return {
        count: body?.audience.segment === 'selected' ? body.audience.selected.length : 243,
        without_subscription: 12,
        sample: demoUsers,
      };
    if (path === '' && method === 'GET') return { campaigns: demoCampaigns };
    const parts = path.split('/');
    const id = Number(parts[1]);
    const action = parts[2];
    if ((method === 'POST' && !path) || method === 'PUT') {
      if (!body?.title || !body.message_text) throw new Error('Введите название и сообщение');
      const old = demoCampaigns.find((c) => c.id === id);
      const campaign = {
        id: id || Date.now(),
        title: body.title,
        payload: structuredClone(body),
        revision: (old?.revision || 0) + 1,
        tested_revision: null,
        status: 'draft',
        total: body.audience.segment === 'selected' ? body.audience.selected.length : 243,
        counts: { pending: 243 },
        rewards: { pending: 243 },
        without_subscription: 12,
        errors: [],
      };
      demoCampaigns = [campaign, ...demoCampaigns.filter((c) => c.id !== campaign.id)];
      return { campaign };
    }
    const campaign = demoCampaigns.find((c) => c.id === id);
    if (!campaign) throw new Error('Черновик не найден');
    if (action === 'test') campaign.tested_revision = campaign.revision;
    if (action === 'start') campaign.status = 'queued';
    if (action === 'stop') campaign.status = 'stopped';
    return { campaign: { ...campaign } };
  }
  const response = await fetch(`/api/admin/broadcasts${path}`, {
    method,
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Не удалось выполнить действие');
  return data;
}

const field =
  'w-full min-w-0 rounded-xl border border-dark-700 bg-dark-900 px-3 py-2.5 text-sm text-dark-100 focus:outline-none focus:ring-2 focus:ring-accent-400 disabled:opacity-50';
const button =
  'rounded-xl border border-dark-700 px-4 py-2.5 text-sm font-medium text-dark-200 hover:bg-dark-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400 disabled:cursor-not-allowed disabled:opacity-40';
const primary = `${button} border-accent-500 bg-accent-500 text-white hover:bg-accent-600`;
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid min-w-0 gap-1.5 text-xs text-dark-300">
      <span>{label}</span>
      {children}
    </label>
  );
}

export default function ArcBroadcasts() {
  const [campaigns, setCampaigns] = useState<Row[]>([]);
  const [options, setOptions] = useState<Row>({ tariffs: [], promocodes: [], test_admins: [] });
  const [draft, setDraft] = useState<Row>(initial);
  const [current, setCurrent] = useState<Row | null>(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [preview, setPreview] = useState<Row | null>(null);
  const [admin, setAdmin] = useState(0);
  const [search, setSearch] = useState('');
  const [users, setUsers] = useState<Row[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [loading, setLoading] = useState(true);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const canEdit = !current || current.status === 'draft';
  const tested = Boolean(current && !dirty && current.tested_revision === current.revision);
  const patch = (values: Row) => {
    setDraft((d) => ({ ...d, ...values }));
    setDirty(true);
    setPreview(null);
    setConfirming(false);
    setNotice('');
  };
  const audience = (values: Row) => patch({ audience: { ...draft.audience, ...values } });
  const reward = (values: Row) => patch({ reward: { ...draft.reward, ...values } });

  const load = useCallback(async () => {
    const [list, choices] = await Promise.all([call(''), call('/options')]);
    setCampaigns(list.campaigns);
    setOptions(choices);
    setAdmin((value) => value || choices.test_admins[0]?.id || 0);
  }, []);
  useEffect(() => {
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [load]);
  const currentId = current?.id;
  const currentStatus = current?.status;
  useEffect(() => {
    if (!currentId || !['queued', 'running'].includes(currentStatus)) return;
    const interval = setInterval(() => {
      call(`/${currentId}`)
        .then((r) => {
          setCurrent(r.campaign);
          return load();
        })
        .catch((e) => setError(e.message));
    }, 4000);
    return () => clearInterval(interval);
  }, [currentId, currentStatus, load]);
  useEffect(() => {
    if (!editing) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      call(`/users?search=${encodeURIComponent(search)}`)
        .then((r) => {
          if (!cancelled) setUsers(r.users);
        })
        .catch((e) => {
          if (!cancelled) setError(e.message);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, editing]);

  async function action(name: string, operation: () => Promise<void>) {
    if (busy) return;
    setBusy(name);
    setError('');
    setNotice('');
    try {
      await operation();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Сервер недоступен');
    } finally {
      setBusy('');
    }
  }
  async function saveDraft() {
    const result = await call(current ? `/${current.id}` : '', current ? 'PUT' : 'POST', draft);
    setCurrent(result.campaign);
    setDirty(false);
    setDraft({
      ...initial(),
      ...result.campaign.payload,
      reward: { ...initial().reward, ...result.campaign.payload.reward },
    });
    await load();
    return result.campaign;
  }
  function open(c: Row) {
    setCurrent(c);
    setDraft({
      ...initial(),
      ...structuredClone(c.payload),
      reward: { ...initial().reward, ...c.payload.reward },
    });
    setEditing(true);
    setDirty(false);
    setPreview(null);
    setNotice('');
    setError('');
    setConfirming(false);
  }
  function format(tag: string) {
    const el = textRef.current;
    if (!el) return;
    const from = el.selectionStart;
    const to = el.selectionEnd;
    const selected = draft.message_text.slice(from, to) || 'текст';
    patch({
      message_text:
        draft.message_text.slice(0, from) +
        `<${tag}>${selected}</${tag}>` +
        draft.message_text.slice(to),
    });
    el.focus();
  }
  const previewMarkup = DOMPurify.sanitize(draft.message_text, {
    ALLOWED_TAGS: [
      'b',
      'strong',
      'i',
      'em',
      'u',
      's',
      'strike',
      'del',
      'code',
      'pre',
      'a',
      'blockquote',
      'tg-spoiler',
    ],
    ALLOWED_ATTR: ['href'],
  });

  return (
    <div className="mx-auto grid w-full max-w-6xl min-w-0 gap-5 pb-8">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link className="text-xs text-accent-400" to="/admin">
            ← Админ-панель
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-dark-50">Рассылки</h1>
          <p className="mt-1 text-sm text-dark-400">
            Сообщения, бонусные дни и предложения для выбранной аудитории.
          </p>
        </div>
        {!editing && (
          <button
            className={primary}
            onClick={() => {
              setDraft(initial());
              setCurrent(null);
              setEditing(true);
              setDirty(true);
              setError('');
            }}
          >
            Создать рассылку
          </button>
        )}
      </header>
      {import.meta.env.DEV && (
        <p className="rounded-xl border border-accent-400/30 p-3 text-sm text-accent-200">
          Демонстрация интерфейса. Сообщения не отправляются, бонусы не начисляются.
        </p>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-error-500/30 bg-error-500/10 p-3 text-sm text-error-300"
        >
          {error}
          <button className="ml-3 underline" onClick={() => action('reload', load)}>
            Обновить
          </button>
        </div>
      )}
      {notice && (
        <p role="status" className="rounded-xl bg-success-500/10 p-3 text-sm text-success-300">
          {notice}
        </p>
      )}
      {loading ? (
        <p role="status" className="py-10 text-dark-400">
          Загружаем рассылки…
        </p>
      ) : !editing ? (
        <>
          {!campaigns.length && (
            <div className="rounded-2xl border border-dashed border-dark-700 p-10 text-center">
              <h2 className="text-lg font-semibold">Рассылок пока нет</h2>
              <p className="mt-2 text-sm text-dark-400">
                Создайте черновик, выберите аудиторию и отправьте тест себе.
              </p>
            </div>
          )}
          <div className="grid gap-2">
            {campaigns.map((c) => (
              <button
                key={c.id}
                className={`${button} flex flex-wrap items-center justify-between gap-3 text-left`}
                onClick={() => open(c)}
              >
                <span className="min-w-0 break-words">
                  <b>{c.title}</b>
                  <small className="mt-1 block text-dark-400">
                    {c.total} получателей · доставлено {c.counts.sent || 0}
                  </small>
                </span>
                <span className="text-xs text-accent-300">{status[c.status]}</span>
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              className={button}
              disabled={Boolean(busy)}
              onClick={() => {
                if (dirty) setDiscarding(true);
                else {
                  setEditing(false);
                  setConfirming(false);
                }
              }}
            >
              ← Все рассылки
            </button>
            <span className="text-xs text-dark-400">
              {current ? status[current.status] : 'Новый черновик'}
              {dirty ? ' · есть несохранённые изменения' : ''}
            </span>
          </div>
          {discarding && (
            <div
              role="alert"
              className="flex flex-wrap items-center gap-3 rounded-xl border border-warning-500/40 p-3 text-sm"
            >
              <p>Несохранённые изменения будут потеряны.</p>
              <button
                className={button}
                onClick={() => {
                  setDiscarding(false);
                  setEditing(false);
                  setConfirming(false);
                }}
              >
                Вернуться без сохранения
              </button>
              <button className={button} onClick={() => setDiscarding(false)}>
                Продолжить редактирование
              </button>
            </div>
          )}
          <div className="grid min-w-0 items-start gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,1fr)]">
            <div className="grid min-w-0 gap-5">
              <section className="grid min-w-0 gap-4 rounded-2xl border border-dark-700 bg-dark-800/40 p-4 sm:p-5">
                <h2 className="font-semibold">1. Сообщение</h2>
                <Field label="Название для истории">
                  <input
                    className={field}
                    aria-label="Название для истории"
                    value={draft.title}
                    maxLength={100}
                    disabled={!canEdit || Boolean(busy)}
                    onChange={(e) => patch({ title: e.target.value })}
                    placeholder="Например, компенсация за сбой"
                  />
                </Field>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    ['b', 'Жирный'],
                    ['i', 'Курсив'],
                    ['u', 'Подчеркнуть'],
                    ['code', 'Код'],
                  ].map(([tag, label]) => (
                    <button
                      key={tag}
                      className={`${button} px-3 py-1.5 text-xs`}
                      disabled={!canEdit || Boolean(busy)}
                      onClick={() => format(tag)}
                    >
                      {label}
                    </button>
                  ))}
                  <button
                    className={`${button} px-3 py-1.5 text-xs`}
                    disabled={!canEdit || Boolean(busy)}
                    onClick={() =>
                      patch({
                        message_text: draft.message_text
                          .replaceAll('&', '&amp;')
                          .replaceAll('<', '&lt;')
                          .replaceAll('>', '&gt;'),
                      })
                    }
                  >
                    Экранировать весь текст
                  </button>
                </div>
                <Field label="Текст сообщения">
                  <textarea
                    ref={textRef}
                    aria-label="Текст сообщения"
                    className={`${field} min-h-44 resize-y`}
                    value={draft.message_text}
                    disabled={!canEdit || Boolean(busy)}
                    onChange={(e) => patch({ message_text: e.target.value })}
                    placeholder="Напишите сообщение. Enter — новая строка."
                  />
                </Field>
                <p className="text-xs leading-5 text-dark-400">
                  Форматирование кнопками добавляет поддерживаемые Telegram теги. Ссылки: &lt;a
                  href=&quot;https://…&quot;&gt;текст&lt;/a&gt;. Лимит:{' '}
                  {draft.photo_file_id ? '1024' : '4096'} символов с учётом бонуса. Проверка
                  выполняется сервером.
                </p>
                <Field label="Фото · JPEG, PNG, WebP до 5 МБ">
                  <input
                    className={field}
                    aria-label="Фотография"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    disabled={!canEdit || Boolean(busy) || import.meta.env.DEV}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      action('photo', async () => {
                        if (file.size > 5 * 1024 * 1024)
                          throw new Error('Фото должно быть меньше 5 МБ');
                        const data = new FormData();
                        data.append('photo', file);
                        const response = await fetch('/api/admin/broadcasts/photo', {
                          method: 'POST',
                          credentials: 'include',
                          body: data,
                        });
                        const result = await response.json();
                        if (!response.ok) throw new Error(result.error);
                        patch({ photo_file_id: result.file_id });
                        setNotice(
                          'Фото загружено в Telegram администратора. Теперь отправьте тест готового сообщения.',
                        );
                      });
                    }}
                  />
                </Field>
                {draft.photo_file_id && (
                  <div className="flex items-center justify-between gap-2 text-xs text-dark-300">
                    <span>Фото прикреплено</span>
                    <button
                      className={button}
                      disabled={!canEdit || Boolean(busy)}
                      onClick={() => patch({ photo_file_id: '' })}
                    >
                      Убрать
                    </button>
                  </div>
                )}
                <div className="grid gap-2">
                  <h3 className="text-sm">Кнопки под сообщением</h3>
                  {draft.buttons.map((b: Row, i: number) => (
                    <div key={i} className="grid gap-2 sm:grid-cols-[1fr_1.4fr_auto]">
                      <input
                        aria-label={`Текст кнопки ${i + 1}`}
                        className={field}
                        value={b.text}
                        placeholder="Открыть кабинет"
                        maxLength={40}
                        disabled={!canEdit || Boolean(busy)}
                        onChange={(e) =>
                          patch({
                            buttons: draft.buttons.map((v: Row, n: number) =>
                              n === i ? { ...v, text: e.target.value } : v,
                            ),
                          })
                        }
                      />
                      <input
                        aria-label={`Ссылка кнопки ${i + 1}`}
                        className={field}
                        value={b.url}
                        placeholder="https://…"
                        disabled={!canEdit || Boolean(busy)}
                        onChange={(e) =>
                          patch({
                            buttons: draft.buttons.map((v: Row, n: number) =>
                              n === i ? { ...v, url: e.target.value } : v,
                            ),
                          })
                        }
                      />
                      <button
                        aria-label={`Удалить кнопку ${i + 1}`}
                        className={button}
                        disabled={!canEdit || Boolean(busy)}
                        onClick={() =>
                          patch({ buttons: draft.buttons.filter((_: Row, n: number) => n !== i) })
                        }
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  {draft.buttons.length < 3 && (
                    <button
                      className={`${button} justify-self-start`}
                      disabled={!canEdit || Boolean(busy)}
                      onClick={() =>
                        patch({
                          buttons: [
                            ...draft.buttons,
                            { text: 'Открыть кабинет', url: 'https://arccnet.space/app/' },
                          ],
                        })
                      }
                    >
                      + Добавить кнопку
                    </button>
                  )}
                </div>
              </section>
              <section className="grid gap-4 rounded-2xl border border-dark-700 bg-dark-800/40 p-4 sm:p-5">
                <h2 className="font-semibold">2. Получатели</h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Группа пользователей">
                    <select
                      aria-label="Группа пользователей"
                      className={field}
                      value={draft.audience.segment}
                      disabled={!canEdit || Boolean(busy)}
                      onChange={(e) => audience({ segment: e.target.value })}
                    >
                      {[
                        ['all', 'Все пользователи Telegram'],
                        ['active', 'Активная подписка'],
                        ['expired', 'Подписка истекла'],
                        ['never_paid', 'Никогда не платили'],
                        ['expiring', 'Подписка скоро заканчивается'],
                        ['selected', 'Выбрать вручную'],
                      ].map(([v, name]) => (
                        <option value={v} key={v}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Дополнительно: тариф">
                    <select
                      aria-label="Тариф аудитории"
                      className={field}
                      value={draft.audience.tariff_id}
                      disabled={!canEdit || Boolean(busy)}
                      onChange={(e) => audience({ tariff_id: Number(e.target.value) })}
                    >
                      <option value={0}>Любой тариф</option>
                      {options.tariffs.map((t: Row) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {draft.audience.segment === 'expiring' && (
                    <Field label="Заканчивается в ближайшие, дней">
                      <input
                        aria-label="Срок окончания"
                        className={field}
                        type="number"
                        min={1}
                        max={365}
                        value={draft.audience.expiring_days}
                        disabled={!canEdit || Boolean(busy)}
                        onChange={(e) => audience({ expiring_days: Number(e.target.value) })}
                      />
                    </Field>
                  )}
                </div>
                <p className="text-xs text-dark-400">
                  Фильтры пересекаются. Забаненные и аккаунты без Telegram исключаются. После
                  сохранения список фиксируется.
                </p>
                {canEdit && (
                  <div className="flex flex-wrap gap-2">
                    {(['selected', 'excluded'] as const).flatMap((key) =>
                      draft.audience[key].map((id: number) => (
                        <button
                          key={`${key}-${id}`}
                          className={`${button} px-2 py-1 text-xs`}
                          disabled={Boolean(busy)}
                          aria-label={`Убрать ${id} из ${key === 'selected' ? 'выбранных' : 'исключений'}`}
                          onClick={() =>
                            audience({
                              [key]: draft.audience[key].filter((value: number) => value !== id),
                            })
                          }
                        >
                          {key === 'selected' ? 'Выбран' : 'Исключён'} ·{' '}
                          {users.find((u) => u.telegram_id === id)?.first_name || id} ×
                        </button>
                      )),
                    )}
                  </div>
                )}
                <Field label="Поиск для выбора или исключения">
                  <input
                    aria-label="Поиск получателей"
                    className={field}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Имя, username или Telegram ID"
                    disabled={!canEdit}
                  />
                </Field>
                <div className="max-h-52 overflow-y-auto rounded-xl border border-dark-700">
                  {users.map((u) => (
                    <div
                      key={u.telegram_id}
                      className="flex flex-wrap items-center gap-2 border-b border-dark-700 p-2 last:border-0"
                    >
                      <span className="min-w-0 flex-1 break-words text-xs">
                        {u.first_name || u.username || u.telegram_id}
                        {u.username ? ` · @${u.username}` : ''}
                      </span>
                      {draft.audience.segment === 'selected' && (
                        <label className="flex items-center gap-1 text-xs">
                          <input
                            type="checkbox"
                            disabled={!canEdit || Boolean(busy)}
                            checked={draft.audience.selected.includes(u.telegram_id)}
                            onChange={(e) =>
                              audience({
                                selected: e.target.checked
                                  ? [...draft.audience.selected, u.telegram_id]
                                  : draft.audience.selected.filter(
                                      (v: number) => v !== u.telegram_id,
                                    ),
                              })
                            }
                          />
                          Выбрать
                        </label>
                      )}
                      <label className="flex items-center gap-1 text-xs text-dark-400">
                        <input
                          type="checkbox"
                          disabled={!canEdit || Boolean(busy)}
                          checked={draft.audience.excluded.includes(u.telegram_id)}
                          onChange={(e) =>
                            audience({
                              excluded: e.target.checked
                                ? [...draft.audience.excluded, u.telegram_id]
                                : draft.audience.excluded.filter(
                                    (v: number) => v !== u.telegram_id,
                                  ),
                            })
                          }
                        />
                        Исключить
                      </label>
                    </div>
                  ))}
                  {!users.length && (
                    <p className="p-3 text-xs text-dark-400">Пользователи не найдены</p>
                  )}
                </div>
                <p className="text-xs text-dark-400">
                  Выбрано вручную: {draft.audience.selected.length} · исключено:{' '}
                  {draft.audience.excluded.length}
                </p>
                <button
                  className={`${button} justify-self-start`}
                  disabled={Boolean(busy) || !canEdit}
                  onClick={() =>
                    action('preview', async () => setPreview(await call('/preview', 'POST', draft)))
                  }
                >
                  Проверить аудиторию и текст
                </button>
                {preview && (
                  <p role="status" className="text-sm text-accent-300">
                    Получателей: {preview.count}. Без подписки: {preview.without_subscription}.
                  </p>
                )}
              </section>
              <section className="grid gap-4 rounded-2xl border border-dark-700 bg-dark-800/40 p-4 sm:p-5">
                <h2 className="font-semibold">3. Бонус или скидка</h2>
                <Field label="Тип предложения">
                  <select
                    aria-label="Тип предложения"
                    className={field}
                    value={draft.reward.kind}
                    disabled={!canEdit || Boolean(busy)}
                    onChange={(e) => reward({ kind: e.target.value })}
                  >
                    {[
                      ['none', 'Только сообщение'],
                      ['days', 'Начислить дни подписки'],
                      ['existing_promo', 'Отправить существующий промокод'],
                      ['new_promo', 'Создать общий промокод'],
                      ['personal_discount', 'Персональная скидка на одну покупку'],
                    ].map(([v, name]) => (
                      <option value={v} key={v}>
                        {name}
                      </option>
                    ))}
                  </select>
                </Field>
                {draft.reward.kind === 'days' && (
                  <>
                    <Field label="Подарочные дни">
                      <input
                        aria-label="Подарочные дни"
                        className={field}
                        type="number"
                        min={1}
                        max={365}
                        value={draft.reward.days}
                        disabled={!canEdit || Boolean(busy)}
                        onChange={(e) => reward({ days: Number(e.target.value) })}
                      />
                    </Field>
                    <p className="text-xs leading-5 text-dark-400">
                      Продлеваем одну основную подписку. Истёкшую — от текущей даты. Тариф и лимиты
                      сохраняются. Без подписки отправим вариант сообщения без обещания начисления.
                    </p>
                  </>
                )}
                {draft.reward.kind === 'existing_promo' && (
                  <Field label="Промокод">
                    <select
                      aria-label="Существующий промокод"
                      className={field}
                      value={draft.reward.promo_id}
                      disabled={!canEdit || Boolean(busy)}
                      onChange={(e) => reward({ promo_id: Number(e.target.value) })}
                    >
                      <option value={0}>Выберите промокод</option>
                      {options.promocodes.map((p: Row) => (
                        <option value={p.id} key={p.id}>
                          {p.code}
                        </option>
                      ))}
                    </select>
                  </Field>
                )}
                {['new_promo', 'personal_discount'].includes(draft.reward.kind) && (
                  <>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {draft.reward.kind === 'new_promo' && (
                        <Field label="Общий код">
                          <input
                            aria-label="Общий код"
                            className={field}
                            value={draft.reward.code}
                            maxLength={32}
                            disabled={!canEdit || Boolean(busy)}
                            onChange={(e) => reward({ code: e.target.value.toUpperCase() })}
                          />
                        </Field>
                      )}
                      <Field label="Тип скидки">
                        <select
                          aria-label="Тип скидки"
                          className={field}
                          value={draft.reward.discount_type}
                          disabled={!canEdit || Boolean(busy)}
                          onChange={(e) => reward({ discount_type: e.target.value })}
                        >
                          <option value="percent">Проценты</option>
                          <option value="fixed">Рубли</option>
                        </select>
                      </Field>
                      <Field
                        label={draft.reward.discount_type === 'percent' ? 'Скидка, %' : 'Скидка, ₽'}
                      >
                        <input
                          aria-label="Размер скидки"
                          className={field}
                          type="number"
                          min={1}
                          max={draft.reward.discount_type === 'percent' ? 100 : 1000000}
                          value={draft.reward.discount_value}
                          disabled={!canEdit || Boolean(busy)}
                          onChange={(e) => reward({ discount_value: Number(e.target.value) })}
                        />
                      </Field>
                      <Field label="Действует после запуска, дней">
                        <input
                          aria-label="Срок скидки"
                          className={field}
                          type="number"
                          min={1}
                          max={3650}
                          value={draft.reward.duration_days}
                          disabled={!canEdit || Boolean(busy)}
                          onChange={(e) => reward({ duration_days: Number(e.target.value) })}
                        />
                      </Field>
                      {draft.reward.kind === 'new_promo' && (
                        <Field label="Всего использований">
                          <input
                            aria-label="Лимит использований"
                            className={field}
                            type="number"
                            min={1}
                            value={draft.reward.max_uses}
                            disabled={!canEdit || Boolean(busy)}
                            onChange={(e) => reward({ max_uses: Number(e.target.value) })}
                          />
                        </Field>
                      )}
                    </div>
                    <p className="text-xs leading-5 text-dark-400">
                      {draft.reward.kind === 'personal_discount'
                        ? 'Каждый получатель получит свой код: только для его аккаунта и на одну покупку.'
                        : 'Общий код можно переслать другим пользователям. Каждый аккаунт использует его один раз.'}{' '}
                      Промокоды активируются при реальном запуске.
                    </p>
                  </>
                )}
              </section>
            </div>
            <div className="grid min-w-0 gap-4 lg:sticky lg:top-20">
              <section className="min-w-0 rounded-2xl border border-dark-700 p-4 sm:p-5">
                <h2 className="mb-3 text-sm font-semibold">Предпросмотр сообщения</h2>
                <div className="rounded-xl bg-dark-800 p-4 text-sm leading-6">
                  <div className="mb-2 text-xs font-semibold text-accent-300">ArcVPN</div>
                  {draft.photo_file_id && (
                    <div className="mb-3 rounded-lg border border-dark-600 p-5 text-center text-xs text-dark-400">
                      Прикреплённое фото · смотрите в Telegram-тесте
                    </div>
                  )}
                  <div
                    className="whitespace-pre-wrap break-words [&_a]:text-accent-300 [&_a]:underline [&_code]:rounded [&_code]:bg-dark-700 [&_code]:px-1 [&_pre]:overflow-x-auto [&_pre]:whitespace-pre-wrap"
                    // biome-ignore lint/security/noDangerouslySetInnerHtml: sanitized by DOMPurify with a strict tag/attribute allowlist
                    dangerouslySetInnerHTML={{
                      __html: previewMarkup || 'Здесь появится ваше сообщение',
                    }}
                  />
                  {draft.reward.kind === 'days' && (
                    <p className="mt-4">
                      🎁 Вам начислено <b>+{draft.reward.days} дн.</b> подписки.
                    </p>
                  )}
                  {['existing_promo', 'new_promo', 'personal_discount'].includes(
                    draft.reward.kind,
                  ) && (
                    <p className="mt-4">
                      🎟 Промокод:{' '}
                      <code>
                        {draft.reward.kind === 'personal_discount'
                          ? 'индивидуальный код получателя'
                          : draft.reward.kind === 'new_promo'
                            ? draft.reward.code || 'CODE'
                            : options.promocodes.find((p: Row) => p.id === draft.reward.promo_id)
                                ?.code || 'Выберите код'}
                      </code>
                    </p>
                  )}
                  {draft.buttons.map((b: Row, i: number) => (
                    <div
                      key={i}
                      className="mt-2 rounded-lg border border-dark-600 py-1.5 text-center text-xs text-accent-300"
                    >
                      {b.text || 'Кнопка'}
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs leading-5 text-dark-400">
                  Это предварительный вид. Точный результат форматирования и бонуса проверяется
                  тестом в Telegram.
                </p>
              </section>
              <section className="grid gap-3 rounded-2xl border border-accent-500/25 bg-dark-800/40 p-4 sm:p-5">
                <h2 className="font-semibold">4. Тест и запуск</h2>
                <p className="text-xs leading-5 text-dark-400">
                  Тест приходит только администратору. Дни и скидки при тесте не активируются.
                </p>
                {canEdit && (
                  <>
                    <button
                      className={button}
                      disabled={Boolean(busy) || !draft.title || !draft.message_text}
                      onClick={() =>
                        action('save', async () => {
                          await saveDraft();
                          setNotice('Черновик сохранён. Отправьте тест себе.');
                        })
                      }
                    >
                      {busy === 'save' ? 'Сохраняем…' : 'Сохранить черновик'}
                    </button>
                    <Field label="Получатель теста">
                      <select
                        aria-label="Получатель теста"
                        className={field}
                        value={admin}
                        disabled={Boolean(busy)}
                        onChange={(e) => setAdmin(Number(e.target.value))}
                      >
                        {options.test_admins.map((a: Row) => (
                          <option value={a.id} key={a.id}>
                            {a.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <button
                      className={primary}
                      disabled={Boolean(busy) || !admin || !draft.title || !draft.message_text}
                      onClick={() =>
                        action('test', async () => {
                          const saved = dirty || !current ? await saveDraft() : current;
                          const r = await call(`/${saved.id}/test`, 'POST', { admin_id: admin });
                          setCurrent(r.campaign);
                          await load();
                          setNotice(
                            import.meta.env.DEV
                              ? 'Демонстрация: тест отмечен. Реального сообщения нет.'
                              : 'Тест отправлен вам в Telegram. Проверьте его перед запуском.',
                          );
                        })
                      }
                    >
                      {busy === 'test' ? 'Отправляем тест…' : 'Отправить тест мне'}
                    </button>
                    <p className={`text-xs ${tested ? 'text-success-300' : 'text-dark-400'}`}>
                      {tested
                        ? 'Тест текущей версии отправлен. Можно подтвердить запуск.'
                        : 'Для запуска нужен успешный тест текущей версии.'}
                    </p>
                    {current && (
                      <p className="text-sm">
                        Зафиксировано получателей: <b>{current.total}</b>
                        <span className="mt-1 block text-xs text-dark-400">
                          Без подписки: {current.without_subscription}
                        </span>
                      </p>
                    )}
                    {!confirming ? (
                      <button
                        className={button}
                        disabled={Boolean(busy) || !tested || !current?.total}
                        onClick={() => setConfirming(true)}
                      >
                        Отправить {current?.total || 0} пользователям
                      </button>
                    ) : (
                      <div className="grid gap-2 rounded-xl border border-warning-500/40 p-3">
                        <p className="text-sm">
                          Вы проверили сообщение в Telegram и подтверждаете отправку{' '}
                          {current?.total} пользователям
                          {draft.reward.kind === 'days'
                            ? ` с начислением +${draft.reward.days} дней`
                            : ''}
                          ?
                        </p>
                        <button
                          className={primary}
                          disabled={Boolean(busy)}
                          onClick={() =>
                            action('start', async () => {
                              if (!current) return;
                              const r = await call(`/${current.id}/start`, 'POST', {
                                revision: current.revision,
                                count: current.total,
                              });
                              setCurrent(r.campaign);
                              setConfirming(false);
                              await load();
                              setNotice('Рассылка поставлена в очередь. Результаты появятся ниже.');
                            })
                          }
                        >
                          Да, начать рассылку
                        </button>
                        <button
                          className={button}
                          disabled={Boolean(busy)}
                          onClick={() => setConfirming(false)}
                        >
                          Отмена
                        </button>
                      </div>
                    )}
                  </>
                )}
                {current && current.status !== 'draft' && (
                  <>
                    <p className="text-lg font-semibold">{status[current.status]}</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {[
                        ['Доставлено', current.counts.sent || 0],
                        ['Ожидают', current.counts.pending || 0],
                        ['Недоступны', current.counts.blocked || 0],
                        ['Ошибки', current.counts.failed || 0],
                        ['Не подтверждено', current.counts.uncertain || 0],
                        ['Бонус применён', current.rewards.applied || 0],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-lg bg-dark-900 p-3">
                          <span className="block text-xs text-dark-400">{label}</span>
                          <b>{value}</b>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs text-dark-400">
                      Дни ожидают синхронизации: {current.rewards.sync_pending || 0}. Без подписки:{' '}
                      {current.rewards.no_subscription || 0}.
                    </p>
                    {['queued', 'running'].includes(current.status) && (
                      <button
                        className={button}
                        disabled={Boolean(busy)}
                        onClick={() =>
                          action('stop', async () => {
                            const r = await call(`/${current.id}/stop`, 'POST', {});
                            setCurrent(r.campaign);
                            await load();
                            setNotice(
                              'Остановлено. Уже выполненные отправки и начисления сохранены.',
                            );
                          })
                        }
                      >
                        Остановить оставшиеся отправки
                      </button>
                    )}
                    {current.errors?.map((e: Row, i: number) => (
                      <p key={i} className="text-xs text-warning-300">
                        {e.count} · {e.error}
                      </p>
                    ))}
                    <button
                      className={button}
                      disabled={Boolean(busy)}
                      onClick={() =>
                        action('refresh', async () => {
                          setCurrent((await call(`/${current.id}`)).campaign);
                          await load();
                        })
                      }
                    >
                      Обновить результаты
                    </button>
                  </>
                )}
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
