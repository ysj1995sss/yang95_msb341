import type { LucideIcon } from "lucide-react";
import { useId } from "react";

const chip = (on: boolean) =>
  `inline-flex min-h-12 cursor-pointer items-center gap-2.5 rounded-2xl border-2 px-3.5 py-2 text-[15px] font-bold leading-tight transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${
    on ? "border-plum-600 bg-plum-600 text-white" : "border-plum-100 bg-surface text-plum-800 hover:border-plum-300"}`;

/** One question on a setup screen, answered by picking one chip. */
export function SetupChoice<T extends string | number>({ legend, hint, options, value, onChange, className }: {
  legend: string; hint?: string; options: readonly { id: T; label: string; icon?: LucideIcon }[]; value: T; onChange: (id: T) => void; className: string;
}) {
  const name = useId();
  return (
    <fieldset>
      <legend className="text-sm font-bold text-muted">{legend}</legend>
      <div className={`mt-2 ${className}`}>
        {options.map((o) => (
          <label key={o.id} className={chip(o.id === value)}>
            <input type="radio" name={name} checked={o.id === value} onChange={() => onChange(o.id)} className="sr-only" />
            {o.icon && <o.icon aria-hidden className="size-5 shrink-0 max-[419px]:hidden" />}
            <span className="min-w-0">{o.label}</span>
          </label>
        ))}
      </div>
      {hint && <p className="mt-2 text-sm text-muted">{hint}</p>}
    </fieldset>
  );
}
