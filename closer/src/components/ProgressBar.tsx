export function ProgressBar({ current, total, label }: { current: number; total: number; label: string }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm font-semibold text-muted">
        <span>{label}</span>
        <span>{Math.round((current / total) * 100)}%</span>
      </div>
      <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={total} aria-valuenow={current}
        className="h-2.5 overflow-hidden rounded-full bg-plum-100">
        <div className="h-full rounded-full bg-gradient-to-r from-plum-500 to-coral-500 transition-[width] duration-500"
          style={{ width: `${(current / total) * 100}%` }} />
      </div>
    </div>
  );
}
