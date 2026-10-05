// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { PlatformContext } from '@/platform/PlatformContext';
import { createWebAdapter } from '@/platform/adapters/WebAdapter';
import ArcPartnerCabinet from './ArcPartnerCabinet';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('uses partner session for login, source filters, pagination and revocation with admin UI components', async () => {
  let authenticated = false;
  const urls: string[] = [];
  const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
    urls.push(url);
    if (url.endsWith('/login')) { authenticated = true; return { ok: true, json: async () => ({ ok: true }) }; }
    if (!authenticated) return { ok: false, status: 401, json: async () => ({ error: 'unauthorized' }) };
    const page = Number(new URL(url, 'https://partners.arccnet.space').searchParams.get('page'));
    return { ok: true, json: async () => ({
      partner: { name: 'Partner fixture' }, sources: [{ id: 7, name: 'Assigned link', url: 'https://t.me/fixture?start=link', active: true, enabled: true }],
      balance: { earned: 2970, accrued: 2970, adjustments: 0, paid: 1000, available: 1970, debt: 0 },
      stats: { clients: 1, paying_clients: 1, purchases: 1, renewals: 0, cohort_paying_clients: 1, conversion_percent: 100, revenue_cents: 9900, avg_purchase_cents: 9900, repeat_clients: 0 },
      network: [], series: [], network_truncated: false,
      purchases: [{ id: 1, client: 'C-opaque', purchase_at: '2026-10-05 10:00:00', purchase_kind: 'new', purchase_description: 'Личный · 30 дней', purchase_cents: 9900, rate_bps: 3000, amount_cents: 2970 }],
      clients: [], journal: [], payouts: [], page, has_more: { purchases: page === 1, clients: false, journal: false, payouts: false },
    }) };
  });
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
  render(<PlatformContext.Provider value={createWebAdapter()}><ArcPartnerCabinet /></PlatformContext.Provider>);
  await screen.findByRole('heading', { name: 'Вход в ArcVPN' });
  fireEvent.change(screen.getByLabelText('Логин'), { target: { value: 'partner-fixture' } });
  fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'fixture-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Войти' }));
  await screen.findByRole('heading', { name: 'Партнёрская панель' });
  expect(screen.getByText('Заработано за всё время')).toBeTruthy();
  expect(screen.queryByText('Начислено')).toBeNull();
  expect(screen.queryByText('Корректировки')).toBeNull();
  expect(screen.queryByText('Журнал')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Покупки' }));
  await screen.findByRole('heading', { name: 'Покупки' });
  await waitFor(() => expect((screen.getByRole('button', { name: 'Применить' }) as HTMLButtonElement).disabled).toBe(false));
  expect(screen.getByText('Личный · 30 дней')).toBeTruthy();
  expect(screen.getByText('C-opaque')).toBeTruthy();
  expect((screen.queryByLabelText('Пароль') as HTMLInputElement | null)).toBeNull();
  fireEvent.change(screen.getByLabelText('Ссылка'), { target: { value: '7' } });
  fireEvent.input(screen.getByLabelText('С даты'), { target: { value: '2026-10-05' } });
  fireEvent.click(screen.getByRole('button', { name: 'Применить' }));
  await waitFor(() => expect(urls[urls.length - 1]).toContain('source=7'));
  expect(urls[urls.length - 1]).toContain('from=2026-10-05');
  await waitFor(() => expect((screen.getByRole('button', { name: 'Далее' }) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }));
  await screen.findByText('Страница 2');
  expect(urls[urls.length - 1]).toContain('source=7');
  expect(urls[urls.length - 1]).toContain('page=2');
  expect(urls.every(url => url.startsWith('/api/partners/'))).toBe(true);
  authenticated = false;
  fireEvent.click(screen.getByRole('button', { name: 'Обновить' }));
  await screen.findByRole('heading', { name: 'Вход в ArcVPN' });
  expect(screen.queryByText('C-opaque')).toBeNull();
  expect(screen.getByRole('alert').textContent).toContain('Сессия завершилась');
  expect(fetchMock.mock.calls.find(([url]) => url.endsWith('/login'))?.[1]?.credentials).toBe('same-origin');
});
