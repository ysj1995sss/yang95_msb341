import { Dices } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { GameShell, Pills, panel } from "../../components/games/kit";
import { primary } from "../../components/ui";
import { gameById } from "../../data/games";
import { budgetLabels, budgets, dateIdeas, moodLabels, moods, type Budget, type DateIdea, type Mood } from "../../data/games/dates";
import { createDeck } from "../../utils/games/deck";

const budgetOptions = budgets.map((value) => ({ value, label: budgetLabels[value] }));
const moodOptions = moods.map((value) => ({ value, label: moodLabels[value] }));

const reducedMotion = () => typeof window !== "undefined" && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

/** Filter by budget and mood, spin, and land on a date idea. With nothing ticked, everything is in. */
export function DateNightRoulette() {
  const [budget, setBudget] = useState<Budget[]>([]);
  const [mood, setMood] = useState<Mood[]>([]);
  const [idea, setIdea] = useState<DateIdea | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [flicker, setFlicker] = useState("");
  const timer = useRef<number | undefined>(undefined);

  const pool = useMemo(
    () => dateIdeas.filter((d) => (budget.length === 0 || budget.includes(d.budget)) && (mood.length === 0 || mood.includes(d.mood))),
    [budget, mood],
  );
  const deck = useMemo(() => (pool.length ? createDeck(pool) : null), [pool]);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const spin = () => {
    if (!deck || spinning) return;
    const landed = deck.draw();
    if (reducedMotion()) { setIdea(landed); return; }
    setSpinning(true);
    let tick = 0;
    const step = () => {
      tick += 1;
      if (tick >= 12) { setFlicker(""); setIdea(landed); setSpinning(false); return; }
      setFlicker(pool[Math.floor(Math.random() * pool.length)]!.text);
      timer.current = window.setTimeout(step, 60 + tick * 14);
    };
    step();
  };
  const filters = (next: () => void) => { window.clearTimeout(timer.current); setSpinning(false); setFlicker(""); next(); };

  return (
    <GameShell game={gameById("date-night-roulette")!} focusKey="roulette">
      <div className={panel}>
        <div className="grid gap-5 sm:grid-cols-2">
          <Pills label="Budget" options={budgetOptions} value={budget} onChange={(v) => filters(() => { setBudget(v); setIdea(null); })} />
          <Pills label="Mood" options={moodOptions} value={mood} onChange={(v) => filters(() => { setMood(v); setIdea(null); })} />
        </div>
        <p className="mt-3 text-sm text-muted">
          {pool.length ? `${pool.length} ${pool.length === 1 ? "idea fits" : "ideas fit"}. Tick nothing to include everything.` : "Nothing fits that mix. Untick something."}
        </p>
        <div className="mt-5 flex min-h-48 flex-col items-center justify-center rounded-3xl bg-plum-50 p-6 text-center">
          {spinning ? (
            <p aria-hidden className="text-2xl font-extrabold leading-tight text-plum-700 dark:text-onplum-soft sm:text-3xl">{flicker}</p>
          ) : idea ? (
            <div role="status">
              <p className="text-2xl font-extrabold leading-tight sm:text-3xl">{idea.text}</p>
              <p className="mt-3 text-sm font-bold text-plum-700 dark:text-onplum-soft">{budgetLabels[idea.budget]} · {moodLabels[idea.mood]}</p>
            </div>
          ) : (
            <p className="text-lg text-muted">Press Spin to land on tonight's idea.</p>
          )}
        </div>
        <button type="button" onClick={spin} disabled={!deck || spinning} className={`${primary} mt-5 w-full sm:w-auto`}>
          <Dices aria-hidden className="size-5" /> {idea ? "Spin again" : "Spin"}
        </button>
      </div>
    </GameShell>
  );
}
