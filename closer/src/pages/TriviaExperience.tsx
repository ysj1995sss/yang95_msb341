import {
  ArrowLeft, ArrowRight, Brain, Check, Clapperboard, Cpu, FlaskConical, Globe, Landmark, Music, Palette, Puzzle, RotateCcw,
  Shapes, SlidersHorizontal, Swords, Trophy, User, Users, Utensils, X, type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { CategoryIcon } from "../components/CategoryIcon";
import { DepthMeter } from "../components/DepthSelector";
import { ProgressBar } from "../components/ProgressBar";
import { TriviaStep } from "../components/QuestionSteps";
import { SetupChoice } from "../components/SetupChoice";
import { tintClass } from "../components/tint";
import { topicSetting } from "../utils/triviaTopicSetting";
import { primary, quiet, secondary } from "../components/ui";
import { categoryById } from "../data/categories";
import { quizLevels } from "../data/depth";
import { categorySet, QUIZ_LENGTH, type PlaySet } from "../data/playSets";
import { topicGroups } from "../data/triviaTopics";
import { useSetting } from "../hooks";
import type { Depth, TriviaQuestion } from "../types";
import { href } from "../utils/router";
import { saveLastPlayed } from "../utils/resume";
import { triviaSeen } from "../utils/seen";
import { advance, recordOutcome, restoreSession, resultTitle, startSession, summarize, type Level, type SessionState } from "../utils/session";
import { createSetting } from "../utils/settings";
import { clearSession, loadSession, saveSession } from "../utils/storage";
import { planRound, unseenCount } from "../utils/triviaRound";

type Mode = "solo" | "together";
const levels: readonly Level[] = ["mix", 1, 2, 3, 4];
export const triviaLevelSetting = createSetting<Level>("closer.trivia.level", "mix", (v): v is Level => levels.includes(v as Level));
export const triviaModeSetting = createSetting<Mode>("closer.trivia.mode", "solo", (v): v is Mode => v === "solo" || v === "together");

const topicIcons: Record<string, LucideIcon> = {
  all: Shapes, geography: Globe, history: Landmark, science: FlaskConical, screen: Clapperboard, music: Music,
  sports: Trophy, food: Utensils, culture: Palette, tech: Cpu, logic: Puzzle,
};
const topics = [{ id: "all", label: "All topics" }, ...topicGroups.map((g) => ({ id: g.id, label: g.label }))];
const levelName = (l: Level) => (l === "mix" ? "Mixed" : quizLevels[l].name);

const triviaPool = (set: PlaySet) => set.pool.filter((q): q is TriviaQuestion => q.kind === "trivia");

/** A saved round that is still going, moved past a question that was already answered. */
function savedRound(set: PlaySet): SessionState | null {
  const saved = restoreSession(loadSession(set.key), "trivia", set.pool, set.limit);
  if (!saved || saved.done || Object.keys(saved.outcomes).length === 0) return null;
  const next = saved.currentId && saved.outcomes[saved.currentId] ? advance(saved, set.pool) : saved;
  return next.done ? null : next;
}

function newRound(set: PlaySet, level: Level): SessionState {
  const plan = planRound(triviaPool(set), { length: QUIZ_LENGTH, level, seen: triviaSeen.all() });
  return startSession("trivia", set.pool, { level, limit: set.limit, order: plan.map((q) => q.id) });
}

/** Trivia: choose a topic, a difficulty and how you're playing, then a round of ten. */
export function TriviaExperience() {
  const topic = useSetting(topicSetting);
  const set = useMemo(() => categorySet("trivia", "everyone", topic)!, [topic]);
  // A round under way on this topic (coming back from a refresh or another page) carries straight on.
  const [state, setState] = useState<SessionState | null>(() => savedRound(set));
  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  const category = categoryById("trivia")!;

  useEffect(() => {
    if (!state) return;
    saveSession(set.key, state);
    if (Object.keys(state.outcomes).length > 0) saveLastPlayed(set.key);
  }, [state, set.key]);

  const currentId = state?.currentId ?? null;
  useEffect(() => { if (currentId) triviaSeen.add(currentId); }, [currentId]);

  // Each new screen (setup, question, results) takes keyboard and screen-reader focus.
  const screen = state ? (state.done ? "results" : currentId) : "setup";
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    stage.current?.focus();
  }, [screen]);

  const start = (level: Level) => setState(newRound(set, level));
  const replay = () => { clearSession(set.key); start(state?.level ?? "mix"); };

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-4 sm:px-6 sm:pt-8">
      <a href={href.explore} className={`${quiet} -ml-3 min-h-11`}><ArrowLeft aria-hidden className="size-5" /> Back to categories</a>
      <div className="mt-2 flex items-center gap-3 sm:gap-4">
        <CategoryIcon category={category} />
        <div className="min-w-0">
          <h1 tabIndex={-1} className="text-xl font-extrabold tracking-tight sm:text-3xl">{state ? set.title : category.name}</h1>
          <p className="mt-0.5 hidden text-muted sm:block">{category.description}</p>
        </div>
      </div>
      <div ref={stage} tabIndex={-1} className="mt-5 rounded-[2rem] outline-none">
        {!state ? <Setup set={set} onStart={start} onContinue={() => setState(savedRound(set))} />
          : state.done ? <Results state={state} set={set} onReplay={replay} onSetup={() => setState(null)} />
          : <Round state={state} set={set} onChange={setState} onSetup={() => setState(null)} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Setup

function Setup({ set, onStart, onContinue }: { set: PlaySet; onStart: (level: Level) => void; onContinue: () => void }) {
  const topic = useSetting(topicSetting);
  const level = useSetting(triviaLevelSetting);
  const mode = useSetting(triviaModeSetting);
  const [, refresh] = useState(0);
  const pool = triviaPool(set).filter((q) => level === "mix" || q.depth === level);
  const fresh = unseenCount(pool, triviaSeen.all());
  const length = Math.min(QUIZ_LENGTH, pool.length);
  const going = savedRound(set);
  return (
    <form onSubmit={(e) => { e.preventDefault(); onStart(level); }}>
      {going && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-plum-100 bg-surface p-4">
          <p className="font-semibold">You have a round going: question {going.seen.length} of {going.order.length}.</p>
          <button type="button" onClick={onContinue} className={secondary}>Continue it <ArrowRight aria-hidden className="size-5" /></button>
        </div>
      )}
      <div className="space-y-6 rounded-[2rem] border border-plum-100 bg-surface/80 p-5 shadow-sm sm:p-8">
        <div>
          <SetupChoice<Mode> legend="Who's playing?" value={mode} onChange={(m) => triviaModeSetting.set(m)} className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2"
            options={[{ id: "solo", label: "On my own", icon: User }, { id: "together", label: "Together", icon: Users }]} />
          {mode === "together" && (
            <div className="mt-3 space-y-3">
              <p className="text-[15px] text-muted">One person reads each question aloud, everyone agrees on an answer, and you share one score.</p>
              <a href={href.game("trivia-duel")} className="flex min-h-12 items-center gap-3 rounded-2xl border-2 border-plum-100 bg-surface px-4 py-3 transition hover:border-plum-300">
                <Swords aria-hidden className="size-6 shrink-0 text-plum-600 dark:text-onplum-soft" />
                <span className="text-[15px]"><span className="font-bold text-plum-800">Just two of you? Trivia Duel.</span> <span className="text-muted">Race each other on one phone.</span></span>
              </a>
            </div>
          )}
        </div>
        <SetupChoice<Level> legend="Difficulty" value={level} onChange={(l) => triviaLevelSetting.set(l)} className="flex flex-wrap gap-2"
          options={levels.map((l) => ({ id: l, label: levelName(l) }))} />
        <SetupChoice legend="Topic" value={topic} onChange={(t) => topicSetting.set(t)} className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:grid-cols-3"
          options={topics.map((t) => ({ ...t, icon: topicIcons[t.id] }))} />
        <div className="rounded-2xl bg-plum-50 p-4 text-[15px] text-ink">
          <p><span className="font-bold">{length} questions.</span> {level === "mix" ? "They start easy and get harder." : `All ${levelName(level)}.`} One point for each right answer; skipping costs nothing. No timer.</p>
          <p className="mt-1 text-muted" role="status">
            {fresh === 0 ? "You've seen every question here. A round brings back the ones from longest ago."
              : fresh < length ? `Only ${fresh} new ${fresh === 1 ? "question" : "questions"} left here. The rest of the round brings back older ones.`
              : `${fresh.toLocaleString("en-US")} questions you haven't seen yet.`}
          </p>
          {fresh < length && pool.length > 0 && (
            <button type="button" onClick={() => { triviaSeen.forget(pool.map((q) => q.id)); refresh((n) => n + 1); }}
              className="mt-2 inline-flex min-h-11 cursor-pointer items-center gap-2 font-bold text-plum-700 underline underline-offset-4 dark:text-onplum-soft">
              <RotateCcw aria-hidden className="size-4" /> Treat them all as new again
            </button>
          )}
        </div>
      </div>
      <div className="sticky bottom-0 z-10 -mx-4 mt-4 bg-page/90 px-4 py-3 backdrop-blur sm:static sm:mx-0 sm:bg-transparent sm:px-0 sm:backdrop-blur-none">
        <button type="submit" disabled={length === 0} className={`${primary} w-full sm:w-auto`}>
          {going ? "Start a new round" : "Start the round"} <ArrowRight aria-hidden className="size-5" />
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- Round and results

function Round({ state, set, onChange, onSetup }: { state: SessionState; set: PlaySet; onChange: (f: (s: SessionState | null) => SessionState | null) => void; onSetup: () => void }) {
  const mode = useSetting(triviaModeSetting);
  const question = triviaPool(set).find((q) => q.id === state.currentId);
  if (!question) return null;
  const total = state.order.length;
  const s = summarize(state);
  const next = () => onChange((st) => st && advance(st, set.pool));
  return (
    <>
      <ProgressBar current={state.seen.length} total={total} label={`Question ${state.seen.length} of ${total}`} />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-4">
        <p className="text-[15px] font-semibold text-muted">{mode === "together" ? "Your score together" : "Your score"}: <span className="text-ink">{s.correct}</span></p>
        <button type="button" onClick={onSetup} className={`${quiet} -mr-3 min-h-11 px-3 text-[15px]`}><SlidersHorizontal aria-hidden className="size-4" /> Change setup</button>
      </div>
      <div className="mt-2">
        <TriviaStep key={question.id} question={question} tone={tintClass[set.category!.tint]} isLast={state.seen.length >= total}
          eyebrow={<><span className="inline-flex items-center gap-2"><DepthMeter depth={question.depth as Depth} /> {quizLevels[question.depth].name}</span><span className="text-muted">{question.topic}</span></>}
          onSubmitted={(correct) => onChange((st) => st && recordOutcome(st, correct ? "correct" : "incorrect"))}
          onSkip={next} onNext={next} />
      </div>
    </>
  );
}

function Results({ state, set, onReplay, onSetup }: { state: SessionState; set: PlaySet; onReplay: () => void; onSetup: () => void }) {
  const s = summarize(state);
  const byId = new Map(triviaPool(set).map((q) => [q.id, q]));
  const message = s.percent >= 80 ? "Brilliant. You're a trivia natural." : s.percent >= 50 ? "Solid round. A rematch could push you higher." : "Every round teaches you something. Try again?";
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-10">
      <div className="text-center">
        <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md"><Brain className="size-8" /></span>
        <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{resultTitle(s)}</h2>
        <p className="mx-auto mt-3 max-w-md text-lg text-muted">{message}{s.skipped > 0 && ` You skipped ${s.skipped}; skipped questions aren't scored.`}</p>
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <button type="button" onClick={onReplay} className={primary}><RotateCcw aria-hidden className="size-5" /> Play again</button>
          <button type="button" onClick={onSetup} className={secondary}>Change topic or difficulty</button>
        </div>
        <a href={href.game("trivia-duel")} className={`${quiet} mt-2`}><Swords aria-hidden className="size-5" /> Challenge someone to a Trivia Duel</a>
      </div>
      <h3 className="mt-8 text-lg font-extrabold">Your round</h3>
      <ol className="mt-3 space-y-2">
        {state.seen.map((id) => {
          const q = byId.get(id);
          if (!q) return null;
          const right = state.outcomes[id] === "correct";
          return (
            <li key={id} className="flex gap-3 rounded-2xl bg-page/60 p-3">
              <span aria-hidden className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full text-white ${right ? "bg-emerald-600" : "bg-coral-600"}`}>
                {right ? <Check className="size-4" /> : <X className="size-4" />}
              </span>
              <span className="text-[15px]"><span className="sr-only">{right ? "Right: " : state.outcomes[id] === "incorrect" ? "Wrong: " : "Skipped: "}</span>{q.text} <span className="font-bold">{q.options[q.answer]}</span></span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
