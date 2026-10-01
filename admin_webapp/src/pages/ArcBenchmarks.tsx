import { useEffect, useState } from 'react';
type Job = {id:string;status:string;created_at:string;output:string;exit_code:number|null;source_sha:string};
export default function ArcBenchmarks({host}:{host:string}) {
  const [jobs,setJobs]=useState<Job[]>([]);
  const [ready,setReady]=useState(false);
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);
  const load=async()=>{const r=await fetch(`/api/admin/nodes/benchmarks?host=${encodeURIComponent(host)}`,{credentials:'include'});if(!r.ok)throw new Error();const data=await r.json();setJobs(data.jobs);setReady(!!data.agent_last_seen);};
  useEffect(()=>{load().catch(()=>setMessage('Не удалось загрузить замеры.'));const timer=setInterval(()=>load().catch(()=>{}),10000);return()=>clearInterval(timer);},[host]);
  const action=async(action:string,id?:string)=>{setBusy(true);try{const r=await fetch('/api/admin/nodes/benchmarks',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({host,action,id})});if(!r.ok){const error=await r.json();throw new Error(error.error || 'Не удалось выполнить операцию');}await load();setMessage(action==='cancel'?'Запрошена остановка.':'Замер поставлен в очередь.');}catch(e){setMessage(e instanceof Error?e.message:'Ошибка');}finally{setBusy(false);}};
  const active=jobs.some(j=>['queued','running','cancelling'].includes(j.status));
  const labels:Record<string,string>={queued:'В очереди',running:'Выполняется',cancelling:'Останавливается',cancelled:'Остановлен',completed:'Завершён',failed:'Ошибка'};
  return <section className="rounded-2xl border border-dark-700 bg-dark-800/50 p-5"><h2 className="font-semibold text-dark-100">Multitest · скорость и пинг до России</h2><p className="mt-2 text-sm text-dark-400">Оригинальный модуль 5: Москва, Санкт-Петербург, Нижний Новгород, Челябинск, Тюмень. До 15 минут, 8 потоков; тест может занять канал. Sender и receiver относятся к одному прямому потоку, а не двум направлениям. Резервный город отмечен (F).</p><p className="mt-2 text-xs text-dark-400">Проверенная версия скрипта фиксирована по SHA256; сетевые настройки не меняются.</p>
  {ready ? <button disabled={busy||active} onClick={()=>action('run')} className="mt-4 rounded-xl border border-primary-500/40 px-4 py-2 text-primary-300 disabled:opacity-40">Запустить замер РФ</button> : <p className="mt-4 text-sm text-warning-400">Агент замеров ещё не подключён.</p>}
  {message && <p role="status" className="mt-3 text-sm text-primary-300">{message}</p>}
  <div className="mt-4 space-y-3">{jobs.map(job=><article key={job.id} className="rounded-xl border border-dark-700 p-3"><div className="flex flex-wrap justify-between gap-2 text-sm"><span>{job.created_at} UTC · {labels[job.status]||job.status}</span>{['queued','running'].includes(job.status)&&<button disabled={busy} onClick={()=>action('cancel',job.id)} className="text-warning-400">Остановить</button>}</div><details className="mt-2"><summary className="cursor-pointer text-sm text-primary-300">Результат и полный вывод</summary><p className="mt-2 text-xs text-dark-400">SHA256: {job.source_sha} · код завершения: {job.exit_code ?? '—'}</p><pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-dark-900 p-3 text-xs">{job.output||'Ожидание вывода агента…'}</pre></details></article>)}</div>
  {!jobs.length&&<p className="mt-4 text-sm text-dark-400">Сохранённых замеров пока нет.</p>}
  </section>;
}
