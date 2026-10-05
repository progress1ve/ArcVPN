import type { ReactNode } from 'react';

/** The admin panel's section shell, shared with the trimmed partner panel. */
export function AdminNavSection({ title, count, gradient, children }: { title: ReactNode; count: number; gradient: string; children: ReactNode }) {
  return <div className="group/card relative overflow-hidden rounded-2xl border border-dark-700/50 bg-dark-800/30 backdrop-blur-xl transition-colors duration-200 hover:border-dark-600/80 light:border-champagne-300/50 light:bg-champagne-100/40 light:hover:border-champagne-400/60">
    <div className="flex items-center gap-2.5 border-b border-dark-700/30 px-3.5 py-2.5 light:border-champagne-300/30">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg" style={{ background: gradient }}><span className="text-xs font-bold text-dark-50" aria-hidden="true">{count}</span></div>
      <h2 className="truncate text-[13px] font-semibold text-dark-100 light:text-champagne-900">{title}</h2>
    </div>
    {children}
  </div>;
}
