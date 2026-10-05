import {useState,lazy,Suspense} from 'react';
import {useQuery} from '@tanstack/react-query';
import {getJson} from '@/arcvpn/api';
import {PeriodPicker,periodDates,type Period} from './PeriodPicker';
import {StatCard} from '@/components/stats/StatCard';
const Chart=lazy(()=>import('@/components/sales-stats/SimpleAreaChart').then(m=>({default:m.SimpleAreaChart})));
export function AcquisitionStats() {
 const [period,setPeriod]=useState<Period>('month');const [dates,setDates]=useState(()=>periodDates('month'));
 const {data,isError,isPending}=useQuery({queryKey:['admin-acquisition',dates],queryFn:()=>getJson('/api/admin/acquisition?'+new URLSearchParams(dates))});
 return <section className="space-y-4"><div><h2 className="text-lg font-semibold">Привлечение пользователей</h2><p className="mt-1 text-sm text-dark-400">Регистрации по источникам · московское время</p></div><PeriodPicker value={period} dates={dates} onChange={(next,value)=>{setPeriod(next);setDates(value);}}/>{isError?<p role="alert" className="text-error-400">Не удалось загрузить привлечение пользователей.</p>:isPending?<p role="status">Загружаем…</p>:<><div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[['Всего',data?.total],['Напрямую',data?.direct],['По рефералам',data?.referral],['По рекламным ссылкам',data?.campaign]].map(([label,value])=><StatCard key={String(label)} label={String(label)} value={Number(value||0)}/>)}</div><div className="grid gap-3 lg:grid-cols-3"><Suspense fallback={<p>Загружаем графики…</p>}>{([['direct','Прямые регистрации'],['referral','Приглашения пользователей'],['campaign','Рекламные ссылки']] as const).map(([key,title])=><Chart key={key} title={title} valueLabel="Регистрации" chartId={'acquisition-'+key} data={(data?.series||[]).map((row:Record<string,string|number>)=>({date:String(row.day),value:Number(row[key])}))}/>)}</Suspense></div><p className="text-xs text-dark-500">Каждый пользователь учитывается один раз: личное приглашение, рекламная ссылка либо прямой вход. Покупки не влияют на число регистраций.</p></>}</section>;
}
