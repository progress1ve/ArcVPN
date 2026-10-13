import { BackIcon } from '@/components/icons';
/** Pure admin page heading shared with the partner entry; no auth/API bootstrap. */
export function SectionHeading({
  title,
  description,
  onBack,
  backLabel = 'Назад',
}: {
  title: string;
  description: string;
  onBack?: () => void;
  backLabel?: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      {onBack && (
        <button
          onClick={onBack}
          aria-label={backLabel}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-dark-700 bg-dark-800 transition-colors hover:border-dark-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-400"
        >
          <BackIcon />
        </button>
      )}
      <div className="min-w-0">
        <h1 className="break-words text-xl font-bold text-dark-100">{title}</h1>
        <p className="break-words text-sm text-dark-300">{description}</p>
      </div>
    </div>
  );
}
