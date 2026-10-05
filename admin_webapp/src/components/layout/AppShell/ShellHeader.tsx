import type { ReactNode } from 'react';

/** Presentational admin shell header; no authentication or API side effects. */
export function ShellHeader({ children, className = 'fixed inset-x-0 top-0 z-50 hidden border-b border-dark-800/50 bg-dark-950/95 lg:block' }: { children: ReactNode; className?: string }) {
  return <header className={className}><div className="mx-auto grid h-14 max-w-[1600px] grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 sm:px-6">{children}</div></header>;
}
