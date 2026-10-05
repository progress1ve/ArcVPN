import {BackIcon} from '@/components/icons';
/** Pure admin page heading shared with the partner entry; no auth/API bootstrap. */
export function SectionHeading({title,description,onBack,backLabel='Назад'}:{title:string;description:string;onBack?:()=>void;backLabel?:string}) {
 return <div className="flex items-center gap-3">{onBack&&<button onClick={onBack} aria-label={backLabel} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-dark-700 bg-dark-800 transition-colors hover:border-dark-600"><BackIcon/></button>}<div><h1 className="text-xl font-bold text-dark-100">{title}</h1><p className="text-sm text-dark-400">{description}</p></div></div>;
}
