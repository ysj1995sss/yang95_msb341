import { ArrowRight, Minimize2, SkipForward } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import type { Countdown } from "../hooks";
import type { OpenQuestion } from "../types";
import { TimerPanel } from "./TimerPanel";

/** The question as one big card that fills the screen, for reading aloud across a table. Takes over
 *  the whole screen where the browser allows it. Arrow keys still move on; Esc closes. */
export function TableMode({ question, label, position, countdown, timerChoice, onTimerChoice, showTimer, onNext, onSkip, onClose }: {
  question: OpenQuestion;
  /** The level, e.g. "Deep", shown small above the question. */
  label: ReactNode;
  /** e.g. "Question 4 of 50". */
  position: string;
  countdown: Countdown;
  timerChoice: number;
  onTimerChoice: (seconds: number) => void;
  showTimer: boolean;
  onNext: () => void;
  onSkip: () => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDivElement>(null);

  // Escape closes it, wherever focus happens to be.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); onClose(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    const scroll = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.focus();
    // Best effort: some browsers (and iPhone Safari) won't go fullscreen, and the card still fills the page.
    void document.documentElement.requestFullscreen?.().catch(() => undefined);
    return () => {
      document.body.style.overflow = scroll;
      if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined);
      before?.focus?.();
    };
  }, []);

  return (
    <div ref={dialog} role="dialog" aria-modal="true" aria-label="Table mode" tabIndex={-1}
      className="fixed inset-0 z-50 flex flex-col overflow-y-auto bg-gradient-to-br from-plum-900 via-[#3b2690] to-plum-700 p-5 text-cream outline-none sm:p-10">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-bold uppercase tracking-wider text-onplum">
          {label} <span className="mx-1 opacity-60">·</span> {position}
        </p>
        <button type="button" onClick={onClose}
          className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full bg-white/10 px-4 font-bold text-cream hover:bg-white/20">
          <Minimize2 aria-hidden className="size-5" /> Close
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center py-8">
        <h2 key={question.id} className="animate-fade-up text-center text-4xl font-extrabold leading-tight sm:text-6xl lg:text-7xl">
          {question.text}
        </h2>
      </div>

      {showTimer && (
        <div className="mx-auto mb-6 w-full max-w-xl">
          <TimerPanel countdown={countdown} choice={timerChoice} onChoice={onTimerChoice} light />
        </div>
      )}

      <div className="mx-auto flex w-full max-w-xl flex-col-reverse gap-3 sm:flex-row sm:justify-center">
        <button type="button" onClick={onSkip}
          className="inline-flex min-h-14 cursor-pointer items-center justify-center gap-2 rounded-full bg-white/10 px-8 text-lg font-bold text-cream hover:bg-white/20">
          <SkipForward aria-hidden className="size-5" /> Skip
        </button>
        <button type="button" onClick={onNext}
          className="inline-flex min-h-14 cursor-pointer items-center justify-center gap-2 rounded-full bg-cream px-10 text-lg font-extrabold text-plum-900 shadow-lg hover:bg-white">
          Next question <ArrowRight aria-hidden className="size-5" />
        </button>
      </div>
    </div>
  );
}
