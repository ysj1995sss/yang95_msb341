import { Pause, Play, RotateCcw, Timer } from "lucide-react";
import type { Countdown } from "../hooks";
import { formatClock, TIMER_CHOICES, timerLabel } from "../utils/timer";

/** Pick how long, then start, pause or restart. Stays out of the way when the timer is off. */
export function TimerPanel({ countdown, choice, onChoice, light = false }: {
  countdown: Countdown;
  choice: number;
  onChoice: (seconds: number) => void;
  /** For the dark table-mode screen. */
  light?: boolean;
}) {
  const { left, running, finished, start, pause, reset } = countdown;
  const chip = (active: boolean) =>
    `inline-flex min-h-9 cursor-pointer items-center rounded-full px-3 text-sm font-bold transition ${
      active
        ? light ? "bg-cream text-plum-900" : "bg-plum-600 text-white"
        : light ? "bg-white/10 text-cream hover:bg-white/20" : "bg-plum-50 text-plum-800 hover:bg-plum-100"}`;
  const ghost = light ? "bg-white/10 text-cream hover:bg-white/20" : "bg-plum-50 text-plum-800 hover:bg-plum-100";

  return (
    <div className={light ? "text-cream" : "rounded-2xl border border-plum-100 bg-surface/80 p-4"}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`mr-1 inline-flex items-center gap-1.5 text-sm font-bold ${light ? "text-onplum" : "text-muted"}`}>
          <Timer aria-hidden className="size-4" /> Timer
        </span>
        <div role="group" aria-label="Countdown length" className="flex flex-wrap gap-1.5">
          {TIMER_CHOICES.map((s) => (
            <button key={s} type="button" aria-pressed={choice === s} onClick={() => onChoice(s)} className={chip(choice === s)}>
              {timerLabel(s)}
            </button>
          ))}
        </div>
      </div>

      {choice > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span role="timer" aria-label="Time left"
            className={`text-4xl font-extrabold tabular-nums ${finished ? "text-coral-600" : light ? "text-cream" : "text-plum-800"}`}>
            {formatClock(left)}
          </span>
          {running ? (
            <button type="button" onClick={pause} className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full px-4 font-bold ${ghost}`}>
              <Pause aria-hidden className="size-4" /> Pause
            </button>
          ) : (
            <button type="button" onClick={start} disabled={finished}
              className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full px-4 font-bold disabled:opacity-50 ${light ? "bg-cream text-plum-900" : "bg-plum-600 text-white"}`}>
              <Play aria-hidden className="size-4" /> {left < choice && left > 0 ? "Resume" : "Start"}
            </button>
          )}
          <button type="button" onClick={reset} className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full px-4 font-bold ${ghost}`}>
            <RotateCcw aria-hidden className="size-4" /> Restart
          </button>
          <p role="status" className="min-w-24 text-lg font-extrabold text-coral-600">{finished ? "Time's up!" : ""}</p>
        </div>
      )}
    </div>
  );
}
