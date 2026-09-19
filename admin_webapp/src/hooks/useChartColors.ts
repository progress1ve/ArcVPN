import { useEffect, useMemo, useState } from 'react';

import { rgbToHex } from '../utils/colorConversion';

/** CSS variable names for chart theme colors */
const CSS_VARS = {
  earnings: '--color-success-400',
  referrals: '--color-accent-400',
  grid: '--color-dark-700',
  tooltipBg: '--color-dark-800',
  tooltipBorder: '--color-dark-600',
  tick: '--color-dark-400',
  label: '--color-dark-300',
} as const;

/** Fallback hex colors (default dark theme) */
const FALLBACK: Record<keyof typeof CSS_VARS, string> = {
  earnings: '#34d399',
  referrals: '#818cf8',
  grid: '#374151',
  tooltipBg: '#1f2937',
  tooltipBorder: '#4b5563',
  tick: '#9ca3af',
  label: '#d1d5db',
};

function cssVarToHex(varName: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  if (!raw) return fallback;

  const parts = raw.split(',').map((s) => parseInt(s.trim(), 10));
  if (parts.length !== 3 || parts.some(isNaN)) return fallback;

  return rgbToHex(parts[0], parts[1], parts[2]);
}

export interface ChartColors {
  earnings: string;
  referrals: string;
  grid: string;
  tooltipBg: string;
  tooltipBorder: string;
  tick: string;
  label: string;
}

/**
 * Reads theme-aware colors from CSS custom properties for use in Recharts.
 * Returns hex values derived from the current theme's CSS variables,
 * adapting to light/dark mode and admin-customized accent colors.
 *
 * Colors are memoized and only recomputed when the document element's
 * class attribute changes (i.e. theme switch).
 */
export function useChartColors(): ChartColors {
  const [themeKey, setThemeKey] = useState(() =>
    typeof document !== 'undefined' ? document.documentElement.className : '',
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setThemeKey(document.documentElement.className);
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  const colors = useMemo<ChartColors>(
    () => ({
      earnings: cssVarToHex(CSS_VARS.earnings, FALLBACK.earnings),
      referrals: cssVarToHex(CSS_VARS.referrals, FALLBACK.referrals),
      grid: cssVarToHex(CSS_VARS.grid, FALLBACK.grid),
      tooltipBg: cssVarToHex(CSS_VARS.tooltipBg, FALLBACK.tooltipBg),
      tooltipBorder: cssVarToHex(CSS_VARS.tooltipBorder, FALLBACK.tooltipBorder),
      tick: cssVarToHex(CSS_VARS.tick, FALLBACK.tick),
      label: cssVarToHex(CSS_VARS.label, FALLBACK.label),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [themeKey],
  );

  return colors;
}
