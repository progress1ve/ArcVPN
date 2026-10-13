import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { TicketIcon } from '@/components/icons';
import { getJson } from './api';

export default function ArcSupportBell() {
  const query = useQuery({
    queryKey: ['arc-support-unread'],
    queryFn: () => getJson('/api/admin/support/threads?status=unread&limit=1'),
    refetchInterval: 30000,
    retry: false,
  });
  const total = query.data?.total;
  return (
    <Link
      to="/admin/tickets"
      aria-label={`Поддержка${total > 0 ? `: ${total} непрочитанных обращений` : ''}`}
      className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-dark-700/50 text-dark-300 hover:text-accent-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400"
    >
      <TicketIcon />
      {total > 0 && (
        <span className="absolute -right-1 -top-1 rounded-full bg-accent-500 px-1.5 text-[10px] text-white">
          {total}
        </span>
      )}
    </Link>
  );
}
