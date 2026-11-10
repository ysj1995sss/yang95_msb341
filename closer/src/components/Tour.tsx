import { ArrowLeft, ArrowRight, Check, Compass, Heart, MessageCircleHeart } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { closeTour, isReplaying, subscribeTour, tourSeen, tourSteps } from "../utils/tour";
import { primary, quiet, secondary } from "./ui";

const icons = [MessageCircleHeart, Compass, Heart];

/** Three short screens for a first visit. Shows once on the home page; "Replay the tour" on About brings it back. */
export function Tour({ onHome }: { onHome: boolean }) {
  const seen = useSyncExternalStore(subscribeTour, () => tourSeen.get());
  const replaying = useSyncExternalStore(subscribeTour, isReplaying);
  const open = replaying || (!seen && onHome);
  const [step, setStep] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setStep(0);
    const before = document.activeElement as HTMLElement | null;
    dialog.current?.focus();
    return () => before?.focus?.();
  }, [open]);

  // Escape closes the tour, and Tab stays inside it. Listened for on the whole window, so it works
  // even if something else (a page heading, say) happens to hold focus.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); closeTour(); return; }
      if (e.key !== "Tab" || !dialog.current) return;
      const focusable = [...dialog.current.querySelectorAll<HTMLElement>("button:not([disabled])")];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (!dialog.current.contains(active)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); }
      else if (e.shiftKey && (active === first || active === dialog.current)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;
  const current = tourSteps[step];
  const Icon = icons[step % icons.length];
  const last = step === tourSteps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-plum-900/70 p-4 backdrop-blur-sm sm:items-center">
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="tour-title" tabIndex={-1}
        className="w-full max-w-md rounded-[2rem] bg-surface p-7 shadow-2xl outline-none animate-fade-up sm:p-9">
        <span aria-hidden className="inline-flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-plum-600 to-coral-500 text-white shadow-md">
          <Icon className="size-7" />
        </span>
        <p className="mt-5 text-sm font-bold text-muted">Step {step + 1} of {tourSteps.length}</p>
        <h2 id="tour-title" className="mt-1 text-2xl font-extrabold tracking-tight">{current.title}</h2>
        <p className="mt-3 text-[17px] leading-relaxed text-muted">{current.text}</p>
        {current.tip && <p className="mt-3 rounded-2xl bg-plum-50 px-4 py-2.5 text-sm font-semibold text-plum-800">{current.tip}</p>}

        <div className="mt-6 flex items-center gap-2" aria-hidden>
          {tourSteps.map((_, i) => <span key={i} className={`h-2 rounded-full transition-all ${i === step ? "w-8 bg-plum-600" : "w-2 bg-plum-200"}`} />)}
        </div>

        <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
          {last ? <span /> : <button type="button" onClick={closeTour} className={quiet}>Skip tour</button>}
          <div className="flex gap-2">
            {step > 0 && (
              <button type="button" onClick={() => setStep(step - 1)} className={secondary}>
                <ArrowLeft aria-hidden className="size-5" /> Back
              </button>
            )}
            {last ? (
              <button type="button" onClick={closeTour} className={primary}>Start playing <Check aria-hidden className="size-5" /></button>
            ) : (
              <button type="button" onClick={() => setStep(step + 1)} className={primary}>Next <ArrowRight aria-hidden className="size-5" /></button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
