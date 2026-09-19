import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { adminRemnawaveApi } from '@/api/adminRemnawave';
import { AdminBackButton } from '@/components/admin';
import { ServerIcon, UsersIcon, ChevronRightIcon } from '@/components/icons';
import { Skeleton, SkeletonGroup } from '@/components/ui/skeleton';

export default function AdminSquads() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ['admin-remnawave-squads'], queryFn: adminRemnawaveApi.getSquads });
  const squads = query.data?.items || [];
  return <div className="animate-fade-in space-y-5">
    <div className="flex items-center gap-3"><AdminBackButton /><div><h1 className="text-2xl font-bold text-dark-100">Сквады</h1><p className="text-sm text-dark-400">Реальные internal squads Remnawave, их пользователи и inbound-наборы.</p></div></div>
    {query.isError && <div className="rounded-xl border border-error-500/30 bg-error-500/10 p-5 text-error-400">Не удалось загрузить сквады Remnawave.</div>}
    {query.isLoading ? <SkeletonGroup className="grid gap-3 md:grid-cols-2"><Skeleton variant="card" count={4} className="h-28" /></SkeletonGroup> : squads.length === 0 ? <div className="rounded-xl border border-dark-700 bg-dark-800/50 p-8 text-center text-dark-400">В Remnawave нет доступных internal squads.</div> : <div className="grid gap-3 md:grid-cols-2">{squads.map(squad => <button key={squad.uuid} onClick={()=>navigate(`/admin/remnawave/squads/${squad.uuid}`)} className="flex items-center gap-4 rounded-xl border border-dark-700 bg-dark-800/50 p-4 text-left transition hover:border-accent-500/50 hover:bg-dark-800"><div className="rounded-lg bg-accent-500/15 p-2 text-accent-400"><ServerIcon /></div><div className="min-w-0 flex-1"><div className="truncate font-semibold text-dark-100">{squad.display_name || squad.name}</div><div className="mt-1 flex gap-4 text-xs text-dark-400"><span className="flex items-center gap-1"><UsersIcon className="h-4 w-4" />{squad.members_count} пользователей</span><span>{squad.inbounds_count} inbound</span></div></div><ChevronRightIcon /></button>)}</div>}
  </div>;
}
