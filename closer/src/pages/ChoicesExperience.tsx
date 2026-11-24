import {
  ArrowLeft, ArrowRight, BadgeDollarSign, Clapperboard, Laugh, Mic, Plane, Rocket, RotateCcw, Scale, Shapes, SlidersHorizontal, Split,
  Undo2, UserRoundPlus, Users, Utensils, WandSparkles, Landmark, type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { CategoryIcon } from "../components/CategoryIcon";
import { DepthMeter } from "../components/DepthSelector";
import { ProgressBar } from "../components/ProgressBar";
import { OpenStep } from "../components/QuestionSteps";
import { SetupChoice } from "../components/SetupChoice";
import { tintClass } from "../components/tint";
import { primary, quiet, secondary } from "../components/ui";
import { AUDIENCES, audienceSetting } from "../data/audience";
import { categoryById } from "../data/categories";
import { choiceTopics } from "../data/choices/bank";
import { conversationLevels } from "../data/depth";
import { categorySet, CHOICES_LENGTH, type PlaySet } from "../data/playSets";
import { useSetting, useShortcuts } from "../hooks";
import type { AudienceChoice, Depth, OpenQuestion } from "../types";
import {
  ceilingSetting, choiceTopicSetting, defaultCeiling, formatSetting, matchChoices, planChoices, type Format, type TopicChoice,
} from "../utils/choices";
import { href } from "../utils/router";
import { saveLastPlayed } from "../utils/resume";
import { choicesSeen } from "../utils/seen";
import { advance, discuss, previous, restoreSession, startSession, summarize, type SessionState } from "../utils/session";
import { clearSession, favorites, loadSession, saveSession } from "../utils/storage";
import { unseenCount } from "../utils/triviaRound";

const topicIcons: Record<TopicChoice, LucideIcon> = {
  all: Shapes, funny: Laugh, food: Utensils, travel: Plane, bonds: UserRoundPlus, money: BadgeDollarSign, pop: Clapperboard,
  future: Rocket, ethics: Scale, society: Landmark, powers: WandSparkles,
};
const topics: { id: TopicChoice; label: string }[] = [{ id: "all", label: "All topics" }, ...choiceTopics];
const formatOptions: { id: Format; label: string; icon: LucideIcon }[] = [
  { id: "both", label: "Both", icon: Shapes },
  { id: "would-you-rather", label: "Would You Rather", icon: Split },
  { id: "debate", label: "Debates", icon: Scale },
];
const ceilingLabels: Record<Depth, string> = { 1: "Keep it light", 2: "Up to Meaningful", 3: "Up to Deep", 4: "Everything, even Bold" };
const ceilings = ([1, 2, 3, 4] as Depth[]).map((id) => ({ id, label: ceilingLabels[id] }));
const audiences: { id: AudienceChoice; label: string }[] = [{ id: "everyone", label: "Everyone" }, ...AUDIENCES.map((a) => ({ id: a.id, label: a.label }))];

/** The choices on the setup screen, as they stand. */
function useFilter() {
  const audience = useSetting(audienceSetting);
  const format = useSetting(formatSetting);
  const topic = useSetting(choiceTopicSetting);
  const chosen = useSetting(ceilingSetting);
  const ceiling = chosen === 0 ? defaultCeiling(audience) : chosen;
  return { audience, format, topic, ceiling };
}

function savedSet(set: PlaySet): SessionState | null {
  const s = restoreSession(loadSession(set.key), "would-you-rather", set.pool, set.limit);
  return s && !s.done && Object.keys(s.outcomes).length > 0 ? s : null;
}

/** Would You Rather & Debates: choose what to talk about, then one prompt at a time. */
export function ChoicesExperience() {
  const filter = useFilter();
  const set = useMemo(() => categorySet("would-you-rather", filter.audience)!, [filter.audience]);
  const pool = useMemo(() => matchChoices(set.pool, filter), [set, filter.format, filter.topic, filter.ceiling]); // eslint-disable-line react-hooks/exhaustive-deps
  const [state, setState] = useState<SessionState | null>(() => savedSet(set));
  const category = categoryById("would-you-rather")!;

  useEffect(() => {
    if (!state) return;
    saveSession(set.key, state);
    if (Object.keys(state.outcomes).length > 0) saveLastPlayed(set.key);
  }, [state, set.key]);

  const currentId = state?.currentId ?? null;
  useEffect(() => { if (currentId) choicesSeen.add(currentId); }, [currentId]);

  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  const screen = state ? (state.done ? "end" : currentId) : "setup";
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    stage.current?.focus();
  }, [screen]);

  const start = () => {
    clearSession(set.key);
    const order = planChoices(pool, { length: CHOICES_LENGTH, ceiling: filter.ceiling, seen: choicesSeen.all() });
    setState(startSession("would-you-rather", set.pool, { limit: set.limit, order }));
  };

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-4 sm:px-6 sm:pt-8">
      <a href={href.explore} className={`${quiet} -ml-3 min-h-11`}><ArrowLeft aria-hidden className="size-5" /> Back to categories</a>
      <div className="mt-2 flex items-center gap-3 sm:gap-4">
        <CategoryIcon category={category} />
        <div className="min-w-0">
          <h1 tabIndex={-1} className="text-xl font-extrabold tracking-tight sm:text-3xl">{category.name}</h1>
          <p className="mt-0.5 hidden text-muted sm:block">{category.description}</p>
        </div>
      </div>
      <div ref={stage} tabIndex={-1} className="mt-4 rounded-[2rem] outline-none">
        {!state ? <Setup set={set} pool={pool} onStart={start} onContinue={() => setState(savedSet(set))} />
          : state.done ? <End state={state} pool={pool} onMore={start} onSetup={() => setState(null)} />
          : <Play state={state} set={set} onChange={setState} onSetup={() => setState(null)} />}
      </div>
    </div>
  );
}

function Setup({ set, pool, onStart, onContinue }: { set: PlaySet; pool: OpenQuestion[]; onStart: () => void; onContinue: () => void }) {
  const { audience, format, topic, ceiling } = useFilter();
  const [, refresh] = useState(0);
  const fresh = unseenCount(pool.map((q) => ({ id: q.id, depth: q.depth, topic: "" })), choicesSeen.all());
  const going = savedSet(set);
  const n = pool.length;
  return (
    <form onSubmit={(e) => { e.preventDefault(); onStart(); }}>
      {going && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-plum-100 bg-surface p-4">
          <p className="font-semibold">You have a set going: {going.seen.length} of {going.order.length}.</p>
          <button type="button" onClick={onContinue} className={secondary}>Continue it <ArrowRight aria-hidden className="size-5" /></button>
        </div>
      )}
      <div className="space-y-6 rounded-[2rem] border border-plum-100 bg-surface/80 p-5 shadow-sm sm:p-8">
        <SetupChoice<Format> legend="Format" value={format} onChange={(v) => formatSetting.set(v)} className="flex flex-wrap gap-2" options={formatOptions} />
        <SetupChoice<AudienceChoice> legend="Who's playing?" value={audience} onChange={(v) => audienceSetting.set(v)} className="flex flex-wrap gap-2" options={audiences} />
        <SetupChoice<Depth> legend="Intensity: how deep it can go" value={ceiling} onChange={(v) => ceilingSetting.set(v)} className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2" options={ceilings}
          hint={ceiling === 4 ? `Bold: ${conversationLevels[4].hint.toLowerCase()}. You can skip any prompt.` : "Sets start light and deepen slowly. Bold prompts only appear if you choose them."} />
        <SetupChoice<TopicChoice> legend="Topic: what it's about" value={topic} onChange={(v) => choiceTopicSetting.set(v)} className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:grid-cols-3"
          options={topics.map((t) => ({ ...t, icon: topicIcons[t.id] }))} />
        <div className="rounded-2xl bg-plum-50 p-4 text-[15px] text-ink">
          <p role="status">
            {n === 0 ? <span className="font-bold">No prompts match.</span> : <><span className="font-bold">{n.toLocaleString("en-US")} {n === 1 ? "prompt matches" : "prompts match"}</span>, {fresh === n ? "all new to you" : `${fresh.toLocaleString("en-US")} you haven't seen yet`}. </>}
            {n === 0 ? " Try another topic or a higher intensity." : n < CHOICES_LENGTH ? "That's a short set; a broader topic or intensity gives you more." : `You'll get ${CHOICES_LENGTH} at a time.`}
          </p>
          {n === 0 && <button type="button" onClick={() => { choiceTopicSetting.set("all"); formatSetting.set("both"); }} className="mt-1 inline-flex min-h-11 cursor-pointer items-center font-bold text-plum-700 underline underline-offset-4 dark:text-onplum-soft">Show all topics and formats</button>}
          {n > 0 && fresh < Math.min(n, CHOICES_LENGTH) && (
            <button type="button" onClick={() => { choicesSeen.forget(pool.map((q) => q.id)); refresh((x) => x + 1); }}
              className="mt-1 inline-flex min-h-11 cursor-pointer items-center gap-2 font-bold text-plum-700 underline underline-offset-4 dark:text-onplum-soft">
              <RotateCcw aria-hidden className="size-4" /> Reshuffle: treat them all as new
            </button>
          )}
        </div>
        {format !== "would-you-rather" && <TimedDebate />}
      </div>
      <div className="sticky bottom-0 z-10 -mx-4 mt-4 bg-page/90 px-4 py-3 backdrop-blur sm:static sm:mx-0 sm:bg-transparent sm:px-0 sm:backdrop-blur-none">
        <button type="submit" disabled={n === 0} className={`${primary} w-full sm:w-auto`}>{going ? "Start a new set" : "Start"} <ArrowRight aria-hidden className="size-5" /></button>
      </div>
    </form>
  );
}

function TimedDebate() {
  return (
    <a href={href.debate} className="flex min-h-12 items-center gap-3 rounded-2xl border-2 border-plum-100 bg-surface px-4 py-3 transition hover:border-plum-300">
      <Mic aria-hidden className="size-6 shrink-0 text-plum-600 dark:text-onplum-soft" />
      <span className="text-[15px]"><span className="font-bold text-plum-800">Want a timed debate with a winner? Debate Night.</span> <span className="text-muted">Here you just talk each prompt through.</span></span>
    </a>
  );
}

function Play({ state, set, onChange, onSetup }: { state: SessionState; set: PlaySet; onChange: (f: (s: SessionState | null) => SessionState | null) => void; onSetup: () => void }) {
  const filter = useFilter();
  const root = useRef<HTMLDivElement>(null);
  const question = set.pool.find((q) => q.id === state.currentId);
  const next = () => onChange((s) => s && discuss(s, set.pool));
  const skip = () => onChange((s) => s && advance(s, set.pool));
  useShortcuts({ next, skip, favorite: question ? () => favorites.toggle(question.id) : undefined, speak: () => document.querySelector<HTMLButtonElement>("[data-speak]")?.click() }, !!question, root);
  if (question?.kind !== "open") return null;
  const total = state.order.length;
  const topic = choiceTopics.find((t) => t.id === question.topic)?.label;
  const chosen = [
    formatOptions.find((f) => f.id === filter.format)!.label === "Both" ? "Both formats" : formatOptions.find((f) => f.id === filter.format)!.label,
    topics.find((t) => t.id === filter.topic)!.label, audiences.find((a) => a.id === filter.audience)!.label, ceilingLabels[filter.ceiling],
  ];
  return (
    <div ref={root} tabIndex={-1} className="outline-none">
      <div className="flex items-center justify-between gap-3 rounded-2xl bg-surface/70 py-1 pl-4 pr-1 ring-1 ring-plum-100">
        <p className="min-w-0 text-sm font-semibold text-muted"><span className="sr-only">Chosen: </span>{chosen.join(" · ")}</p>
        <button type="button" onClick={onSetup} className={`${quiet} min-h-11 shrink-0 px-3 text-[15px]`}><SlidersHorizontal aria-hidden className="size-4" /> Change</button>
      </div>
      <div className="mt-3"><ProgressBar current={state.seen.length} total={total} label={`Prompt ${state.seen.length} of ${total}`} /></div>
      <div className="mt-4">
        <OpenStep key={question.id} question={question} tone={tintClass[set.category!.tint]} isLast={state.seen.length >= total}
          eyebrow={<><span>{question.categoryId === "debate" ? "Debate" : "Would You Rather"}</span>{topic && <span className="text-muted">{topic}</span>}<span className="inline-flex items-center gap-2"><DepthMeter depth={question.depth} /> {conversationLevels[question.depth].name}</span></>}
          onSkip={skip} onNext={next} />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <button type="button" disabled={state.seen.length < 2} onClick={() => onChange((s) => s && previous(s))} className={`${quiet} disabled:cursor-not-allowed disabled:opacity-50`}>
          <Undo2 aria-hidden className="size-5" /> Previous prompt
        </button>
        {question.categoryId === "debate" && <a href={href.debate} className={quiet}><Mic aria-hidden className="size-5" /> Timed Debate Night</a>}
      </div>
    </div>
  );
}

function End({ state, pool, onMore, onSetup }: { state: SessionState; pool: OpenQuestion[]; onMore: () => void; onSetup: () => void }) {
  const s = summarize(state);
  const fresh = unseenCount(pool.map((q) => ({ id: q.id, depth: q.depth, topic: "" })), choicesSeen.all());
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-coral-500 to-amber-400 text-white shadow-md"><Users className="size-8" /></span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">That's the set</h2>
      <p className="mx-auto mt-3 max-w-md text-lg text-muted">
        You talked through {s.answered} and skipped {s.skipped}. {fresh > 0 ? `${fresh.toLocaleString("en-US")} more you haven't seen match your choices.` : "You've seen every prompt that matches. Reshuffle to go round again, or broaden your choices."}
      </p>
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={() => { if (fresh === 0) choicesSeen.forget(pool.map((q) => q.id)); onMore(); }} className={primary}>
          <RotateCcw aria-hidden className="size-5" /> {fresh === 0 ? "Reshuffle and play again" : "Keep going"}
        </button>
        <button type="button" onClick={onSetup} className={secondary}>Change topic or format</button>
      </div>
    </div>
  );
}
