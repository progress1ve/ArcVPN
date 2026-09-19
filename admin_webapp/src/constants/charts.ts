export const CHART_COMMON = {
  KOPEKS_DIVISOR: 100,
  GRADIENT: {
    START_OFFSET: '5%',
    END_OFFSET: '95%',
    START_OPACITY: 0.3,
    END_OPACITY: 0,
  },
  AXIS: {
    TICK_FONT_SIZE: 11,
  },
  TOOLTIP: {
    BORDER_RADIUS: '8px',
    FONT_SIZE: '12px',
  },
  STROKE_WIDTH: 2,
  GRID_DASH: '3 3',
  STALE_TIME: 60_000,
  CHART: {
    MARGIN: { top: 5, right: 10, left: 0, bottom: 5 },
  },
} as const;
