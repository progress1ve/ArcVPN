import {useEffect,useState} from 'react';
type Profile={name:string;kind:string;strategy:string|null;members:number};
export default function ArcEffectiveStructure(){
 const [profiles,setProfiles]=useState<Profile[]|null>(null);const [failed,setFailed]=useState(false);
 useEffect(()=>{fetch('/api/admin/subscription-structure',{credentials:'include'}).then(async r=>{if(!r.ok)throw new Error();setProfiles((await r.json()).profiles);}).catch(()=>setFailed(true));},[]);
 return <section className="rounded-2xl border border-dark-700 p-5"><h2 className="font-semibold">Фактически выдаваемая структура</h2><p className="mt-2 text-sm text-dark-400">Тот же генератор Happ JSON, что используется в клиентской подписке владельца. Это опубликованная структура; настройки ниже — редактор. Состав для других тарифов может отличаться.</p>{failed?<p className="mt-3 text-warning-400">Не удалось прочитать действующую подписку. Не считаем редактор синхронизированным.</p>:profiles?<ol className="mt-4 space-y-2">{profiles.map((p,i)=><li key={i} className="flex flex-wrap justify-between gap-2 border-b border-dark-700 py-2"><span>{i+1}. {p.name}</span><span className="text-xs text-dark-400">{p.kind==='balancer'?`Балансировщик · ${p.strategy}`:'Локация'}</span></li>)}</ol>:<p className="mt-3 text-dark-400">Читаем действующую подписку…</p>}</section>;
}
