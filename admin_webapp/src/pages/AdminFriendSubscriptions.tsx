import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { QRCodeSVG } from 'qrcode.react';
import { getJson } from '@/arcvpn/api';
import { BackIcon, UserPlusIcon } from '@/components/icons';

type Guest = { id: number; label: string; expires_at: string; device_limit: number; devices_used: number; lte_quota_gb: number; state: string; sub_url: string | null };
const field = 'w-full rounded-xl border border-dark-700 bg-dark-800 p-3 text-dark-100';

export default function AdminFriendSubscriptions() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Guest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [label, setLabel] = useState('');
  const [days, setDays] = useState('3');
  const [devices, setDevices] = useState('3');
  const [quota, setQuota] = useState(15);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [qr, setQr] = useState<Guest | null>(null);
  const load = async () => {
    const result = await getJson('/api/admin/friend-subscriptions');
    setItems(result.subscriptions);
  };
  useEffect(() => {
    load().catch(() => setError('Не удалось загрузить временные подписки.')).finally(() => setLoading(false));
    const timer = setInterval(() => load().catch(() => {}), 30000);
    return () => clearInterval(timer);
  }, []);
  const create = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const result = await getJson('/api/admin/friend-subscriptions', { method: 'POST', body: JSON.stringify({ label, days: Number(days), device_limit: Number(devices), lte_quota_gb: quota, request_id: requestId }) });
      setItems(result.subscriptions);
      const created = result.subscriptions.find((item: Guest) => item.id === result.created_id);
      if (created?.sub_url) { setQr(created); setLabel(''); setRequestId(crypto.randomUUID()); }
      else if (created?.state === 'failed' || created?.state === 'deleting') { setError('Создание не завершилось. Неиспользуемый доступ удаляется; можно попробовать снова.'); setRequestId(crypto.randomUUID()); }
      else setNotice('Создание ещё выполняется. Подписка появится в списке.');
    } catch (err) { setError(err instanceof Error && err.message.includes('403') ? 'Запрос отклонён. Перезагрузите страницу и войдите в админку заново, если потребуется.' : 'Не удалось создать доступ. Обновите список перед повторной попыткой: создание могло завершиться на сервере.'); }
    finally { setBusy(false); }
  };
  const remove = async (item: Guest) => {
    if (!window.confirm(`Отключить и удалить доступ «${item.label}»?`)) return;
    setBusy(true); setError('');
    try { await getJson(`/api/admin/friend-subscriptions/${item.id}`, { method: 'DELETE' }); await load(); if (qr?.id === item.id) setQr(null); }
    catch { setError('Не удалось отключить доступ. Повторите попытку.'); }
    finally { setBusy(false); }
  };
  const copy = async (url: string) => {
    try { await navigator.clipboard.writeText(url); setNotice('Ссылка скопирована.'); }
    catch { setError('Не удалось скопировать. Выделите ссылку под QR-кодом.'); }
  };
  return <div className="mx-auto max-w-4xl space-y-6 pb-12">
    <header className="flex items-center gap-3"><button aria-label="Назад к пользователям" className={field + ' !w-auto'} onClick={() => navigate('/admin/users')}><BackIcon /></button><div><h1 className="text-xl font-bold">Доступ для друзей</h1><p className="text-sm text-dark-400">Временная подписка через CDN · удаляется по окончании срока</p></div></header>
    <form onSubmit={create} className="space-y-4 rounded-2xl border border-dark-700 p-5">
      <h2 className="font-semibold">Создать подписку</h2>
      <label className="block text-sm">Название<input className={field + ' mt-2'} value={label} maxLength={80} required placeholder="Например, друзья — выходные" onChange={e => { setLabel(e.target.value); setRequestId(crypto.randomUUID()); }} disabled={busy} /></label>
      <div className="grid gap-4 sm:grid-cols-3">
        <label className="text-sm">Срок, дней<input className={field + ' mt-2'} type="number" min={1} max={90} value={days} onChange={e => {setDays(e.target.value);setRequestId(crypto.randomUUID());}} required disabled={busy} /></label>
        <label className="text-sm">Устройств<input className={field + ' mt-2'} type="number" min={1} max={15} value={devices} onChange={e => {setDevices(e.target.value);setRequestId(crypto.randomUUID());}} required disabled={busy} /></label>
        <label className="text-sm">Обход LTE/CDN, ГБ<select className={field + ' mt-2'} value={quota} onChange={e => {setQuota(Number(e.target.value));setRequestId(crypto.randomUUID());}} disabled={busy}>{Array.from({ length: 33 }, (_, i) => (i + 1) * 15).map(v => <option key={v} value={v}>{v} ГБ</option>)}</select></label>
      </div>
      <p className="text-sm text-dark-400">Срок начинается сразу. Одну ссылку можно раздать нескольким людям; лимиты устройств и обхода общие для всех.</p>
      <button disabled={busy || !label.trim()} className="flex items-center gap-2 rounded-xl bg-accent-500 px-5 py-3 font-semibold disabled:opacity-50"><UserPlusIcon />{busy ? 'Выполняется…' : 'Создать доступ'}</button>
    </form>
    {error && <p role="alert" className="text-error-400">{error}</p>}{notice && <p role="status" className="text-dark-300">{notice}</p>}
    {qr?.sub_url && <section className="space-y-4 rounded-2xl border border-dark-700 p-5"><div className="flex items-center justify-between gap-3"><h2 className="font-semibold">{qr.label}</h2><button onClick={() => setQr(null)} className="text-sm text-dark-400">Скрыть QR</button></div><div className="w-fit rounded-xl bg-white p-4"><QRCodeSVG value={qr.sub_url} size={220} level="M" /></div><p className="text-sm text-dark-400">Сканируйте в VPN-клиенте или скопируйте ссылку для импорта.</p><code className="block break-all text-xs text-dark-300">{qr.sub_url}</code><button className={field + ' !w-auto'} onClick={() => copy(qr.sub_url!)}>Скопировать ссылку</button></section>}
    <section className="space-y-3"><h2 className="font-semibold">Созданные подписки</h2>{loading ? <p className="text-dark-400">Загрузка…</p> : !items.length ? <p className="text-dark-400">Пока нет временных подписок.</p> : items.map(item => <article key={item.id} className="rounded-xl border border-dark-700 p-4"><h3 className="break-words font-semibold">{item.label}</h3><p className="mt-2 text-sm text-dark-400">До {new Date(item.expires_at.replace(' ', 'T') + 'Z').toLocaleString('ru-RU')} · устройств {item.devices_used}/{item.device_limit} · обход {item.lte_quota_gb} ГБ</p><div className="mt-3 flex flex-wrap items-center gap-4">{item.sub_url ? <><button onClick={() => setQr(item)} className="text-accent-400">QR-код</button><button onClick={() => copy(item.sub_url!)} className="text-dark-300">Копировать</button></> : <span className="text-sm text-dark-400">{item.state === 'deleting' ? 'Удаляется' : item.state === 'pending' ? 'Создаётся' : item.state === 'failed' ? 'Ошибка создания, доступ удаляется' : 'Срок истёк'}</span>}<button disabled={busy} onClick={() => remove(item)} className="text-sm text-error-400 disabled:opacity-50">Удалить</button></div></article>)}</section>
  </div>;
}
