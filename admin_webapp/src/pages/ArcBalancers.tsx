import { useEffect, useState } from 'react';
import ArcSubscriptionCatalog from './ArcSubscriptionCatalog';

type Policy = { id: string; name: string; kind: 'auto' | 'youtube' | 'bypass'; members: string[]; weights: Record<string, number>; strategy: string; fallback: string };
export default function ArcBalancers() {
  const [items, setItems] = useState<Policy[]>([]);
  const [revision, setRevision] = useState('');
  const [preview, setPreview] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch('/api/admin/subscription-balancers', { credentials: 'include' }).then(async r => {
      if (!r.ok) throw new Error();
      const data = await r.json();
      setItems(data.draft || (data.live.length ? data.live : data.defaults)); setRevision(data.revision);
    }).catch(() => setMessage('Не удалось загрузить настройки. Нужны права управления подпиской.'));
  }, []);
  const update = (next: Policy[]) => { setItems(next); setPreview(''); setMessage(''); };
  const action = async (action: string) => {
    setBusy(true);
    try {
      const response = await fetch('/api/admin/subscription-balancers', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, balancers: items, revision, preview_hash: preview }) });
      if (!response.ok) throw new Error();
      const data = await response.json();
      setRevision(data.revision);
      setPreview(action === 'preview' ? data.preview_hash : '');
      setMessage(action === 'draft' ? 'Черновик сохранён. Подписки не изменены.' : action === 'publish' ? 'Опубликовано. Клиентам нужно обновить подписку.' : 'Проверьте порядок, состав и резерв ниже, затем опубликуйте.');
    } catch { setMessage('Операция не выполнена. Проверьте поля; если настройки изменились, перезагрузите страницу.'); }
    finally { setBusy(false); }
  };
  return <section className="space-y-4">
    <header><h2 className="text-xl font-semibold text-dark-100">Балансировщики подписки</h2><p className="mt-2 text-sm text-dark-400">Happ JSON: автовыбор, YouTube и обходы. Ручные локации и адреса подписок сохраняются. Порядок карточек задаёт порядок балансировщиков.</p><p className="mt-1 text-xs text-dark-400">Распределение людей по весам закрепляет основную локацию за пользователем. Пропорции приблизительные; при сбое используется резерв. Для leastLoad вес влияет на стоимость задержки. Существующий резерв сохраняет текущую цепочку; у YouTube CDN-резерва нет.</p></header>
    {items.map((item, index) => <article key={item.id} className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5">
      <div className="flex flex-wrap gap-3"><label className="flex-1 text-sm text-dark-400">Название<input value={item.name} maxLength={100} onChange={e => update(items.map((p, i) => i === index ? { ...p, name: e.target.value } : p))} className="mt-1 w-full rounded-lg border border-dark-700 bg-dark-900 p-2 text-dark-100" /></label><div className="flex items-end gap-2"><button disabled={index === 0} onClick={() => { const next = [...items]; [next[index-1], next[index]] = [next[index], next[index-1]]; update(next); }} className="p-2 disabled:opacity-30" aria-label={`Поднять ${item.name}`}>↑</button><button disabled={index === items.length-1} onClick={() => { const next = [...items]; [next[index+1], next[index]] = [next[index], next[index+1]]; update(next); }} className="p-2 disabled:opacity-30" aria-label={`Опустить ${item.name}`}>↓</button><button onClick={() => update(items.filter((_, i) => i !== index))} className="p-2 text-warning-400">Удалить</button></div></div>
      <div className="mt-4 grid gap-4 md:grid-cols-3"><label className="text-sm text-dark-400">Тип<select value={item.kind} onChange={e => update(items.map((p,i) => i === index ? {...p,kind:e.target.value as Policy['kind']} : p))} className="mt-1 w-full rounded-lg bg-dark-900 p-2"><option value="auto">Автовыбор</option><option value="youtube">YouTube без рекламы</option><option value="bypass">Обход</option></select></label><label className="text-sm text-dark-400">Выбор локации<select value={item.strategy} onChange={e => update(items.map((p,i) => i === index ? {...p,strategy:e.target.value} : p))} className="mt-1 w-full rounded-lg bg-dark-900 p-2"><option value="leastLoad">По нагрузке и задержке</option><option value="leastPing">Минимальный пинг</option><option value="roundRobin">По очереди</option><option value="random">Случайно</option><option value="weightedUsers">Люди по весам</option></select></label><label className="text-sm text-dark-400">Если локации недоступны<select value={item.fallback} onChange={e => update(items.map((p,i) => i === index ? {...p,fallback:e.target.value} : p))} className="mt-1 w-full rounded-lg bg-dark-900 p-2"><option value="existing">Существующий резерв</option><option value="block">Остановить подключение</option></select></label></div>
      <div className="mt-4 flex flex-wrap gap-5">{[['fi','Финляндия'],['ee','Эстония']].map(([code,label]) => <div key={code} className="flex items-center gap-2 text-sm"><label><input type="checkbox" checked={item.members.includes(code)} onChange={e => update(items.map((p,i) => i === index ? {...p,members:e.target.checked ? [...p.members,code] : p.members.filter(m=>m!==code)} : p))} /> {label}</label><label className="text-dark-400">Вес <input type="number" min={1} max={100} disabled={!['leastLoad','weightedUsers'].includes(item.strategy)} value={item.weights[code] || 1} onChange={e => update(items.map((p,i) => i === index ? {...p,weights:{...p.weights,[code]:Number(e.target.value)}} : p))} className="w-16 rounded bg-dark-900 p-1" /></label></div>)}</div>
    </article>)}
    <div className="flex flex-wrap gap-3"><button onClick={() => update([...items, {id:`custom-${Date.now()}`,kind:'auto',name:'Новый балансировщик',members:['fi','ee'],weights:{fi:1,ee:1},strategy:'leastLoad',fallback:'existing'}])} className="rounded-xl border border-dark-700 px-4 py-2">Добавить балансировщик</button><button disabled={busy || !items.length} onClick={()=>action('draft')} className="rounded-xl border border-dark-700 px-4 py-2">Сохранить черновик</button><button disabled={busy || !items.length} onClick={()=>action('preview')} className="rounded-xl border border-primary-500/40 px-4 py-2">Предпросмотр</button>{preview && <button disabled={busy} onClick={()=>action('publish')} className="rounded-xl bg-primary-500/20 px-4 py-2 text-primary-300">Опубликовать проверенный состав</button>}</div>
    {message && <p role="status" className="text-sm text-primary-300">{message}</p>}
    {preview && <div className="rounded-xl border border-dark-700 p-4"><h3 className="font-semibold">Будет опубликовано</h3><ol className="mt-2 space-y-2">{items.map((item,i)=><li key={item.id}>{i+1}. {item.name} — {item.members.map(m=>m==='fi'?'Финляндия':'Эстония').join(', ')}; {item.strategy}; резерв: {item.fallback==='block'?'остановить':'существующий'}</li>)}</ol></div>}
    <ArcSubscriptionCatalog />
  </section>;
}
