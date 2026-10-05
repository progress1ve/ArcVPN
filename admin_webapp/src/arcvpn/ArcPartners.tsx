import { useEffect, useState, type FormEvent } from 'react';
import { AdminBackButton } from '@/components/admin';

type Row = Record<string, any>;
const money = (value: number) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format((value || 0) / 100);
const stamp = (value: string) => value ? new Date(value.includes('T') ? value : value.replace(' ', 'T') + 'Z').toLocaleString('ru-RU') : '—';
const labels: Row = { accrual: 'Начисление', adjustment: 'Корректировка', refund: 'Возврат', payout: 'Ручная выплата', reversal: 'Отмена', new: 'Покупка', renew: 'Продление', upgrade: 'Смена тарифа', addon_lte: 'Трафик', addon_device: 'Устройства', addon_combined: 'Устройства и трафик' };
const actions: Row = { 'partner.create':'Создан партнёр', 'partner.update':'Изменены условия / доступ', 'client.bind':'Закреплён клиент', 'source.assign':'Назначена ссылка', 'source.disable':'Отключено назначение', 'ledger.payout':'Записана выплата', 'ledger.adjustment':'Записана корректировка', 'ledger.reversal':'Отменена запись' };
function historyText(row: Row) {
  const p = row.payload;
  if (row.action === 'partner.update') {
    const changes = [];
    if (p.before.rate_bps !== p.after.rate_bps) changes.push(`Ставка будущих клиентов: ${p.before.rate_bps / 100}% → ${p.after.rate_bps / 100}%`);
    if (p.before.access_enabled !== p.after.access_enabled) changes.push(p.after.access_enabled ? 'Доступ предоставлен' : 'Доступ отозван');
    if (p.before.recruiting_enabled !== p.after.recruiting_enabled) changes.push(p.after.recruiting_enabled ? 'Привлечение возобновлено' : 'Привлечение остановлено');
    if (p.before.name !== p.after.name) changes.push(`Название: ${p.before.name} → ${p.after.name}`);
    if (p.password_reset) changes.push('Пароль изменён; сессии завершены');
    return changes.join(' · ') || 'Сохранены параметры';
  }
  if (row.action === 'client.bind') return `Клиент #${p.user_id} · ссылка #${p.source_id} · ${p.rate_bps / 100}% · ${p.binding_kind === 'new' ? 'новый клиент' : 'подтверждённый список'}`;
  if (row.action === 'partner.create') return `Начальная ставка ${p.rate_bps / 100}%`;
  if (row.action.startsWith('source.')) return `Ссылка #${p.source_id}`;
  return `Запись #${p.entry_id} · ${money(p.amount_cents)}${p.related_id ? ' · исходная запись #' + p.related_id : ''}`;
}
const errors: Row = { insufficient_balance: 'Сумма превышает доступный остаток.', operation_conflict: 'Этот ключ операции уже использован с другими данными.', source_already_assigned: 'Ссылка уже назначена другому партнёру.', preview_changed: 'Список изменился. Подготовьте новый предварительный список.', invalid_preview: 'Предварительный список истёк. Подготовьте новый.', password_min_12: 'Пароль должен содержать от 12 до 256 символов.', record_conflict: 'Логин или операция уже существует.', forbidden: 'Управление партнёрами доступно владельцу.', refund_exceeds_purchase: 'Возврат превышает сумму покупки.', reversal_not_allowed: 'Эту запись нельзя отменить.', invalid_amount: 'Укажите корректную положительную сумму.' };
async function api(path = '', body?: Row, method = 'POST') {
  const response = await fetch('/api/admin/partners' + path, {
    credentials: 'include', cache: 'no-store',
    ...(body !== undefined ? { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(errors[value.error] || 'Не удалось выполнить операцию. Проверьте данные и повторите.');
  return value;
}
const field = 'w-full rounded-xl border border-dark-700 bg-dark-800 px-3 py-2.5 text-sm text-dark-100 outline-none focus:border-accent-500';
const button = 'rounded-xl bg-accent-500 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50';
const quiet = 'rounded-xl border border-dark-700 bg-dark-800 px-3 py-2 text-sm text-dark-200 disabled:opacity-50';
const box = 'rounded-2xl border border-dark-700 bg-dark-900 p-5';
Object.assign(errors, {
  negative_balance_confirmation_required: 'Корректировка создаст задолженность. Подтвердите её флажком в форме.',
  already_reversed: 'Эта запись уже отменена.',
  entry_not_found: 'Запись журнала этого партнёра не найдена.',
  invalid_rate: 'Ставка должна быть от 0 до 100%, максимум два знака после запятой.',
  invalid_date: 'Укажите дату не позднее сегодняшней.',
  note_required: 'Укажите примечание или подтверждение.',
  method_required: 'Укажите способ ручного перевода.',
});
function operationKey(partnerId: number | null, fresh = false) {
  if (partnerId === null) return crypto.randomUUID();
  const name = 'arcvpn-partner-operation-' + partnerId;
  try {
    const key = fresh ? crypto.randomUUID() : sessionStorage.getItem(name) || crypto.randomUUID();
    sessionStorage.setItem(name, key);
    return key;
  } catch { return crypto.randomUUID(); }
}

export default function ArcPartners() {
  const [list, setList] = useState<Row | null>(null);
  const [id, setId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Row | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState({ name: '', login: '', password: '' });
  const [rate, setRate] = useState('30');
  const [password, setPassword] = useState('');
  const [selection, setSelection] = useState('');
  const [preview, setPreview] = useState<Row | null>(null);
  const [tab, setTab] = useState('purchases');
  const [filters, setFilters] = useState({ source: '', from: '', to: '', page:'1' });
  const [entry, setEntry] = useState({ kind: 'payout', amount: '', occurred_on: new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Moscow' }).format(new Date()), method: '', note: '', related_id: '' });
  const [key, setKey] = useState<string>(() => crypto.randomUUID());
  const [acceptNegative, setAcceptNegative] = useState(false);

  async function load(nextId = id, selectedFilters = filters) {
    const result = await api();
    setList(result);
    if (nextId !== null) {
      const report = await api('/' + nextId + '?' + new URLSearchParams(selectedFilters));
      setDetail(report);
      setRate(String(report.partner.rate_bps / 100));
    }
  }
  useEffect(() => { load().catch(e => setError(e.message)).finally(() => setLoading(false)); }, []);
  async function run(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка'); }
    finally { setBusy(false); }
  }
  const choose = (next: number) => run(async () => {
    const clean = { source:'', from:'', to:'', page:'1' };
    setId(next); setDetail(null); setPreview(null); setSelection(''); setFilters(clean); setKey(operationKey(next));
    await load(next, clean);
  });
  function changeTab(next: string) {
    run(async () => { const nextFilters = { ...filters, page:'1' }; setTab(next); setFilters(nextFilters); await load(id, nextFilters); });
  }
  function turnPage(delta: number) {
    run(async () => { const nextFilters = { ...filters, page:String((detail?.page || 1) + delta) }; setFilters(nextFilters); await load(id, nextFilters); });
  }
  const patch = (body: Row) => run(async () => { await api('/' + id, body, 'PATCH'); setPassword(''); await load(); setNotice('Сохранено. Условия закреплённых клиентов сохранены.'); });
  const sources: Row[] = list ? [
    ...list.sources.campaigns.map((s: Row) => ({ value: 'campaign:' + s.id, label: `Реклама: ${s.name} (${s.code})`, kind: 'campaign', id: s.id })),
    ...list.sources.referrals.map((s: Row) => ({ value: 'referral:' + s.id, label: `Реферальная: ${s.username || s.first_name || 'клиент ' + s.id} (${s.referral_code})`, kind: 'referral', id: s.id })),
  ].filter(s => !list.sources.assigned.some((a: Row) => a.kind === s.kind && a.target_id === s.id)) : [];
  const formEntry = (event: FormEvent) => {
    event.preventDefault();
    run(async () => {
      // Decimal input becomes an integer kopek value; all accounting is server-side.
      const raw = entry.amount.replace(',', '.');
      if (entry.kind !== 'reversal' && !/^-?\d+(\.\d{1,2})?$/.test(raw)) throw new Error('Сумма: рубли, максимум два знака после запятой.');
      const [whole, fraction = ''] = raw.replace('-', '').split('.');
      const cents = (Number(whole) * 100 + Number(fraction.padEnd(2, '0'))) * (raw.startsWith('-') ? -1 : 1);
      if (entry.kind !== 'reversal' && !Number.isSafeInteger(cents)) throw new Error('Слишком большая сумма.');
      await api('/' + id + '/ledger', { kind: entry.kind, amount_cents: cents, occurred_on: entry.occurred_on,
        method: entry.method, note: entry.note, related_id: entry.related_id ? Number(entry.related_id) : null,
        operation_key: key, accept_negative: acceptNegative });
      setKey(operationKey(id, true)); setAcceptNegative(false); setEntry({ ...entry, amount: '', note: '', related_id: '' }); await load();
      setNotice('Операция сохранена в журнале. Денежный перевод выполняется вами вручную.');
    });
  };

  return <div className="space-y-6">
    <AdminBackButton />
    <div><p className="text-xs uppercase tracking-wider text-accent-400">ArcVPN</p><h1 className="mt-1 text-2xl font-bold text-dark-50">Партнёры</h1><p className="mt-2 text-sm text-dark-400">Закрепление клиентов, денежный журнал и ручные выплаты.</p></div>
    {error && <div role="alert" className="rounded-xl border border-error-500/30 bg-error-500/10 p-4 text-sm text-error-400">{error}</div>}
    {notice && <p role="status" className="text-sm text-accent-300">{notice}</p>}
    {loading ? <p className="text-dark-400">Загрузка…</p> : <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="space-y-4">
        <section className={box}><h2 className="mb-3 font-semibold">Партнёры</h2>
          {list?.partners.map((p: Row) => <button key={p.id} disabled={busy} onClick={() => choose(p.id)} className={`mb-2 w-full rounded-xl border p-3 text-left text-sm ${id === p.id ? 'border-accent-500 bg-accent-500/10' : 'border-dark-700 bg-dark-800'}`}><b className="block">{p.name}</b><span className="text-xs text-dark-400">{p.login} · {p.access_enabled ? 'Доступ открыт' : 'Доступ отозван'}</span></button>)}
          {!list?.partners.length && <p className="text-sm text-dark-400">Партнёров пока нет.</p>}
        </section>
        <form className={box + ' space-y-3'} onSubmit={e => { e.preventDefault(); run(async () => { const r = await api('', account); setAccount({ name: '', login: '', password: '' }); setId(r.partner.id); const clean = { source:'', from:'', to:'', page:'1' }; setFilters(clean); setKey(operationKey(r.partner.id)); await load(r.partner.id, clean); }); }}>
          <h2 className="font-semibold">Создать партнёра</h2>
          <label className="block text-xs text-dark-400">Название<input className={field + ' mt-1'} value={account.name} maxLength={100} required onChange={e => setAccount({ ...account, name: e.target.value })} /></label>
          <label className="block text-xs text-dark-400">Логин<input className={field + ' mt-1'} value={account.login} pattern="[a-zA-Z0-9_.-]{3,64}" autoComplete="off" required onChange={e => setAccount({ ...account, login: e.target.value })} /></label>
          <label className="block text-xs text-dark-400">Пароль · минимум 12 символов<input className={field + ' mt-1'} type="password" value={account.password} minLength={12} maxLength={256} autoComplete="new-password" required onChange={e => setAccount({ ...account, password: e.target.value })} /></label>
          <button className={button + ' w-full'} disabled={busy}>Создать</button>
          <a className="block break-all text-xs text-accent-300" href="https://partners.arccnet.space" target="_blank" rel="noreferrer">partners.arccnet.space</a>
        </form>
      </aside>
      <div className="min-w-0 space-y-5">{detail ? <>
        <section className={box}>
          <h2 className="text-xl font-semibold">{detail.partner.name}</h2>
          <div className="my-4 flex flex-wrap gap-2">
            <button className={quiet} disabled={busy} onClick={() => patch({ access_enabled: !detail.partner.access_enabled })}>{detail.partner.access_enabled ? 'Отозвать доступ' : 'Предоставить доступ'}</button>
            <button className={quiet} disabled={busy} onClick={() => patch({ recruiting_enabled: !detail.partner.recruiting_enabled })}>{detail.partner.recruiting_enabled ? 'Остановить привлечение' : 'Возобновить привлечение'}</button>
          </div>
          <p className="mb-4 text-xs text-dark-400">Остановка привлечения и отзыв доступа сохраняют клиентов, их ставки и задолженность.</p>
          <form className="flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); const [whole, fraction = ''] = rate.split('.'); const value = /^\d+(\.\d{1,2})?$/.test(rate) ? Number(whole) * 100 + Number(fraction.padEnd(2, '0')) : NaN; if (Number.isInteger(value)) patch({ rate_bps: value }); else setError('Ставка: максимум два знака после запятой.'); }}>
            <label className="text-xs text-dark-400">Ставка для будущих клиентов, %<input className={field + ' mt-1'} type="number" min="0" max="100" step="0.01" value={rate} required onChange={e => setRate(e.target.value)} /></label><button className={quiet} disabled={busy}>Назначить ставку</button>
          </form>
          <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); patch({ password }); }}>
            <label className="text-xs text-dark-400">Новый пароль<input className={field + ' mt-1'} type="password" autoComplete="new-password" minLength={12} maxLength={256} value={password} required onChange={e => setPassword(e.target.value)} /></label><button className={quiet} disabled={busy}>Сменить пароль и завершить сессии</button>
          </form>
        </section>
        <section className={box}><h2 className="mb-4 font-semibold">Назначенные ссылки</h2>
          {detail.sources.map((s: Row) => <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-dark-700 py-3"><div className="min-w-0"><b className="text-sm">{s.name}</b><a className="block break-all text-xs text-accent-300" href={s.url} target="_blank" rel="noreferrer">{s.url}</a><span className="text-xs text-dark-400">{s.active ? 'Назначена' : 'Назначение отключено'} · {s.enabled ? 'Ссылка активна' : 'Ссылка отключена'}</span></div>{s.active && <div className="flex flex-wrap gap-2"><button className={quiet} disabled={busy} onClick={() => run(async () => { setPreview(null); setPreview(await api('/' + id + '/import-preview', { source_id: s.id })); })}>Список существующих клиентов</button><button className={quiet} disabled={busy} onClick={() => run(async () => { await api('/' + id + '/sources/' + s.id, {}, 'DELETE'); setPreview(null); await load(); })}>Отключить назначение</button></div>}</div>)}
          <form className="mt-4 flex flex-wrap gap-3" onSubmit={e => { e.preventDefault(); run(async () => { const [kind, target] = selection.split(':'); await api('/' + id + '/sources', { kind, target_id: Number(target) }); setSelection(''); await load(); }); }}>
            <select aria-label="Ссылка для назначения" className={field + ' flex-1'} value={selection} required onChange={e => setSelection(e.target.value)}><option value="">Выберите существующую ссылку</option>{sources.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}</select><button className={button} disabled={busy || !selection}>Назначить</button>
          </form><p className="mt-3 text-xs text-dark-400">Назначение ссылки привязывает только новых клиентов. Старые клиенты — после подтверждения списка, без начислений за прошлые покупки.</p>
          {preview && <div className="mt-4 rounded-xl border border-accent-500/40 p-4"><h3 className="font-semibold">Предварительный список · {preview.clients.length} клиентов · ставка {preview.rate_bps / 100}%</h3><p className="my-2 text-xs text-dark-400">Проверьте каждую строку. Подтверждение закрепит клиентов для будущих покупок.</p><div className="max-h-64 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>ID</th><th>Имя</th><th>Username</th></tr></thead><tbody>{preview.clients.map((c: Row) => <tr key={c.id}><td className="p-2">{c.id}</td><td>{c.first_name || '—'}</td><td>{c.username || '—'}</td></tr>)}</tbody></table></div><button className={button + ' mt-3'} disabled={busy || !preview.clients.length} onClick={() => run(async () => { await api('/' + id + '/import-confirm', { token: preview.token, confirmed: true }); setPreview(null); await load(); })}>Подтверждаю перенос всего списка</button><button className={quiet + ' ml-2'} onClick={() => setPreview(null)}>Отмена</button></div>}
        </section>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[['Начислено', detail.balance.accrued], ['Корректировки', detail.balance.adjustments], ['Выплачено', detail.balance.paid], ['Доступно', detail.balance.available]].map(([name, value]) => <div className={box} key={name}><p className="text-xs text-dark-400">{name}</p><b className="mt-2 block text-xl">{money(value)}</b></div>)}</div>
        {detail.balance.debt > 0 && <p className="text-sm text-error-400">Отрицательный остаток: {money(detail.balance.debt)}. Учитывается в будущих начислениях.</p>}
        <form className={box + ' space-y-3'} onSubmit={formEntry}>
          <h2 className="font-semibold">Записать операцию</h2><p className="text-xs text-dark-400">Выплата — запись уже выполненного вами перевода. Автоматических переводов нет. Примечание видно партнёру.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-dark-400">Операция<select className={field + ' mt-1'} value={entry.kind} onChange={e => { setEntry({ ...entry, kind: e.target.value }); setKey(operationKey(id, true)); setAcceptNegative(false); }}>{[['payout', 'Ручная выплата'], ['adjustment', 'Корректировка (+ / −)'], ['reversal', 'Отмена записи']].map(([v, l]) => <option value={v} key={v}>{l}</option>)}</select></label>
            {entry.kind !== 'reversal' && <label className="text-xs text-dark-400">{entry.kind === 'refund' ? 'Возвращено покупателю, ₽' : 'Сумма, ₽'}<input className={field + ' mt-1'} inputMode="decimal" value={entry.amount} required onChange={e => setEntry({ ...entry, amount: e.target.value })} /></label>}
            {['refund', 'reversal', 'adjustment'].includes(entry.kind) && <label className="text-xs text-dark-400">ID записи журнала {entry.kind === 'adjustment' ? '(необязательно)' : ''}<input className={field + ' mt-1'} type="number" min="1" value={entry.related_id} required={entry.kind !== 'adjustment'} onChange={e => setEntry({ ...entry, related_id: e.target.value })} /></label>}
            <label className="text-xs text-dark-400">Дата<input className={field + ' mt-1'} type="date" value={entry.occurred_on} required onChange={e => setEntry({ ...entry, occurred_on: e.target.value })} /></label>
            {entry.kind === 'payout' && <label className="text-xs text-dark-400">Способ перевода<input className={field + ' mt-1'} value={entry.method} maxLength={100} required onChange={e => setEntry({ ...entry, method: e.target.value })} /></label>}
          </div>
          <label className="block text-xs text-dark-400">Примечание / подтверждение (без реквизитов и секретов)<textarea className={field + ' mt-1'} value={entry.note} maxLength={1000} required onChange={e => setEntry({ ...entry, note: e.target.value })} /></label>
          {entry.kind !== 'payout' && <><p className="text-xs text-dark-400">Для полного или частичного возврата укажите отрицательную корректировку вознаграждения, ID начисления и причину. Возврат покупателю этот журнал не выполняет. Сумму корректировки определяете вы.</p><label className="flex items-start gap-2 text-xs text-dark-400"><input type="checkbox" checked={acceptNegative} onChange={e => setAcceptNegative(e.target.checked)} />Если корректировка превышает остаток, подтверждаю задолженность в счёт будущих начислений.</label></>}
          <button className={button} disabled={busy}>Сохранить в журнал</button>
          <button type="button" className={quiet + ' ml-2'} disabled={busy} onClick={() => { setKey(operationKey(id, true)); setNotice('Начата новая операция. Используйте после изменения данных предыдущей записи.'); }}>Новая операция</button>
        </form>
        <section className={box}>
          <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); run(async () => { const next = { ...filters, page:'1' }; setFilters(next); await load(id, next); }); }}>
            <label className="text-xs text-dark-400">Ссылка<select className={field + ' mt-1'} value={filters.source} onChange={e => setFilters({ ...filters, source: e.target.value })}><option value="">Все</option>{detail.sources.map((s: Row) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
            <label className="text-xs text-dark-400">С даты<input className={field + ' mt-1'} type="date" value={filters.from} onChange={e => setFilters({ ...filters, from: e.target.value })} /></label>
            <label className="text-xs text-dark-400">По дату<input className={field + ' mt-1'} type="date" value={filters.to} onChange={e => setFilters({ ...filters, to: e.target.value })} /></label><button className={quiet} disabled={busy}>Применить</button>
          </form>
          <div className="mb-4 flex flex-wrap gap-2">{[['purchases', 'Покупки'], ['clients', 'Клиенты'], ['journal', 'Журнал'], ['history', 'История условий']].map(([v, l]) => <button className={tab === v ? button : quiet} key={v} disabled={busy} onClick={() => changeTab(v)}>{l}</button>)}</div>
          <div className="overflow-auto">
            {tab === 'history' ? <table className="w-full text-left text-xs"><thead><tr><th>Дата</th><th>Событие</th><th>Администратор</th><th>Подробности</th></tr></thead><tbody>{detail.history.map((r: Row) => <tr key={r.id} className="border-t border-dark-700"><td className="whitespace-nowrap p-3">{stamp(r.created_at)}</td><td className="p-3">{actions[r.action] || r.action}</td><td className="p-3">{r.actor}</td><td className="max-w-xl break-all p-3">{historyText(r)}</td></tr>)}</tbody></table>
              : tab === 'clients' ? <table className="w-full text-left text-sm"><thead><tr><th>Клиент</th><th>Закреплён</th><th>Ссылка</th><th>Ставка</th><th>Покупки</th></tr></thead><tbody>{detail.clients.map((r: Row) => <tr key={r.client} className="border-t border-dark-700"><td className="p-3">{r.client}</td><td className="whitespace-nowrap p-3">{stamp(r.bound_at)}</td><td className="p-3">{r.source_name}</td><td className="p-3">{r.rate_bps / 100}%</td><td className="p-3">{r.purchases}</td></tr>)}</tbody></table>
              : <table className="w-full text-left text-sm"><thead><tr><th>ID</th><th>Дата</th><th>Клиент / операция</th><th>Оплачено</th><th>Ставка</th><th>Сумма</th><th>Примечание</th></tr></thead><tbody>{(tab === 'purchases' ? detail.purchases : detail.journal).map((r: Row) => <tr key={r.id} className="border-t border-dark-700"><td className="p-3">{r.id}</td><td className="whitespace-nowrap p-3">{stamp(r.occurred_at)}</td><td className="p-3">{r.user_id ? <a className='text-accent-300' href={'/admin/users/' + r.user_id}>{r.client}</a> : r.client} {labels[r.purchase_kind || r.kind] || r.kind}{r.payment_id && <small className='block text-dark-400'>Покупка #{r.payment_id}</small>}</td><td className="p-3">{r.purchase_cents != null ? money(r.purchase_cents) : '—'}</td><td className="p-3">{r.rate_bps != null ? r.rate_bps / 100 + '%' : '—'}</td><td className="whitespace-nowrap p-3">{money(r.amount_cents)}</td><td className="max-w-sm break-words p-3">{r.note} {r.related_id ? '(запись ' + r.related_id + ')' : ''}</td></tr>)}</tbody></table>}
          </div><div className="mt-4 flex items-center justify-between gap-3"><button className={quiet} disabled={busy || detail.page <= 1} onClick={() => turnPage(-1)}>Назад</button><span className="text-xs text-dark-400">Страница {detail.page}</span><button className={quiet} disabled={busy || !detail.has_more[tab]} onClick={() => turnPage(1)}>Далее</button></div>
        </section>
      </> : <p className="text-sm text-dark-400">Выберите партнёра или создайте нового.</p>}</div>
    </div>}
  </div>;
}
