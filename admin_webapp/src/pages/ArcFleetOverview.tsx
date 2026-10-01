import {useEffect,useState} from 'react';
import {Link} from 'react-router';
type Node={address:string;name:string;connected:boolean;disabled:boolean;users_online:number};
type Capacity={network_user_estimate?:{additional_users:number}|null};
type Traffic={groups:{main:{bytes:number};lte:{bytes:number}}};
const hosts=['87.251.19.197','151.241.137.174'];
const gb=(n:number)=>`${(n/1024**3).toLocaleString('ru-RU',{maximumFractionDigits:2})} ГБ`;
async function read<T>(path:string):Promise<T>{const r=await fetch(path,{credentials:'include'});if(!r.ok)throw new Error();return r.json();}
export default function ArcFleetOverview(){
 const [nodes,setNodes]=useState<Node[]|null>(null);const [capacity,setCapacity]=useState<(Capacity|null)[]>([]);
 const [traffic,setTraffic]=useState<(Traffic|null)[]>([]);const [total,setTotal]=useState<{main:number;lte:number}|null>(null);
 const [health,setHealth]=useState<string>('Проверяем…');const [error,setError]=useState(false);
 useEffect(()=>{let live=true;const load=async()=>{
  const jobs=await Promise.allSettled([read<{remnawave:{nodes:Node[]}}>('/api/admin/overview'),...hosts.map(h=>read<Capacity>(`/api/admin/nodes/capacity?host=${h}&range=7d`)),...hosts.map(h=>read<{results:{operator:string;outcome:string;checked_at:string}[]}>(`/api/admin/nodes/operator-probes?host=${h}`))]);
  if(!live)return;const overview=jobs[0];if(overview.status==='fulfilled')setNodes((overview.value as {remnawave:{nodes:Node[]}}).remnawave.nodes.filter(n=>hosts.includes(n.address)));else setError(true);
  setCapacity(jobs.slice(1,3).map(r=>r.status==='fulfilled'?r.value as Capacity:null));
  // Unknown/offline provider probes do not establish a node outage.
  const recent=jobs.slice(3).flatMap(r=>{if(r.status!=='fulfilled')return [];const seen=new Set<string>();return ((r.value as {results?:{operator:string;outcome:string;checked_at:string}[]}).results||[]).filter(p=>{if(seen.has(p.operator))return false;seen.add(p.operator);return Date.now()-Date.parse(p.checked_at.replace(' ','T')+'Z')<86400000;});});
  setHealth(recent.some(p=>p.outcome==='failed')?'Есть неуспешные проверки':recent.filter(p=>p.outcome==='ok').length>=8?`VPN работает${recent.some(p=>p.outcome==='unknown')?' · есть недоступные пробы':''}`:'Нет свежих подтверждённых проверок');
 };load();const timer=setInterval(load,60000);
 Promise.allSettled([read<Traffic>('/api/admin/traffic/period?period=7&limit=10'),read<Traffic>('/api/admin/traffic/period?period=30&limit=10'),read<{main:number;lte:number}>('/api/admin/traffic/retained-total')]).then(r=>{if(!live)return;setTraffic(r.slice(0,2).map(x=>x.status==='fulfilled'?x.value as Traffic:null));if(r[2].status==='fulfilled')setTotal(r[2].value as {main:number;lte:number});});
 return()=>{live=false;clearInterval(timer);};},[]);
 const complete=capacity.length===2&&capacity.every(c=>c?.network_user_estimate);const spare=capacity.reduce((s,c)=>s+(c?.network_user_estimate?.additional_users||0),0);
 return <div className="space-y-6">
  {error&&<p role="alert" className="text-warning-400">Не удалось обновить состояние нод.</p>}
  <div className="grid gap-4 sm:grid-cols-2"><section className="rounded-2xl border border-dark-700 p-5"><p className="text-dark-400">Онлайн на нодах</p><p className="mt-2 text-3xl font-semibold">{nodes?nodes.reduce((s,n)=>s+n.users_online,0):'—'}</p><p className="mt-2 text-xs text-dark-400">Сумма сессий Эстонии и Финляндии; один человек может иметь несколько соединений.</p></section><section className="rounded-2xl border border-dark-700 p-5"><p className="text-dark-400">Ещё можно разместить · оценка</p><p className="mt-2 text-3xl font-semibold">{complete?`${spare} чел.`:'Собираем наблюдения'}</p><p className="mt-2 text-sm text-dark-400">{complete?(spare<20?'Запас небольшой — стоит планировать новую ноду.':'По средней нагрузке запас пока есть.'):'Рекомендация о покупке появится после парных замеров на обеих нодах.'}</p></section></div>
  <section className="rounded-2xl border border-dark-700 p-5"><h2 className="font-semibold">Трафик</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[420px] text-left text-sm [&_th]:px-2 [&_td]:px-2"><thead className="text-dark-400"><tr><th className="py-2">Профили</th><th>7 дней</th><th>30 дней</th><th>За всё время*</th></tr></thead><tbody>{(['main','lte'] as const).map(group=><tr key={group} className="border-t border-dark-700"><th className="py-3 font-normal">{group==='main'?'Обычные':'LTE / CDN'}</th>{[0,1].map(i=><td key={i}>{traffic[i]?gb(traffic[i]!.groups[group].bytes):'—'}</td>)}<td>{total?gb(total[group]):'—'}</td></tr>)}</tbody></table></div><p className="mt-2 text-xs text-dark-400">Фактически израсходовано по истории Remnawave. *С начала учёта пользователей ArcVPN; история до этого периода недоступна.</p></section>
  <section className="rounded-2xl border border-dark-700 p-5"><h2 className="font-semibold">Состояние</h2><div className="mt-3 space-y-3">{nodes?.map(n=><div key={n.address} className="flex flex-wrap justify-between gap-2"><Link className="text-primary-300" to={`/admin/remnawave/nodes/${n.address}`}>{n.name}</Link><span className={n.connected&&!n.disabled?'text-success-400':'text-warning-400'}>{n.connected&&!n.disabled?'В сети':'Недоступна'}</span></div>)}<div className="flex flex-wrap justify-between gap-2 border-t border-dark-700 pt-3"><span>LTE / CDN</span><span className="text-dark-300">{health}</span></div><p className="text-xs text-dark-400">Успешная VPN-проверка не подтверждает работу в период ограничений. Билайн может быть офлайн у провайдера проверок.</p></div></section>
 </div>;
}
