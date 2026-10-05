// Small, accessible building blocks for the whole app (spec 009 visual system).
"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { createContext, useCallback, useContext, useId, useState, type ReactNode } from "react";

export type Tone = "neutral" | "verified" | "review" | "blocked" | "primary";

const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ");

const buttonBase =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-control)] px-4 text-[15px] font-semibold " +
  "transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer";
const buttonVariants = {
  primary: "bg-primary text-on-primary hover:bg-primary-hover",
  secondary: "border border-line-strong bg-paper text-ink hover:bg-canvas",
  ghost: "text-primary hover:bg-primary-soft",
  danger: "border border-blocked/40 bg-paper text-blocked hover:bg-blocked-soft",
};

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof buttonVariants;
  busy?: boolean;
};

export function Button({ variant = "secondary", busy, className, children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={cx(buttonBase, buttonVariants[variant], className)}
    >
      {busy && <Loader2 aria-hidden className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export function LinkButton({
  href, variant = "secondary", className, children, external,
}: { href: string; variant?: keyof typeof buttonVariants; className?: string; children: ReactNode; external?: boolean }) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cx(buttonBase, buttonVariants[variant], className)}>
        {children}
      </a>
    );
  }
  return <Link href={href} className={cx(buttonBase, buttonVariants[variant], className)}>{children}</Link>;
}

/** A file download. A plain link, never next/link: client navigation would prefetch the file. */
export function DownloadLink({ href, variant = "secondary", className, children }: {
  href: string; variant?: keyof typeof buttonVariants; className?: string; children: ReactNode;
}) {
  return <a href={href} download className={cx(buttonBase, buttonVariants[variant], className)}>{children}</a>;
}

export function Card({ children, className, as: As = "section", ...rest }: {
  children: ReactNode; className?: string; as?: "section" | "div" | "article"; "aria-labelledby"?: string;
}) {
  return (
    <As {...rest} className={cx("rounded-[var(--radius-card)] border border-line bg-paper p-5 sm:p-6", className)}>
      {children}
    </As>
  );
}

const chipTones: Record<Tone, string> = {
  neutral: "bg-canvas text-muted border-line",
  verified: "bg-verified-soft text-verified border-verified/30",
  review: "bg-review-soft text-review border-review/30",
  blocked: "bg-blocked-soft text-blocked border-blocked/30",
  primary: "bg-primary-soft text-primary border-primary/30",
};

export function Chip({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[13px] font-semibold whitespace-nowrap", chipTones[tone])}>
      {children}
    </span>
  );
}

export function toneOf(value: string | undefined | null): Tone {
  if (value === "verified" || value === "review" || value === "blocked" || value === "primary") return value;
  if (value === "action") return "primary";
  return "neutral";
}

const alertTones: Record<Tone, string> = {
  neutral: "border-line bg-paper",
  verified: "border-verified/30 bg-verified-soft",
  review: "border-review/30 bg-review-soft",
  blocked: "border-blocked/30 bg-blocked-soft",
  primary: "border-primary/30 bg-primary-soft",
};

export function Alert({ tone = "neutral", title, children, role }: {
  tone?: Tone; title?: ReactNode; children?: ReactNode; role?: "alert" | "status";
}) {
  return (
    <div role={role} className={cx("rounded-[var(--radius-card)] border-l-4 p-4", alertTones[tone])}>
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={cx("text-[15px]", title ? "mt-1" : undefined)}>{children}</div>}
    </div>
  );
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[28px] leading-tight font-semibold sm:text-[32px]">{title}</h1>
        {description && <p className="mt-1 max-w-[65ch] text-muted">{description}</p>}
      </div>
      {action}
    </header>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-muted">
      <Loader2 aria-hidden className="size-5 animate-spin" /> {label}…
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <Alert tone="blocked" role="alert" title="Something went wrong">
      <p>{error.message}</p>
      {retry && <Button className="mt-3" onClick={retry}>Try again</Button>}
    </Alert>
  );
}

// --- form fields: always a visible label, help under it, the error next to the field ---

type FieldProps = { label: string; help?: string; error?: string; className?: string };

function FieldShell({ id, label, help, error, className, children }: FieldProps & { id: string; children: ReactNode }) {
  return (
    <div className={cx("flex flex-col gap-1", className)}>
      <label htmlFor={id} className="text-[15px] font-semibold">{label}</label>
      {help && <p id={`${id}-help`} className="text-[14px] text-muted">{help}</p>}
      {children}
      {error && <p id={`${id}-error`} className="text-[14px] font-semibold text-blocked">{error}</p>}
    </div>
  );
}

const control =
  "w-full rounded-[var(--radius-control)] border border-line-strong bg-paper px-3 py-2.5 text-[16px] " +
  "placeholder:text-muted/70 aria-[invalid=true]:border-blocked";

export function TextField({ label, help, error, className, ...rest }: FieldProps & React.InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} help={help} error={error} className={className}>
      <input id={id} {...rest} aria-invalid={Boolean(error)}
        aria-describedby={cx(help && `${id}-help`, error && `${id}-error`) || undefined} className={cx(control, "min-h-11")} />
    </FieldShell>
  );
}

export function TextArea({ label, help, error, className, ...rest }: FieldProps & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} help={help} error={error} className={className}>
      <textarea id={id} {...rest} aria-invalid={Boolean(error)}
        aria-describedby={cx(help && `${id}-help`, error && `${id}-error`) || undefined} className={control} />
    </FieldShell>
  );
}

export function SelectField({ label, help, error, className, options, ...rest }: FieldProps &
  React.SelectHTMLAttributes<HTMLSelectElement> & { options: Array<{ value: string; label: string }> }) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} help={help} error={error} className={className}>
      <select id={id} {...rest} aria-invalid={Boolean(error)} className={cx(control, "min-h-11")}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </FieldShell>
  );
}

export function RadioGroup<T extends string>({ legend, help, value, options, onChange, name }: {
  legend: string; help?: string; value: T; name: string;
  options: Array<{ value: T; label: string }>; onChange: (value: T) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-[15px] font-semibold">{legend}</legend>
      {help && <p className="text-[14px] text-muted">{help}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.value}
            className={cx("flex min-h-11 cursor-pointer items-center gap-2 rounded-[var(--radius-control)] border px-3",
              value === o.value ? "border-primary bg-primary-soft" : "border-line-strong bg-paper")}>
            <input type="radio" name={name} value={o.value} checked={value === o.value}
              onChange={() => onChange(o.value)} className="accent-[var(--color-primary)]" />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function Checkbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex min-h-11 cursor-pointer items-center gap-2">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
        className="size-4 accent-[var(--color-primary)]" />
      {label}
    </label>
  );
}

// --- toasts: one polite live region ---

const ToastContext = createContext<(message: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Array<{ id: number; text: string }>>([]);
  const push = useCallback((text: string) => {
    const id = Date.now() + Math.random();
    setMessages((m) => [...m, { id, text }]);
    setTimeout(() => setMessages((m) => m.filter((x) => x.id !== id)), 4000);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-24 z-50 flex flex-col items-center gap-2 sm:bottom-6">
        {messages.map((m) => (
          <div key={m.id} className="rounded-[var(--radius-card)] bg-inverse px-4 py-2.5 text-[15px] text-on-inverse">{m.text}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
export { cx };
