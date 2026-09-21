import { type FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AdminBackButton } from '@/components/admin';
import { useNotify } from '@/platform/hooks/useNotify';
import { copyToClipboard } from '@/utils/clipboard';
import {
  createMarketingCampaign,
  createMarketingPromocode,
  getMarketing,
  updateMarketingCampaign,
  updateMarketingPromocode,
} from './api';

type Tab = 'links' | 'promocodes';

type CampaignItem = {
  id: number;
  name: string;
  code: string;
  link?: string | null;
  is_active: boolean;
  arrivals?: number;
  paying_users?: number;
  entry_bonus_days?: number;
  payment_bonus_days?: number;
};

type PromocodeItem = {
  id: number;
  code: string;
  discount_type: 'fixed' | 'percent';
  discount_percent?: number;
  discount_rub?: number;
  used_count?: number;
  max_uses: number;
  expires_at: string;
  is_active: boolean;
};

async function copy(value: string, notify: ReturnType<typeof useNotify>) {
  try {
    await copyToClipboard(value);
    notify.success('Скопировано');
  } catch {
    notify.error('Не удалось скопировать');
  }
}

export default function ArcMarketing() {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const initialTab = new URLSearchParams(window.location.search).get('tab');
  const [tab, setTab] = useState<Tab>(initialTab === 'promocodes' ? 'promocodes' : 'links');
  const [showForm, setShowForm] = useState(false);
  const [campaign, setCampaign] = useState({
    name: '',
    code: '',
    entry_bonus_days: 0,
    payment_bonus_days: 0,
  });
  const [promocode, setPromocode] = useState({
    code: '',
    discount_type: 'fixed',
    discount_value: 0,
    max_uses: 100,
    duration_days: 30,
  });
  const query = useQuery({ queryKey: ['arc-marketing'], queryFn: getMarketing });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['arc-marketing'] });
  const createCampaign = useMutation({
    mutationFn: () => createMarketingCampaign(campaign),
    onSuccess: () => {
      notify.success('Реферальная ссылка создана');
      setShowForm(false);
      setCampaign({ name: '', code: '', entry_bonus_days: 0, payment_bonus_days: 0 });
      refresh();
    },
    onError: () => notify.error('Не удалось создать ссылку. Проверьте код и название.'),
  });
  const createPromocode = useMutation({
    mutationFn: () => createMarketingPromocode(promocode),
    onSuccess: () => {
      notify.success('Промокод создан');
      setShowForm(false);
      setPromocode({
        code: '',
        discount_type: 'fixed',
        discount_value: 0,
        max_uses: 100,
        duration_days: 30,
      });
      refresh();
    },
    onError: () => notify.error('Не удалось создать промокод. Проверьте поля и уникальность кода.'),
  });
  const campaigns = useMemo(() => (query.data?.campaigns || []) as CampaignItem[], [query.data]);
  const promocodes = useMemo(() => (query.data?.promocodes || []) as PromocodeItem[], [query.data]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    tab === 'links' ? createCampaign.mutate() : createPromocode.mutate();
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6">
      <header className="mb-6 flex flex-wrap items-center gap-3">
        <AdminBackButton />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-dark-50">Маркетинг</h1>
          <p className="mt-1 text-sm text-dark-400">
            Реферальные ссылки и скидочные промокоды ArcVPN
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((value) => !value)}>
          {showForm ? 'Закрыть' : tab === 'links' ? 'Создать ссылку' : 'Создать промокод'}
        </button>
      </header>

      <div className="mb-5 flex gap-2 border-b border-dark-700">
        {(
          [
            ['links', 'Реферальные ссылки'],
            ['promocodes', 'Промокоды'],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            onClick={() => {
              setTab(value);
              setShowForm(false);
            }}
            className={`border-b-2 px-4 py-3 text-sm font-medium ${tab === value ? 'border-accent-500 text-accent-400' : 'border-transparent text-dark-400 hover:text-dark-200'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {showForm && (
        <form
          onSubmit={submit}
          className="mb-5 rounded-2xl border border-dark-700 bg-dark-900/80 p-4 sm:p-5"
        >
          {tab === 'links' ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm text-dark-300">
                Название
                <input
                  required
                  maxLength={100}
                  className="input mt-2"
                  value={campaign.name}
                  onChange={(e) => setCampaign({ ...campaign, name: e.target.value })}
                  placeholder="Telegram · сентябрь"
                />
              </label>
              <label className="text-sm text-dark-300">
                Код ссылки
                <input
                  pattern="[A-Za-z0-9_-]{4,40}"
                  className="input mt-2"
                  value={campaign.code}
                  onChange={(e) => setCampaign({ ...campaign, code: e.target.value })}
                  placeholder="telegram_sep (можно оставить пустым)"
                />
              </label>
              <label className="text-sm text-dark-300">
                Дней за регистрацию
                <input
                  min={0}
                  max={365}
                  type="number"
                  className="input mt-2"
                  value={campaign.entry_bonus_days}
                  onChange={(e) =>
                    setCampaign({ ...campaign, entry_bonus_days: Number(e.target.value) })
                  }
                />
              </label>
              <label className="text-sm text-dark-300">
                Дней после первой оплаты
                <input
                  min={0}
                  max={365}
                  type="number"
                  className="input mt-2"
                  value={campaign.payment_bonus_days}
                  onChange={(e) =>
                    setCampaign({ ...campaign, payment_bonus_days: Number(e.target.value) })
                  }
                />
              </label>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <label className="text-sm text-dark-300">
                Код
                <input
                  required
                  pattern="[A-Za-z0-9_-]{3,32}"
                  className="input mt-2 uppercase"
                  value={promocode.code}
                  onChange={(e) =>
                    setPromocode({ ...promocode, code: e.target.value.toUpperCase() })
                  }
                  placeholder="START20"
                />
              </label>
              <label className="text-sm text-dark-300">
                Тип скидки
                <select
                  className="input mt-2"
                  value={promocode.discount_type}
                  onChange={(e) => setPromocode({ ...promocode, discount_type: e.target.value })}
                >
                  <option value="fixed">Рубли</option>
                  <option value="percent">Проценты</option>
                </select>
              </label>
              <label className="text-sm text-dark-300">
                Размер скидки
                <input
                  required
                  min={1}
                  max={promocode.discount_type === 'percent' ? 100 : 1000000}
                  type="number"
                  className="input mt-2"
                  value={promocode.discount_value}
                  onChange={(e) =>
                    setPromocode({ ...promocode, discount_value: Number(e.target.value) })
                  }
                />
              </label>
              <label className="text-sm text-dark-300">
                Лимит использований
                <input
                  required
                  min={1}
                  type="number"
                  className="input mt-2"
                  value={promocode.max_uses}
                  onChange={(e) => setPromocode({ ...promocode, max_uses: Number(e.target.value) })}
                />
              </label>
              <label className="text-sm text-dark-300">
                Срок, дней
                <input
                  required
                  min={1}
                  max={3650}
                  type="number"
                  className="input mt-2"
                  value={promocode.duration_days}
                  onChange={(e) =>
                    setPromocode({ ...promocode, duration_days: Number(e.target.value) })
                  }
                />
              </label>
            </div>
          )}
          <div className="mt-5 flex justify-end">
            <button
              disabled={createCampaign.isPending || createPromocode.isPending}
              className="btn-primary disabled:opacity-50"
            >
              Создать
            </button>
          </div>
        </form>
      )}

      {query.isLoading && <div className="py-16 text-center text-dark-400">Загрузка…</div>}
      {query.isError && (
        <div className="rounded-xl border border-error-500/30 bg-error-500/10 p-5 text-error-300">
          Не удалось загрузить маркетинг.{' '}
          <button className="underline" onClick={() => query.refetch()}>
            Повторить
          </button>
        </div>
      )}

      {!query.isLoading && !query.isError && tab === 'links' && (
        <div className="space-y-3">
          {campaigns.length === 0 && (
            <div className="rounded-xl border border-dashed border-dark-700 p-10 text-center text-dark-400">
              Реферальных ссылок пока нет
            </div>
          )}
          {campaigns.map((item) => (
            <article key={item.id} className="rounded-xl border border-dark-700 bg-dark-900/70 p-4">
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="truncate font-semibold text-dark-100">{item.name}</h2>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${item.is_active ? 'bg-success-500/15 text-success-400' : 'bg-dark-700 text-dark-400'}`}
                    >
                      {item.is_active ? 'Активна' : 'Выключена'}
                    </span>
                  </div>
                  <p className="mt-1 break-all font-mono text-xs text-dark-400">
                    {item.link || `ad_${item.code}`}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  onClick={() => copy(item.link || `ad_${item.code}`, notify)}
                >
                  Копировать
                </button>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    updateMarketingCampaign(Number(item.id), { is_active: !item.is_active }).then(
                      refresh,
                    )
                  }
                >
                  {item.is_active ? 'Выключить' : 'Включить'}
                </button>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <Metric label="Переходы" value={item.arrivals || 0} />
                <Metric label="Оплатили" value={item.paying_users || 0} />
                <Metric label="Бонус за вход" value={`${item.entry_bonus_days || 0} дн.`} />
                <Metric label="Бонус за оплату" value={`${item.payment_bonus_days || 0} дн.`} />
              </div>
            </article>
          ))}
        </div>
      )}

      {!query.isLoading && !query.isError && tab === 'promocodes' && (
        <div className="space-y-3">
          {promocodes.length === 0 && (
            <div className="rounded-xl border border-dashed border-dark-700 p-10 text-center text-dark-400">
              Промокодов пока нет
            </div>
          )}
          {promocodes.map((item) => (
            <article
              key={item.id}
              className="flex flex-wrap items-center gap-4 rounded-xl border border-dark-700 bg-dark-900/70 p-4"
            >
              <button
                className="rounded-lg bg-dark-800 px-3 py-2 font-mono font-semibold text-accent-300"
                onClick={() => copy(item.code, notify)}
              >
                {item.code}
              </button>
              <div className="min-w-[120px] flex-1 text-sm text-dark-300">
                Скидка{' '}
                <b className="text-dark-100">
                  {item.discount_type === 'percent'
                    ? `${item.discount_percent}%`
                    : `${item.discount_rub} ₽`}
                </b>
                <div className="mt-1 text-xs text-dark-500">
                  Использовано {item.used_count || 0} из {item.max_uses} · до{' '}
                  {new Date(item.expires_at).toLocaleDateString('ru-RU')}
                </div>
              </div>
              <span className={item.is_active ? 'text-success-400' : 'text-dark-500'}>
                {item.is_active ? 'Активен' : 'Выключен'}
              </span>
              <button
                className="btn-secondary"
                onClick={() =>
                  updateMarketingPromocode(Number(item.id), { is_active: !item.is_active }).then(
                    refresh,
                  )
                }
              >
                {item.is_active ? 'Выключить' : 'Включить'}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-dark-800/70 px-3 py-2">
      <div className="text-xs text-dark-500">{label}</div>
      <div className="mt-1 font-semibold text-dark-100">{value}</div>
    </div>
  );
}
