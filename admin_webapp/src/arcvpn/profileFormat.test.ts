import { describe, expect, it } from 'vitest';
import { adminDate, gigabytes, parseAnswer, surveyName } from './profileFormat';
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
  });
  it('distinguishes a missing counter from zero', () => {
    expect(gigabytes(null)).toBe('Нет данных');
    expect(gigabytes(0)).toBe('0 ГБ');
    expect(gigabytes(1024 ** 3)).toBe('1 ГБ');
  });
  it('identifies the survey', () =>
    expect(surveyName('expired_winback')).toBe('Почему не продлил'));
});
