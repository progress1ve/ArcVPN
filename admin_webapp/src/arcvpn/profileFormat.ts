export const answerNames: Record<string, string> = {
  great: 'Всё отлично',
  connection: 'Проблема подключения',
  speed: 'Низкая скорость',
  service: 'Не работал нужный сервис',
  setup: 'Сложно настроить',
  other: 'Другое',
  expensive: 'Дорого',
  quality: 'Качество VPN',
  competitor: 'Выбрал другой VPN',
};
export function parseAnswer(value: string) {
  const [code, ...parts] = value.split(':');
  return { label: answerNames[code.trim()] || code.trim(), comment: parts.join(':').trim() };
}
export function adminDate(value?: string | null) {
  if (!value) return 'Нет данных';
  let normalized = value.trim().replace(' ', 'T');
  if (!/([zZ]|[+-]\d\d:\d\d)$/.test(normalized)) normalized += 'Z';
  const date = new Date(normalized);
  return Number.isNaN(date.getTime())
    ? 'Нет данных'
    : date.toLocaleString('ru-RU', {
        timeZone: 'Europe/Moscow',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
}
export const rubles = (value: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 2,
  }).format(value);
export const gigabytes = (value: number | null | undefined) =>
  value == null
    ? 'Нет данных'
    : `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value / 1024 ** 3)} ГБ`;
export const surveyName = (event: string) =>
  event === 'expired_winback'
    ? 'Почему не продлил'
    : event === 'trial_day1_rating'
      ? 'Первый день триала'
      : event === 'day5_rating'
        ? 'Оценка VPN'
        : event;
export const supportStatus: Record<string, string> = {
  open: 'Открыт',
  pending: 'Ожидает менеджера',
  answered: 'Ответ отправлен',
  closed: 'Закрыт',
};
