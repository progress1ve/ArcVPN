import { describe, expect, it } from 'vitest';
import {
  adminDate,
  adminDateParts,
  gigabytes,
  parseAnswer,
  surveyName,
  waitingDuration,
} from './profileFormat';
describe('operator data formatting', () => {
  it('keeps comments with punctuation intact', () =>
    expect(parseAnswer('service: YouTube: не работает')).toEqual({
      label: 'Не работал нужный сервис',
      comment: 'YouTube: не работает',
    }));
  it('uses Moscow for both SQLite UTC and ISO timestamps', () => {
    expect(adminDate('2026-10-13 09:24:00')).toEqual(adminDate('2026-10-13T09:24:00Z'));
    expect(adminDate('2026-10-13T12:24:00+03:00')).toEqual(adminDate('2026-10-13T09:24:00Z'));
    expect(adminDate(null)).toBe('Нет данных');
    expect(adminDate('bad')).toBe('Нет данных');
    expect(adminDateParts('2026-10-12 23:40:00')).toEqual({ date: '13.10.2026', time: '02:40' });
    expect(adminDateParts('2026-10-13T02:40:00+03:00')).toEqual({
      date: '13.10.2026',
      time: '02:40',
    });
    expect(adminDateParts('bad')).toBeNull();
  });
  it('distinguishes a missing counter from zero', () => {
    expect(gigabytes(null)).toBe('Нет данных');
    expect(gigabytes(0)).toBe('0 ГБ');
    expect(gigabytes(1024 ** 3)).toBe('1 ГБ');
  });
  it('identifies the survey', () =>
    expect(surveyName('expired_winback')).toBe('Почему не продлил'));
  it('formats waiting time consistently in UTC without negative or invalid ages', () => {
    const now = Date.parse('2026-10-13T12:00:00Z');
    expect(waitingDuration('2026-10-12 10:00:00', now)).toBe('1 д. 2 ч.');
    expect(waitingDuration('2026-10-13T13:00:00+03:00', now)).toBe('2 ч. 0 мин.');
    expect(waitingDuration('2026-10-14', now)).toBe('меньше минуты');
    expect(waitingDuration('bad', now)).toBe('Нет данных');
  });
});
