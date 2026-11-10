import { ArrowLeft, Heart, Maximize2, RotateCcw, Trophy } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { levelsFor } from "../data/depth";
import { sourceLabel } from "../data/lookup";
import { QUIZ_LENGTH } from "../data/playSets";
import { useCountdown, useSetting, useShortcuts, useSwipe } from "../hooks";
import type { Category, Question } from "../types";
import { href } from "../utils/router";
import { saveLastPlayed } from "../utils/resume";
import {
  advance, changeLevel, discuss, progress, recordOutcome, remainingByLevel, restoreSession, resultTitle, startSession, summarize,
  type Level, type SessionState,
} from "../utils/session";
import { clearSession, favorites, loadSession, saveSession } from "../utils/storage";
import { timerSetting } from "../utils/timer";
import { CategoryIcon } from "./CategoryIcon";
import { DepthMeter, DepthSelector } from "./DepthSelector";
import { OpenStep, TriviaStep } from "./QuestionSteps";
import { ProgressBar } from "./ProgressBar";
import { TableMode } from "./TableMode";
import { TimerPanel } from "./TimerPanel";
import { primary, quiet, secondary } from "./ui";

export interface SessionViewProps {
  /** The category being played, or null for a mixed set (surprise, packs, favorites, your own questions). */
  category: Category | null;
  heading: string;
  description: string;
  pool: Question[];
  /** Quiz length for trivia. Leave out for the default (10, or fewer if the pool is smaller). */
  limit?: number | null;
  /** Keeps progress across refreshes and visits. Leave out for one-off sets. */
  persistKey?: string;
  backHref: string;
  backLabel: string;
  /** The tile beside the heading for a mixed set. */
  icon?: ReactNode;
  /** Shown between the heading and the depth selector, e.g. the trivia topic picker. */
  beforeDepth?: ReactNode;
  /** Offer the optional countdown (party games and debates). */
  timer?: boolean;
}

const kbd = "rounded-md border border-plum-200 bg-surface px-1.5 py-0.5 text-xs font-bold text-plum-800";

/** One play-through of a set of questions: shuffled once, no repeats, depth switchable any time. */
export function SessionView({ category, heading, description, pool, limit: limitProp, persistKey, backHref, backLabel, icon, beforeDepth, timer = false }: SessionViewProps) {
  const quiz = pool.length > 0 && pool.every((q) => q.kind === "trivia");
  const limit = limitProp !== undefined ? limitProp : quiz ? Math.min(QUIZ_LENGTH, pool.length) : null;
  const scope = category?.id ?? "mixed";
  const byId = useMemo(() => new Map(pool.map((q) => [q.id, q])), [pool]);

  const [state, setState] = useState<SessionState>(() => {
    const saved = persistKey ? restoreSession(loadSession(persistKey), scope, pool, limit) : null;
    if (!saved) return startSession(scope, pool, { limit });
    // Reloaded on a question that was already answered: move on rather than ask it twice.
    return saved.currentId && saved.outcomes[saved.currentId] ? advance(saved, pool) : saved;
  });

  // Progress is kept as it changes, and the set counts as "last played" once the person has done something in it.
  useEffect(() => {
    if (!persistKey) return;
    saveSession(persistKey, state);
    if (Object.keys(state.outcomes).length > 0) saveLastPlayed(persistKey);
  }, [persistKey, state]);

  // Each new question (and the end screen) gets keyboard and screen-reader focus.
  const stage = useRef<HTMLDivElement>(null);
  const firstRender = useRef(true);
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    // Not while a full-screen dialog (table mode) is open: focus belongs to it.
    if (document.querySelector('[role="dialog"][aria-modal="true"]')) return;
    // Someone switching depth with the arrow keys keeps focus on the selector, so they can keep going;
    // screen readers are told what the new question is instead.
    if (document.activeElement?.closest("[data-depth-selector]")) {
      const shown = state.currentId ? byId.get(state.currentId) : undefined;
      setAnnouncement(shown ? `Now showing: ${shown.text}` : "Round complete");
      return;
    }
    stage.current?.focus();
  }, [state.currentId, state.done, byId]);

  const question = state.currentId ? byId.get(state.currentId) : undefined;
  const isOpen = question?.kind === "open";

  const [table, setTable] = useState(false);
  useEffect(() => { if (!isOpen) setTable(false); }, [isOpen]);

  const timerChoice = useSetting(timerSetting);
  const countdown = useCountdown(timer && isOpen ? timerChoice : 0, state.currentId);

  const next = () => setState((s) => advance(s, pool));
  const talked = () => setState((s) => discuss(s, pool));

  useShortcuts(
    {
      next: isOpen ? talked : undefined,
      skip: isOpen ? next : undefined,
      favorite: question ? () => favorites.toggle(question.id) : undefined,
      table: isOpen ? () => setTable((t) => !t) : undefined,
      speak: () => document.querySelector<HTMLButtonElement>("[data-speak]")?.click(),
    },
    !state.done && !!question,
  );
  const swipe = useSwipe((direction) => (direction === "left" ? talked() : next()), isOpen && !table);

  if (pool.length === 0) return null;

  const prog = progress(state, pool);
  const remaining = remainingByLevel(state, pool);
  const names = levelsFor(category?.id ?? (quiz ? "trivia" : "deep"));
  const mixed = category === null;
  const levelName = (q: Question) => levelsFor(q.categoryId)[q.depth].name;

  const restart = () => {
    if (persistKey) clearSession(persistKey);
    setState(startSession(scope, pool, { limit, level: state.level }));
  };
  const onLevel = (level: Level) => setState((s) => changeLevel(s, pool, level));
  const eyebrow = (q: Question) => (
    <>
      {mixed && sourceLabel(q) && <span>{sourceLabel(q)}</span>}
      <span className="inline-flex items-center gap-2"><DepthMeter depth={q.depth} /> {levelName(q)}</span>
      {q.kind === "trivia" && <span className="text-muted">{q.topic}</span>}
    </>
  );
  const position = state.done ? "Round complete" : `Question ${prog.done} of ${prog.total}`;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-8 sm:px-6 sm:pt-12">
      <a href={backHref} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> {backLabel}
      </a>
      <div className="mt-4 flex items-center gap-4">
        {category ? (
          <CategoryIcon category={category} size="lg" />
        ) : (
          icon ?? (
            <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-coral-500 to-plum-500 text-white shadow-md">
              <Heart className="size-8" fill="currentColor" strokeWidth={0} />
            </span>
          )
        )}
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">{heading}</h1>
          <p className="mt-1 text-muted">{description}</p>
        </div>
      </div>

      {beforeDepth}

      <p role="status" className="sr-only">{announcement}</p>

      <div className="mt-8">
        <DepthSelector categoryId={category?.id ?? (quiz ? "trivia" : "deep")} level={state.level} remaining={remaining} onChange={onLevel} />
      </div>

      <div className="mt-6">
        <ProgressBar
          current={state.done ? Math.max(prog.done, 1) : prog.done}
          total={Math.max(prog.total, 1)}
          label={position}
        />
      </div>

      {isOpen && !state.done && (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <button type="button" onClick={() => setTable(true)}
            className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 border-plum-200 bg-surface px-4 text-sm font-bold text-plum-800 transition hover:border-plum-300 hover:bg-plum-50">
            <Maximize2 aria-hidden className="size-4" /> Table mode
          </button>
          <p className="hidden text-sm text-muted sm:block">
            <kbd className={kbd}>←</kbd> skip <span aria-hidden>·</span> <kbd className={kbd}>→</kbd> next <span aria-hidden>·</span> <kbd className={kbd}>F</kbd> favorite <span aria-hidden>·</span> <kbd className={kbd}>T</kbd> table mode <span aria-hidden>·</span> <kbd className={kbd}>R</kbd> read aloud
          </p>
          <p className="text-sm text-muted sm:hidden">Swipe the card: left for next, right to skip.</p>
        </div>
      )}

      {timer && isOpen && !state.done && (
        <div className="mt-4">
          <TimerPanel countdown={countdown} choice={timerChoice} onChoice={(s) => timerSetting.set(s)} />
        </div>
      )}

      <div ref={stage} tabIndex={-1} {...swipe} className="mt-6 touch-pan-y rounded-[2rem] outline-none">
        {state.done || !question ? (
          quiz ? (
            <QuizResults state={state} onRestart={restart} backHref={backHref} backLabel={backLabel} />
          ) : (
            <Completion state={state} remaining={remaining} names={names} onLevel={onLevel} onRestart={restart}
              backHref={backHref} backLabel={backLabel} />
          )
        ) : question.kind === "trivia" ? (
          <TriviaStep key={question.id} question={question} eyebrow={eyebrow(question)} isLast={prog.done >= prog.total}
            onSubmitted={(correct) => setState((s) => recordOutcome(s, correct ? "correct" : "incorrect"))}
            onSkip={next} onNext={next} />
        ) : (
          <OpenStep key={question.id} question={question} eyebrow={eyebrow(question)} isLast={prog.done >= prog.total}
            onSkip={next} onNext={talked} />
        )}
      </div>

      {table && question?.kind === "open" && (
        <TableMode question={question} label={levelName(question)} position={position} countdown={countdown}
          timerChoice={timerChoice} onTimerChoice={(s) => timerSetting.set(s)} showTimer={timer}
          onNext={talked} onSkip={next} onClose={() => setTable(false)} />
      )}

      {persistKey && !state.done && state.seen.length > 1 && (
        <div className="mt-4 flex justify-center">
          <button type="button" className={quiet}
            onClick={() => { if (window.confirm("Start over with a fresh shuffle? Your progress in this round will be cleared.")) restart(); }}>
            <RotateCcw aria-hidden className="size-4" /> Start over
          </button>
        </div>
      )}

      {category && category.id !== "trivia" && !state.done && (
        <a href={href.guess} className="mt-6 flex items-center gap-3 rounded-2xl border border-plum-100 bg-surface/70 p-4 text-[15px] transition hover:border-plum-300 hover:bg-surface">
          <Trophy aria-hidden className="size-6 shrink-0 text-plum-600 dark:text-onplum-soft" />
          <span><span className="font-bold text-plum-800">Playing with a partner?</span> <span className="text-muted">Try Guess My Answer, a game for 2 to 6 players on one device.</span></span>
        </a>
      )}
    </div>
  );
}

function ResultCard({ title, message, children, actions }: { title: string; message: string; children?: ReactNode; actions: ReactNode }) {
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{title}</h2>
      <p className="mx-auto mt-3 max-w-md text-lg text-muted">{message}</p>
      {children}
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">{actions}</div>
    </div>
  );
}

/** Trivia finished: the numbers, then play again or leave. */
function QuizResults({ state, onRestart, backHref, backLabel }: { state: SessionState; onRestart: () => void; backHref: string; backLabel: string }) {
  const s = summarize(state);
  const message =
    s.percent >= 80 ? "Brilliant. You're a trivia natural." : s.percent >= 50 ? "Solid round. A rematch could push you higher." : "Every round teaches you something. Try again?";
  const stats: [string, number | string][] = [
    ["Answered", s.answered], ["Correct", s.correct], ["Incorrect", s.incorrect], ["Score", `${s.percent}%`],
  ];
  return (
    <ResultCard
      title={resultTitle(s)}
      message={message}
      actions={
        <>
          <button type="button" onClick={onRestart} className={primary}><RotateCcw aria-hidden className="size-5" /> Play again</button>
          <a href={backHref} className={secondary}>{backLabel === "Back to categories" ? "Return to categories" : backLabel}</a>
        </>
      }
    >
      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-plum-50 p-4">
            <dd className="text-3xl font-extrabold text-plum-800">{value}</dd>
            <dt className="text-sm font-semibold text-muted">{label}</dt>
          </div>
        ))}
      </dl>
      {s.skipped > 0 && <p className="mt-3 text-sm text-muted">{`You skipped ${s.skipped}. Skipped questions aren't scored.`}</p>}
    </ResultCard>
  );
}

/** A conversation set (or one depth of it) is used up. */
function Completion({ state, remaining, names, onLevel, onRestart, backHref, backLabel }: {
  state: SessionState;
  remaining: Record<1 | 2 | 3 | 4, number>;
  names: ReturnType<typeof levelsFor>;
  onLevel: (level: Level) => void;
  onRestart: () => void;
  backHref: string;
  backLabel: string;
}) {
  const s = summarize(state);
  const atLevel = state.level === "mix" ? null : names[state.level].name;
  const others = ([1, 2, 3, 4] as const).filter((d) => remaining[d] > 0);
  return (
    <ResultCard
      title={atLevel ? `You've finished ${atLevel}` : "You've been through them all"}
      message={`You talked through ${s.answered} and skipped ${s.skipped}. ${others.length ? "More questions are waiting at other levels." : "Good conversations take time."}`}
      actions={
        <>
          <button type="button" onClick={onRestart} className={primary}><RotateCcw aria-hidden className="size-5" /> Start over with a fresh shuffle</button>
          <a href={backHref} className={secondary}>{backLabel}</a>
        </>
      }
    >
      {others.length > 0 && (
        <div className="mt-6">
          <p className="text-sm font-semibold text-muted">Keep going at another level</p>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            {others.map((d) => (
              <button key={d} type="button" onClick={() => onLevel(d)}
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 border-plum-200 bg-surface px-4 text-sm font-bold text-plum-800 transition hover:border-plum-400 hover:bg-plum-50">
                {names[d].name} <span className="text-muted">{remaining[d]} left</span>
              </button>
            ))}
            {state.level !== "mix" && (
              <button type="button" onClick={() => onLevel("mix")}
                className="inline-flex min-h-11 cursor-pointer items-center rounded-full border-2 border-plum-200 bg-surface px-4 text-sm font-bold text-plum-800 transition hover:border-plum-400 hover:bg-plum-50">
                Mix of all levels
              </button>
            )}
          </div>
        </div>
      )}
    </ResultCard>
  );
}
