import { ArrowLeft, Heart, RotateCcw, Trophy, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { categoryById } from "../data/categories";
import { levelsFor } from "../data/depth";
import type { Category, Question } from "../types";
import { href } from "../utils/router";
import {
  advance, changeLevel, progress, recordOutcome, remainingByLevel, restoreSession, startSession, summarize,
  type Level, type SessionState,
} from "../utils/session";
import { clearSession, loadSession, saveSession } from "../utils/storage";
import { CategoryIcon } from "./CategoryIcon";
import { DepthMeter, DepthSelector } from "./DepthSelector";
import { OpenStep, TriviaStep } from "./QuestionSteps";
import { ProgressBar } from "./ProgressBar";
import { primary, quiet, secondary } from "./ui";

const QUIZ_LENGTH = 10;

export interface SessionViewProps {
  /** The category being played, or null for a mixed set (favorites). */
  category: Category | null;
  heading: string;
  description: string;
  pool: Question[];
  /** Keeps progress across a refresh while the tab stays open. Leave out for one-off sets. */
  persistKey?: string;
  backHref: string;
  backLabel: string;
}

/** One play-through of a set of questions: shuffled once, no repeats, depth switchable any time. */
export function SessionView({ category, heading, description, pool, persistKey, backHref, backLabel }: SessionViewProps) {
  const quiz = pool.length > 0 && pool.every((q) => q.kind === "trivia");
  const limit = quiz ? QUIZ_LENGTH : null;
  const scope = category?.id ?? "mixed";
  const byId = useMemo(() => new Map(pool.map((q) => [q.id, q])), [pool]);

  const [state, setState] = useState<SessionState>(() => {
    const saved = persistKey ? restoreSession(loadSession(persistKey), scope, pool, limit) : null;
    if (!saved) return startSession(scope, pool, { limit });
    // Reloaded on a question that was already answered: move on rather than ask it twice.
    return saved.currentId && saved.outcomes[saved.currentId] ? advance(saved, pool) : saved;
  });

  useEffect(() => {
    if (persistKey) saveSession(persistKey, state);
  }, [persistKey, state]);

  // Each new question (and the end screen) gets keyboard and screen-reader focus.
  const stage = useRef<HTMLDivElement>(null);
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    stage.current?.focus();
  }, [state.currentId, state.done]);

  if (pool.length === 0) return null;

  const question = state.currentId ? byId.get(state.currentId) : undefined;
  const prog = progress(state, pool);
  const remaining = remainingByLevel(state, pool);
  const names = levelsFor(category?.id ?? (quiz ? "trivia" : "deep"));
  const mixed = category === null;
  const levelName = (q: Question) => names[q.depth].name;

  const restart = () => {
    if (persistKey) clearSession(persistKey);
    setState(startSession(scope, pool, { limit, level: state.level }));
  };
  const onLevel = (level: Level) => setState((s) => changeLevel(s, pool, level));
  const next = () => setState((s) => advance(s, pool));
  const eyebrow = (q: Question) => (
    <>
      {mixed && <span>{categoryById(q.categoryId)?.name}</span>}
      <span className="inline-flex items-center gap-2"><DepthMeter depth={q.depth} /> {levelName(q)}</span>
      {q.kind === "trivia" && <span className="text-muted">{q.topic}</span>}
    </>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-8 sm:px-6 sm:pt-12">
      <a href={backHref} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> {backLabel}
      </a>
      <div className="mt-4 flex items-center gap-4">
        {category ? (
          <CategoryIcon category={category} size="lg" />
        ) : (
          <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-coral-500 to-plum-500 text-white shadow-md">
            <Heart className="size-8" fill="currentColor" strokeWidth={0} />
          </span>
        )}
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">{heading}</h1>
          <p className="mt-1 text-muted">{description}</p>
        </div>
      </div>

      <div className="mt-8">
        <DepthSelector categoryId={category?.id ?? (quiz ? "trivia" : "deep")} level={state.level} remaining={remaining} onChange={onLevel} />
      </div>

      <div className="mt-6">
        <ProgressBar
          current={state.done ? Math.max(prog.done, 1) : prog.done}
          total={Math.max(prog.total, 1)}
          label={state.done ? "Round complete" : `Question ${prog.done} of ${prog.total}`}
        />
      </div>

      <div ref={stage} tabIndex={-1} className="mt-6 rounded-[2rem] outline-none">
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
            onSaved={() => setState((s) => recordOutcome(s, "answered"))}
            onSkip={next} onNext={next} />
        )}
      </div>

      {category && category.id !== "trivia" && !state.done && (
        <a href={href.guess} className="mt-6 flex items-center gap-3 rounded-2xl border border-plum-100 bg-white/70 p-4 text-[15px] transition hover:border-plum-300 hover:bg-white">
          <Users aria-hidden className="size-6 shrink-0 text-plum-600" />
          <span><span className="font-bold text-plum-800">Playing with a partner?</span> <span className="text-muted">Try Guess My Answer, a two-player game on one device.</span></span>
        </a>
      )}
    </div>
  );
}

function ResultCard({ title, message, children, actions }: { title: string; message: string; children?: ReactNode; actions: ReactNode }) {
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-8 text-center shadow-lg sm:p-12">
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
  const total = s.answered + s.skipped;
  const message =
    s.percent >= 80 ? "Brilliant. You're a trivia natural." : s.percent >= 50 ? "Solid round. A rematch could push you higher." : "Every round teaches you something. Try again?";
  const stats: [string, number | string][] = [
    ["Answered", s.answered], ["Correct", s.correct], ["Incorrect", s.incorrect], ["Score", `${s.percent}%`],
  ];
  return (
    <ResultCard
      title={`You got ${s.correct} of ${total} right`}
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
      message={`You answered ${s.answered} and skipped ${s.skipped}. ${others.length ? "More questions are waiting at other levels." : "Good conversations take time."}`}
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
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 border-plum-200 bg-white px-4 text-sm font-bold text-plum-800 transition hover:border-plum-400 hover:bg-plum-50">
                {names[d].name} <span className="text-muted">{remaining[d]} left</span>
              </button>
            ))}
            {state.level !== "mix" && (
              <button type="button" onClick={() => onLevel("mix")}
                className="inline-flex min-h-11 cursor-pointer items-center rounded-full border-2 border-plum-200 bg-white px-4 text-sm font-bold text-plum-800 transition hover:border-plum-400 hover:bg-plum-50">
                Mix of all levels
              </button>
            )}
          </div>
        </div>
      )}
    </ResultCard>
  );
}
