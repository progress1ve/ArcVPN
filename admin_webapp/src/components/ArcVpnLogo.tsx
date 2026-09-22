import { cn } from '@/lib/utils';

export function ArcVpnLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 384 384"
      fill="none"
      aria-hidden="true"
      className={cn('block', className)}
    >
      <path
        fill="currentColor"
        d="M164 28c7-2 11 2 11 9v73c0 22-10 34-33 42l-66 20c-23 7-23 33 0 40l66 21c23 7 33 20 33 42v72c0 8-6 12-13 9L48 317c-25-9-36-24-36-51V118c0-27 11-42 36-51l116-39Z"
      />
      <path
        fill="currentColor"
        d="M220 28c-7-2-11 2-11 9v73c0 22 10 34 33 42l66 20c23 7 23 33 0 40l-66 21c-23 7-33 20-33 42v72c0 8 6 12 13 9l114-39c25-9 36-24 36-51V118c0-27-11-42-36-51L220 28Z"
      />
    </svg>
  );
}
