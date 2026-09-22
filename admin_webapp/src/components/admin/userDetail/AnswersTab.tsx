import type { UserLifecycleAnswer } from '../../../api/adminUsers';

interface AnswersTabProps {
  answers: UserLifecycleAnswer[];
  formatDate: (value: string | null) => string;
}

const QUESTIONS: Record<string, string> = {
  trial_day1_rating: 'Что важнее всего улучшить после первого дня?',
  day5_rating: 'Что важнее всего улучшить после пробного периода?',
  expired_winback: 'Почему не стали продлевать подписку?',
};

const ANSWERS: Record<string, string> = {
  great: 'Всё работало отлично',
  connection: 'Не подключалось или работало нестабильно',
  speed: 'Низкая скорость',
  service: 'Не работал нужный сервис',
  setup: 'Было сложно настроить',
  expensive: 'Слишком дорого',
  quality: 'Не устроило качество работы',
  competitor: 'Пользуется другим VPN',
  other: 'Другая причина',
};

function parseAnswer(rawAnswer: string) {
  const separator = rawAnswer.indexOf(':');
  const code = (separator === -1 ? rawAnswer : rawAnswer.slice(0, separator)).trim();
  const detail = separator === -1 ? '' : rawAnswer.slice(separator + 1).trim();
  return { label: ANSWERS[code] || code || 'Ответ не указан', detail };
}

export function AnswersTab({ answers, formatDate }: AnswersTabProps) {
  if (!answers.length) {
    return (
      <div className="rounded-2xl border border-dark-700/60 bg-dark-800/35 px-5 py-10 text-center">
        <p className="text-base font-medium text-dark-100">Пользователь пока не отвечал на вопросы</p>
        <p className="mt-1 text-sm text-dark-400">
          Здесь появятся ответы из опросов после триала и окончания подписки.
        </p>
      </div>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-dark-700/60 bg-dark-800/35">
      <div className="border-b border-dark-700/60 px-5 py-4">
        <h2 className="text-base font-semibold text-dark-50">Ответы пользователя</h2>
        <p className="mt-1 text-sm text-dark-400">Опросы после триала и окончания подписки</p>
      </div>
      <div className="divide-y divide-dark-700/60">
        {answers.map((item, index) => {
          const answer = parseAnswer(item.answer);
          return (
            <article key={`${item.event_key}-${item.answered_at || index}`} className="px-5 py-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm text-dark-400">
                    {QUESTIONS[item.event_key] || 'Ответ на вопрос'}
                  </p>
                  <p className="mt-1 text-base font-medium text-dark-50">{answer.label}</p>
                  {answer.detail && (
                    <p className="mt-2 rounded-lg bg-dark-900/60 px-3 py-2 text-sm text-dark-200">
                      {answer.detail}
                    </p>
                  )}
                </div>
                <time className="shrink-0 text-xs text-dark-500">
                  {formatDate(item.answered_at || item.sent_at || null)}
                </time>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
