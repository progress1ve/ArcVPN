import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Twemoji from 'react-twemoji';
import { PlatformProvider } from '@/platform/PlatformProvider';
import { ThemeColorsProvider } from '@/providers/ThemeColorsProvider';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { ToastProvider } from '@/components/Toast';
import { TooltipProvider } from '@/components/primitives/Tooltip';
import { BackgroundHost } from '@/components/backgrounds/BackgroundHost';
import Layout from '@/components/layout/Layout';
import AdminPanel from '@/pages/AdminPanel';
import AdminDashboard from '@/pages/AdminDashboard';
import AdminUsers from '@/pages/AdminUsers';
import AdminUserDetail from '@/pages/AdminUserDetail';
import ReferralNetwork from '@/pages/ReferralNetwork';
import AdminPayments from '@/pages/AdminPayments';
import AdminSalesStats from '@/pages/AdminSalesStats';
import AdminTrafficUsage from '@/pages/AdminTrafficUsage';
import AdminTickets from '@/pages/AdminTickets';
import AdminRemnawave from '@/pages/AdminRemnawave';
import AdminRemnawaveSquadDetail from '@/pages/AdminRemnawaveSquadDetail';
import AdminSquads from '@/pages/AdminSquads';
import { useAuthStore } from '@/store/auth';
import { usePermissionStore } from '@/store/permissions';
import { access, login } from './api';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});
const permissions = [
  'stats:read',
  'users:read',
  'payments:read',
  'tickets:read',
  'traffic:read',
  'sales_stats:read',
  'servers:read',
  'remnawave:read',
  'audit:read',
];

try {
  sessionStorage.setItem(
    'cabinet_branding',
    JSON.stringify({ name: 'ArcVPN', logo_url: null, logo_letter: 'A', has_custom_logo: false }),
  );
  localStorage.removeItem('cabinet_branding');
} catch {
  // Storage can be unavailable in hardened webviews; upstream fallbacks still apply.
}

function seedSession(role = 'owner') {
  useAuthStore.setState({
    isAuthenticated: true,
    isLoading: false,
    isAdmin: true,
    accessToken: null,
    user: {
      id: 0,
      telegram_id: 0,
      username: 'owner',
      first_name: 'Владелец',
      last_name: null,
    } as never,
  });
  usePermissionStore.setState({ permissions, roles: [role], roleLevel: 999, isLoaded: true });
}

function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <main className="flex min-h-screen items-center justify-center bg-dark-950 px-4">
      <form
        className="w-full max-w-sm rounded-2xl border border-dark-700 bg-dark-900 p-6 shadow-2xl"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError('');
          try {
            await login(password);
            seedSession();
            onSuccess();
          } catch {
            setError('Неверный пароль или сервер недоступен');
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl bg-accent-500/15 text-xl font-bold text-accent-400">
          A
        </div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-accent-400">ArcVPN</p>
        <h1 className="mb-2 text-2xl font-bold text-dark-50">Вход в админ-панель</h1>
        <p className="mb-6 text-sm text-dark-400">Используйте административный пароль.</p>
        <label className="mb-2 block text-xs text-dark-300" htmlFor="admin-password">
          Пароль
        </label>
        <input
          id="admin-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mb-3 w-full rounded-xl border border-dark-700 bg-dark-800 px-4 py-3 text-dark-100 outline-none focus:border-accent-500"
        />
        {error && <p className="mb-3 text-sm text-error-400">{error}</p>}
        <button
          disabled={busy || !password}
          className="w-full rounded-xl bg-accent-500 px-4 py-3 font-semibold text-white disabled:opacity-50"
        >
          {busy ? 'Проверяем…' : 'Войти'}
        </button>
        <a
          className="mt-5 block text-center text-[11px] text-dark-500 hover:text-dark-300"
          href="https://github.com/progress1ve/ArcVPN/tree/main/admin_webapp"
          target="_blank"
          rel="noreferrer"
        >
          Исходный код · AGPL-3.0
        </a>
      </form>
    </main>
  );
}

function Unavailable() {
  return (
    <div className="py-20 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-dark-700 bg-dark-800 text-accent-400">
        A
      </div>
      <h1 className="text-xl font-bold text-dark-100">Раздел подключается к ArcVPN</h1>
      <p className="mt-2 text-sm text-dark-400">
        Интерфейс BEDOLAGA перенесён; для этого раздела ещё нужен серверный адаптер.
      </p>
    </div>
  );
}

function AdminRoutes() {
  return (
    <>
      <BackgroundHost />
      <Layout>
        <Routes>
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/users/:id" element={<AdminUserDetail />} />
          <Route path="/admin/referral-network" element={<ReferralNetwork />} />
          <Route path="/admin/payments" element={<AdminPayments />} />
          <Route path="/admin/sales-stats" element={<AdminSalesStats />} />
          <Route path="/admin/traffic" element={<AdminTrafficUsage />} />
          <Route path="/admin/traffic-usage" element={<AdminTrafficUsage />} />
          <Route path="/admin/tickets" element={<AdminTickets />} />
          <Route path="/admin/tickets/:ticketId" element={<AdminTickets />} />
          <Route path="/admin/remnawave" element={<AdminRemnawave />} />
          <Route path="/admin/squads" element={<AdminSquads />} />
          <Route path="/admin/remnawave/squads/:uuid" element={<AdminRemnawaveSquadDetail />} />
          <Route path="/admin/*" element={<Unavailable />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Layout>
      <a
        className="fixed bottom-2 right-3 z-[70] text-[10px] text-dark-600 transition-colors hover:text-dark-300 focus:text-dark-200"
        href="https://github.com/progress1ve/ArcVPN/tree/main/admin_webapp"
        target="_blank"
        rel="noreferrer"
      >
        Исходный код · AGPL-3.0
      </a>
    </>
  );
}

export function ArcAdminRoot() {
  const [state, setState] = useState<'loading' | 'ready' | 'login'>('loading');
  useEffect(() => {
    access()
      .then((result) => {
        seedSession(String(result.role || 'owner'));
        setState('ready');
      })
      .catch(() => setState('login'));
  }, []);
  if (state === 'loading')
    return (
      <div className="flex min-h-screen items-center justify-center bg-dark-950 text-sm text-dark-400">
        Загрузка ArcVPN Admin…
      </div>
    );
  if (state === 'login') return <Login onSuccess={() => setState('ready')} />;
  return <AdminRoutes />;
}

export default function Root() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PlatformProvider>
          <ThemeColorsProvider>
            <TooltipProvider>
              <ToastProvider>
                <WebSocketProvider>
                  <Twemoji options={{ className: 'twemoji', folder: 'svg', ext: '.svg' }}>
                    <ArcAdminRoot />
                  </Twemoji>
                </WebSocketProvider>
              </ToastProvider>
            </TooltipProvider>
          </ThemeColorsProvider>
        </PlatformProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
