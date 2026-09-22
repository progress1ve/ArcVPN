import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminProfitApi } from '@/api/adminProfit';
import { BackIcon } from '@/components/icons';

const categories: Record<string, string> = {
  hosting: 'Хостинг',
  cdn: 'CDN',
  advertising: 'Реклама',
  other: 'Прочее',
};

const money = (value: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 2 }).format(value || 0);

const currentMonth = () => new Date().toISOString().slice(0, 7);
const today = () => new Date().toISOString().slice(0, 10);

export default function AdminProfit() {
  const queryClient = useQueryClient();
  const [month, setMonth] = useState(currentMonth);
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('hosting');
  const [incurredOn, setIncurredOn] = useState(today);
  const [recurring, setRecurring] = useState(true);
  const report = useQuery({ queryKey: ['admin-profit', month], queryFn: () => adminProfitApi.get(month) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['admin-profit'] });
  const createExpense = useMutation({ mutationFn: adminProfitApi.create, onSuccess: refresh });
  const removeExpense = useMutation({ mutationFn: adminProfitApi.remove, onSuccess: refresh });

  const chartMax = useMemo(
    () => Math.max(1, ...(report.data?.monthly || []).flatMap((item) => [item.recognized_revenue_rub, item.expenses_rub])),
    [report.data],
  );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const amountRub = Number(amount.replace(',', '.'));
    if (!title.trim() || !Number.isFinite(amountRub) || amountRub <= 0) return;
    createExpense.mutate({
      title: title.trim(), category, amount_rub: amountRub, incurred_on: incurredOn,
      recurring_monthly: recurring, note: null,
    });
    setTitle('');
    setAmount('');
  };

  if (report.isLoading) return <div className="card h-64 animate-pulse" />;
  if (report.isError || !report.data) return <div className="card text-error-400">Не удалось загрузить отчёт о прибыли.</div>;
  const { summary, expenses, monthly } = report.data;

  return (
    <div className="animate-fade-in space-y-6 pb-16">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/admin" className="flex h-10 w-10 items-center justify-center rounded-xl border border-dark-700 bg-dark-800"><BackIcon /></Link>
          <div><h1 className="text-2xl font-bold text-dark-50">Прибыль</h1><p className="text-sm text-dark-400">Помесячное признание выручки и операционные расходы</p></div>
        </div>
        <label className="text-xs text-dark-400">Месяц<input aria-label="Месяц отчёта" type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="ml-3 rounded-xl border border-dark-700 bg-dark-900 px-3 py-2 text-sm text-dark-100" /></label>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Доход за месяц" value={money(summary.month_revenue_rub)} tone="success" />
        <Metric label="Расходы" value={money(summary.month_expenses_rub)} tone="warning" />
        <Metric label="Чистая прибыль" value={money(summary.month_net_rub)} tone={summary.month_net_rub >= 0 ? 'accent' : 'error'} />
      </div>

      <section className="card">
        <h2 className="mb-1 text-lg font-semibold text-dark-100">Доход и расходы за 12 месяцев</h2>
        <p className="mb-5 text-xs text-dark-400">Платёж распределяется поровну между месяцами оплаченного срока подписки.</p>
        <div className="flex h-56 items-end gap-2 overflow-x-auto border-b border-dark-700 pb-1">
          {monthly.map((item) => <div key={item.month} className="flex min-w-14 flex-1 flex-col items-center gap-1" title={`${item.month}: доход ${money(item.recognized_revenue_rub)}, расходы ${money(item.expenses_rub)}`}>
            <div className="flex h-44 items-end gap-1">
              <div className="w-3 rounded-t bg-success-500" style={{ height: `${Math.max(2, item.recognized_revenue_rub / chartMax * 100)}%` }} />
              <div className="w-3 rounded-t bg-warning-500" style={{ height: `${Math.max(2, item.expenses_rub / chartMax * 100)}%` }} />
            </div>
            <span className="text-[10px] text-dark-500">{item.month.slice(5)}</span>
          </div>)}
        </div>
        <div className="mt-3 flex gap-5 text-xs text-dark-400"><span><i className="mr-2 inline-block h-2 w-2 rounded-full bg-success-500" />Доход</span><span><i className="mr-2 inline-block h-2 w-2 rounded-full bg-warning-500" />Расходы</span></div>
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(300px,0.8fr)_1.2fr]">
        <form className="card space-y-4" onSubmit={submit}>
          <h2 className="text-lg font-semibold text-dark-100">Добавить расход</h2>
          <Field label="Название"><input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Например, VPS Германия" className="input" /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Сумма, ₽"><input required inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} className="input" /></Field><Field label="Категория"><select value={category} onChange={(e) => setCategory(e.target.value)} className="input">{Object.entries(categories).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field></div>
          <Field label="Дата"><input required type="date" value={incurredOn} onChange={(e) => setIncurredOn(e.target.value)} className="input" /></Field>
          <label className="flex items-start gap-3 text-sm text-dark-200"><input type="checkbox" checked={recurring} onChange={(e) => setRecurring(e.target.checked)} className="mt-1" /><span>Повторять ежемесячно<small className="block text-dark-500">Для постоянного хостинга или CDN</small></span></label>
          <button disabled={createExpense.isPending} className="w-full rounded-xl bg-accent-500 px-4 py-3 font-semibold text-white disabled:opacity-50">{createExpense.isPending ? 'Сохраняем…' : 'Добавить расход'}</button>
        </form>

        <section className="card min-w-0">
          <h2 className="mb-4 text-lg font-semibold text-dark-100">Все расходы</h2>
          <div className="divide-y divide-dark-700">{expenses.length === 0 ? <p className="py-8 text-center text-dark-500">Расходов ещё нет</p> : expenses.map((expense) => <div key={expense.id} className="flex items-center gap-3 py-3">
            <div className="min-w-0 flex-1"><p className="truncate font-medium text-dark-100">{expense.title}</p><p className="text-xs text-dark-500">{categories[expense.category] || 'Прочее'} · {expense.incurred_on}{expense.recurring_monthly ? ' · ежемесячно' : ''}</p></div>
            <strong className="text-sm text-dark-100">{money(expense.amount_rub)}</strong>
            <button aria-label={`Удалить ${expense.title}`} onClick={() => window.confirm(`Удалить расход «${expense.title}»?`) && removeExpense.mutate(expense.id)} className="rounded-lg px-2 py-1 text-xs text-error-400 hover:bg-error-500/10">Удалить</button>
          </div>)}</div>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  const colors: Record<string, string> = { success: 'text-success-400', warning: 'text-warning-400', accent: 'text-accent-300', error: 'text-error-400' };
  return <div className="card"><p className="text-xs text-dark-400">{label}</p><p className={`mt-2 text-2xl font-bold ${colors[tone]}`}>{value}</p></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-xs text-dark-400"><span className="mb-1.5 block">{label}</span>{children}</label>;
}
