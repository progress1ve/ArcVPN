import { useState } from 'react';
export type Period = 'today' | 'week' | 'month' | '30days' | 'all' | 'custom';
export function periodDates(period: Period, now = new Date()) {
 const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Moscow', year:'numeric', month:'2-digit',day:'2-digit' }).format(now);
 const day = new Date(today + 'T12:00:00Z');
 if (period === 'all' || period === 'custom') return {from:'',to:''};
 if (period === 'month') return {from:today.slice(0,8)+'01',to:today};
 day.setUTCDate(day.getUTCDate()-(period === 'week' ? 6 : period === '30days' ? 29 : 0));
 return {from:day.toISOString().slice(0,10),to:today};
}
export function PeriodPicker({value,onChange,dates}:{value:Period;onChange:(period:Period,dates:{from:string;to:string})=>void;dates:{from:string;to:string}}) {
 const [draft,setDraft]=useState(dates);
 return <div className="space-y-3"><div className="flex flex-wrap gap-2" aria-label="Период">{([['today','Сегодня'],['week','7 дней'],['30days','30 дней'],['month','Месяц'],['all','Всё время'],['custom','Период']] as const).map(([key,label])=><button key={key} aria-pressed={value===key} className={`rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-accent-500 ${value===key?'bg-accent-500 text-on-accent':'bg-dark-800 text-dark-300 hover:bg-dark-700'}`} onClick={()=>{if(key==='custom')setDraft(dates);onChange(key,key==='custom'?dates:periodDates(key));}}>{label}</button>)}</div>{value==='custom'&&<form className="flex flex-wrap items-end gap-3" onSubmit={e=>{e.preventDefault();onChange('custom',draft);}}><label className="text-xs text-dark-400">С даты<input aria-label="С даты" type="date" className="ml-2 rounded-lg border border-dark-700 bg-dark-800 p-2" value={draft.from} onInput={e=>setDraft({...draft,from:e.currentTarget.value})} onChange={e=>setDraft({...draft,from:e.target.value})}/></label><label className="text-xs text-dark-400">По дату<input aria-label="По дату" type="date" className="ml-2 rounded-lg border border-dark-700 bg-dark-800 p-2" value={draft.to} onInput={e=>setDraft({...draft,to:e.currentTarget.value})} onChange={e=>setDraft({...draft,to:e.target.value})}/></label><button className="btn-primary" type="submit">Применить</button></form>}</div>;
}
