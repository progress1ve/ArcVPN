// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnswersTab } from './AnswersTab';

const formatDate = (value: string | null) => value || '—';

describe('AnswersTab', () => {
  it('renders readable labels and preserves free-text details', () => {
    render(
      <AnswersTab
        formatDate={formatDate}
        answers={[
          {
            event_key: 'trial_day1_rating',
            answer: 'service: Не открывался YouTube',
            sent_at: '2026-09-19T12:00:00Z',
            answered_at: '2026-09-19T12:05:00Z',
          },
          {
            event_key: 'expired_winback',
            answer: 'expensive',
            sent_at: null,
            answered_at: '2026-09-21T12:03:00Z',
          },
        ]}
      />,
    );

    expect(screen.getByText('Не работал нужный сервис')).toBeTruthy();
    expect(screen.getByText('Не открывался YouTube')).toBeTruthy();
    expect(screen.getByText('Слишком дорого')).toBeTruthy();
  });

  it('renders a compact empty state', () => {
    render(<AnswersTab answers={[]} formatDate={formatDate} />);
    expect(screen.getByText('Пользователь пока не отвечал на вопросы')).toBeTruthy();
  });
});
