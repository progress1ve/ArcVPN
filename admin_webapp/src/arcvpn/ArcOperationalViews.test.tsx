// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ArcUserProfile from './ArcUserProfile';
import ArcSupport from './ArcSupport';
import ArcFeedback from './ArcFeedback';
const calls = vi.hoisted(() => ({ getJson: vi.fn(), access: vi.fn() }));
vi.mock('./api', () => calls);
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
function mount(component: React.ReactNode, path: string, route: string) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={route} element={component} />
          <Route path="/admin" element={<p>Главная админка</p>} />
          <Route path="/admin/users" element={<p>Список пользователей</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
describe('ArcVPN operator views', () => {
  it('uses the users heading navigation in answers without a redundant refresh action', async () => {
    calls.getJson.mockResolvedValue({ answers: [], summary: [], total: 0 });
    mount(<ArcFeedback />, '/admin/feedback', '/admin/feedback');
    expect(screen.queryByRole('button', { name: 'Обновить' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Вернуться в админку' }));
    expect(await screen.findByText('Главная админка')).toBeTruthy();
  });
  it('requests ticket waiting and unread order from the server', async () => {
    calls.access.mockResolvedValue({ role: 'owner' });
    calls.getJson.mockResolvedValue({ threads: [], total: 0 });
    mount(<ArcSupport />, '/admin/tickets', '/admin/tickets');
    expect(screen.queryByRole('button', { name: 'Обновить' })).toBeNull();
    fireEvent.change(screen.getByLabelText('Фильтр обращений'), { target: { value: 'waiting' } });
    fireEvent.change(screen.getByLabelText('Порядок обращений'), {
      target: { value: 'unreviewed' },
    });
    await waitFor(() =>
      expect(calls.getJson).toHaveBeenCalledWith(
        expect.stringContaining('status=waiting&order=unreviewed'),
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Вернуться в админку' }));
    expect(await screen.findByText('Главная админка')).toBeTruthy();
  });
  it('shows real subscription, separated totals and unknown telemetry without donor defaults', async () => {
    calls.getJson.mockResolvedValue({
      user: {
        telegram_id: 100,
        first_name: 'Тест',
        device_limit: 4,
        lte_quota_gb: 40,
        lte_used_bytes: 0,
      },
      summary: {
        first_subscription_at: '2026-08-01',
        purchase_totals: { rub: 299, usd: 2.5, stars: 25, count: 3 },
      },
      presence: {
        online: null,
        last_online_at: null,
        last_node: null,
        source: 'Панель недоступна',
      },
      subscriptions: [
        {
          id: 1,
          active: 0,
          panel_disabled_at: '2026-09-01',
          plan_name: 'Кастомный тариф',
          traffic_used: 1024 ** 3,
        },
      ],
      payments: [],
      devices: [],
      support: [],
      referrals: { friends: [] },
      lifecycle_answers: [],
    });
    mount(<ArcUserProfile />, '/admin/users/100', '/admin/users/:id');
    expect(await screen.findByText('Доступ отключён')).toBeTruthy();
    expect(screen.getByText('Онлайн неизвестен')).toBeTruthy();
    expect(screen.getByText('Кастомный тариф')).toBeTruthy();
    expect(screen.getByText(/2.5 USD/)).toBeTruthy();
    expect(screen.getByText('Нет достоверных данных')).toBeTruthy();
    expect(screen.queryByText('Промо-группа')).toBeNull();
    expect(screen.queryByText('Подарки')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Устройства' }));
    expect(screen.getByText('Устройства ещё не зарегистрированы.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Обновить' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Вернуться к пользователям' }));
    expect(await screen.findByText('Список пользователей')).toBeTruthy();
  });
  it('preserves a failed reply and distinguishes AI from manager messages', async () => {
    calls.access.mockResolvedValue({ role: 'owner' });
    calls.getJson.mockImplementation((path: string, init?: RequestInit) => {
      if (init?.method === 'POST') return Promise.reject(new Error('failed'));
      if (path.includes('?')) return Promise.resolve({ threads: [], total: 0, next_cursor: null });
      return Promise.resolve({
        thread: {
          id: 7,
          telegram_id: 100,
          first_name: 'Тест',
          status: 'open',
          ai_handoff_reason: 'spam',
        },
        messages: [
          { id: 1, sender: 'admin', is_ai: 1, body: 'AI message' },
          { id: 2, sender: 'admin', is_ai: 0, body: 'Manager message' },
        ],
      });
    });
    mount(<ArcSupport />, '/admin/tickets/7', '/admin/tickets/:ticketId');
    expect(await screen.findByText('ИИ-помощник')).toBeTruthy();
    expect(screen.getByText('Менеджер')).toBeTruthy();
    const input = screen.getByLabelText('Ответ менеджера') as HTMLTextAreaElement;
    await waitFor(() => expect(input.disabled).toBe(false));
    fireEvent.change(input, { target: { value: 'Проверяем проблему' } });
    fireEvent.click(screen.getByRole('button', { name: 'Отправить ответ' }));
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(input.value).toBe('Проверяем проблему');
    expect(calls.getJson).toHaveBeenCalledWith('/api/admin/support/threads/7', {
      method: 'POST',
      body: JSON.stringify({ body: 'Проверяем проблему' }),
    });
  });
});
