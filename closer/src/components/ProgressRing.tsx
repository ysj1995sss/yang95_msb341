/** A small ring that fills as a round is played. Decorative: the numbers beside it say the same thing. */
export function ProgressRing({ done, total, size = 36 }: { done: number; total: number; size?: number }) {
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const fraction = total > 0 ? Math.min(1, done / total) : 0;
  return (
    <svg aria-hidden width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0 -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-plum-100" />
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={circumference * (1 - fraction)}
        className={fraction >= 1 ? "stroke-emerald-500" : "stroke-plum-500"} />
    </svg>
  );
}
