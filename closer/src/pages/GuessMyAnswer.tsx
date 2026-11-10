import { ArrowLeft, Check, Eye, EyeOff, Minus, Plus, RotateCcw, Trophy, Users, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { QuestionCard } from "../components/QuestionCard";
import { ProgressBar } from "../components/ProgressBar";
import { primary, quiet, secondary } from "../components/ui";
import { guessPool, guessThemes } from "../data/guessQuestions";
import type { GuessQuestion } from "../types";
import * as game from "../utils/guessGame";
import { href } from "../utils/router";

const EACH_CHOICES = [2, 3, 4, 5];

interface Setup {
  /** A name for every possible seat; only the first `count` are used. */
  names: string[];
  count: number;
  theme: string;
  /** How many times each person answers. */
  each: number;
}

const blankNames = () => Array.from({ length: game.MAX_PLAYERS }, () => "");

/** Two to six players, one device: one picks a secret answer, the others guess it. The answerer rotates every round. */
export function GuessMyAnswer() {
  const [setup, setSetup] = useState<Setup>({ names: blankNames(), count: 2, theme: "mix", each: 3 });
  const [state, setState] = useState<game.GuessState | null>(null);

  // Names fall back to "Player 1", "Player 2" and so on when left blank.
  const names = (s: Setup): string[] => s.names.slice(0, s.count).map((n, i) => n.trim() || `Player ${i + 1}`);
  const start = () => setState(game.startGame(names(setup), guessPool(setup.theme), game.totalRounds(setup.count, setup.each)));

  // Each new screen takes focus so keyboard and screen-reader users land on it.
  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    stage.current?.focus();
  }, [state?.phase, state?.round, state?.turn, state === null]);

  const update = (fn: (s: game.GuessState) => game.GuessState) => setState((s) => (s ? fn(s) : s));

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-8 sm:px-6 sm:pt-12">
      <a href={href.explore} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> Back to categories
      </a>
      <div className="mt-4 flex items-center gap-4">
        <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-plum-600 to-coral-500 text-white shadow-md">
          <Users className="size-8" />
        </span>
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">Guess My Answer</h1>
          <p className="mt-1 text-muted">Two to six players, one device. How well do you know each other?</p>
        </div>
      </div>

      <div ref={stage} tabIndex={-1} className="mt-8 rounded-[2rem] outline-none">
        {!state ? (
          <SetupForm setup={setup} onChange={setSetup} onStart={start} />
        ) : (
          <Game state={state} update={update}
            onReplay={() => setState((s) => (s ? game.replay(s, guessPool(setup.theme)) : s))}
            onSetup={() => setState(null)} />
        )}
      </div>
    </div>
  );
}

function SetupForm({ setup, onChange, onStart }: { setup: Setup; onChange: (s: Setup) => void; onStart: () => void }) {
  const id = useId();
  const field = "mt-2 w-full rounded-2xl border border-plum-100 bg-page/60 p-3.5 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400";
  const stepper = "inline-flex size-11 cursor-pointer items-center justify-center rounded-full border-2 border-plum-200 bg-surface text-plum-800 transition hover:bg-plum-50 disabled:cursor-not-allowed disabled:opacity-40";
  const total = game.totalRounds(setup.count, setup.each);
  const available = guessPool(setup.theme).length;
  return (
    <form className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-10"
      onSubmit={(e) => { e.preventDefault(); onStart(); }}>
      <h2 className="text-2xl font-extrabold">Set up your game</h2>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">
        <li>One person secretly picks the answer that fits them best.</li>
        <li>Pass the device around. Everyone else guesses which one it was.</li>
        <li>Each right guess scores a point. Then the next person picks.</li>
      </ol>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <span id={`${id}-count`} className="text-sm font-semibold text-muted">Players</span>
        <button type="button" aria-label="Fewer players" disabled={setup.count <= game.MIN_PLAYERS} onClick={() => onChange({ ...setup, count: setup.count - 1 })} className={stepper}>
          <Minus aria-hidden className="size-5" />
        </button>
        <output aria-labelledby={`${id}-count`} className="min-w-8 text-center text-2xl font-extrabold">{setup.count}</output>
        <button type="button" aria-label="More players" disabled={setup.count >= game.MAX_PLAYERS} onClick={() => onChange({ ...setup, count: setup.count + 1 })} className={stepper}>
          <Plus aria-hidden className="size-5" />
        </button>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {Array.from({ length: setup.count }, (_, i) => (
          <div key={i}>
            <label htmlFor={`${id}-p${i}`} className="text-sm font-semibold text-muted">Player {i + 1}</label>
            <input id={`${id}-p${i}`} type="text" maxLength={20} placeholder={`Player ${i + 1}`} value={setup.names[i]}
              onChange={(e) => { const names = [...setup.names]; names[i] = e.target.value; onChange({ ...setup, names }); }}
              className={field} autoComplete="off" />
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`${id}-theme`} className="text-sm font-semibold text-muted">Theme</label>
          <select id={`${id}-theme`} value={setup.theme} onChange={(e) => onChange({ ...setup, theme: e.target.value })} className={field}>
            <option value="mix">Mix of everything</option>
            {guessThemes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${id}-each`} className="text-sm font-semibold text-muted">Turns to pick, each</label>
          <select id={`${id}-each`} value={setup.each} onChange={(e) => onChange({ ...setup, each: Number(e.target.value) })} className={field}>
            {EACH_CHOICES.map((n) => <option key={n} value={n}>{n} turns ({game.totalRounds(setup.count, n)} rounds)</option>)}
          </select>
        </div>
      </div>
      <p className="mt-2 text-sm text-muted">
        {setup.theme === "mix" ? `Questions from all ${guessThemes.length} themes.` : guessThemes.find((t) => t.id === setup.theme)?.description}
        {total > available && ` This theme has ${available} questions, so the game will have ${available} rounds.`}
      </p>

      <button type="submit" className={`${primary} mt-6 w-full sm:w-auto`}>Start the game</button>
    </form>
  );
}

const list = (names: string[]) =>
  names.length <= 1 ? (names[0] ?? "") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;

function Game({ state, update, onReplay, onSetup }: {
  state: game.GuessState;
  update: (fn: (s: game.GuessState) => game.GuessState) => void;
  onReplay: () => void;
  onSetup: () => void;
}) {
  const { players, round, phase, scores } = state;
  const total = state.questions.length;
  const n = players.length;

  if (phase === "final") return <Final state={state} onReplay={onReplay} onSetup={onSetup} />;

  const question = state.questions[round];
  const answererIdx = game.answererOf(round, n);
  const answerer = players[answererIdx];
  const guesserIdx = phase === "handoff-guess" || phase === "guessing" ? game.currentGuesser(state) : null;
  const guesser = guesserIdx === null ? "" : players[guesserIdx];
  const others = list(players.filter((_, i) => i !== answererIdx));
  const highlight = phase === "handoff-answer" || phase === "answering" ? answererIdx : guesserIdx;

  return (
    <div className="space-y-5">
      <ProgressBar current={round + (phase === "reveal" ? 1 : 0)} total={total} label={`Round ${round + 1} of ${total}`} />
      <Scoreboard players={players} scores={scores} highlight={highlight} />

      {phase === "handoff-answer" && (
        <Handoff key="ha" name={answerer}
          text={`Pass the device to ${answerer}. ${n === 2 ? `${others}, look away` : "Everyone else, look away"}: ${answerer} is about to pick a secret answer.`}
          button={`I'm ${answerer}, show the question`} onReady={() => update(game.beginAnswering)} />
      )}
      {phase === "answering" && (
        <Pick key={`a${round}`} question={question} eyebrow={`${answerer}: pick your answer in secret`}
          hint={`Choose the one that fits you best. ${others} will try to guess it.`}
          button="Lock in my answer" onSubmit={(i) => update((s) => game.lockAnswer(s, i))} />
      )}
      {phase === "handoff-guess" && (
        <Handoff key={`hg${round}-${state.turn}`} name={guesser} locked
          text={state.turn === 0
            ? `Answer locked and hidden. Pass the device to ${guesser}.`
            : `Guess locked and hidden. Pass the device to ${guesser}, and no peeking at earlier guesses.`}
          button={`I'm ${guesser}, show the question`} onReady={() => update(game.beginGuessing)} />
      )}
      {phase === "guessing" && (
        <Pick key={`g${round}-${state.turn}`} question={question} eyebrow={`${guesser}: guess ${answerer}'s answer`}
          hint={`Which one did ${answerer} pick?`}
          button="Lock in my guess" onSubmit={(i) => update((s) => game.submitGuess(s, i))} />
      )}
      {phase === "reveal" && state.secret !== null && (
        <Reveal key={`r${round}`} state={state} question={question} isLast={round + 1 >= total} onNext={() => update(game.nextRound)} />
      )}
    </div>
  );
}

function Scoreboard({ players, scores, highlight }: { players: string[]; scores: number[]; highlight: number | null }) {
  const cols = players.length <= 2 ? "grid-cols-2" : players.length === 4 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-3";
  return (
    <div role="group" aria-label="Scores" className={`grid gap-3 ${cols}`}>
      {players.map((name, i) => (
        <div key={i} className={`rounded-2xl border-2 p-3 text-center ${i === highlight ? "border-plum-300 bg-plum-50" : "border-plum-100 bg-surface"}`}>
          <p className="truncate text-sm font-semibold text-muted">{name}</p>
          <p className="text-2xl font-extrabold text-plum-800">{scores[i]}</p>
        </div>
      ))}
    </div>
  );
}

/** The screen that stands between the players so a secret answer stays secret. */
function Handoff({ name, text, button, onReady, locked }: { name: string; text: string; button: string; onReady: () => void; locked?: boolean }) {
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-plum-100 text-plum-700 dark:text-onplum-soft">
        {locked ? <EyeOff className="size-8" /> : <Eye className="size-8" />}
      </span>
      <h2 className="mt-5 text-2xl font-extrabold sm:text-3xl">{locked ? "Locked in" : `${name}'s turn`}</h2>
      <p className="mx-auto mt-3 max-w-md text-lg text-muted">{text}</p>
      <button type="button" onClick={onReady} className={`${primary} mt-8`}>{button}</button>
    </div>
  );
}

function Pick({ question, eyebrow, hint, button, onSubmit }: {
  question: GuessQuestion; eyebrow: string; hint: string; button: string; onSubmit: (option: number) => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [sent, setSent] = useState(false);
  const group = useId();
  return (
    <QuestionCard eyebrow={eyebrow} text={question.text}>
      <p className="mt-3 text-muted">{hint}</p>
      <fieldset className="mt-5" disabled={sent}>
        <legend className="sr-only">Choose one</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {question.options.map((option, i) => {
            const chosen = i === choice;
            return (
              <label key={option} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 p-4 font-semibold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${
                chosen ? "border-plum-500 bg-plum-50 ring-2 ring-plum-200" : "border-plum-100 bg-surface hover:border-plum-300"}`}>
                <input type="radio" name={group} value={i} checked={chosen} onChange={() => setChoice(i)} className="sr-only" />
                <span aria-hidden className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${chosen ? "bg-plum-600 text-white" : "bg-plum-100 text-plum-800"}`}>{"ABCD"[i]}</span>
                <span>{option}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      <button type="button" disabled={choice === null || sent} className={`${primary} mt-5 w-full sm:w-auto`}
        onClick={() => { if (choice !== null && !sent) { setSent(true); onSubmit(choice); } }}>
        {button}
      </button>
    </QuestionCard>
  );
}

function Reveal({ state, question, isLast, onNext }: { state: game.GuessState; question: GuessQuestion; isLast: boolean; onNext: () => void }) {
  const { players, round, secret, guesses } = state;
  const answerer = players[game.answererOf(round, players.length)];
  const guessers = game.guessersOf(round, players.length);
  const matched = guessers.filter((g) => guesses[g] === secret);
  const row = (key: string, label: string, index: number, tone: string, icon: ReactNode, delay = 0) => (
    <div key={key} className={`flex items-center gap-3 rounded-2xl border-2 p-4 animate-reveal ${tone}`} style={delay ? { animationDelay: `${delay}ms` } : undefined}>
      {icon}
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-muted">{label}</p>
        <p className="text-lg font-extrabold">{question.options[index]}</p>
      </div>
    </div>
  );
  const summary = matched.length === 0
    ? "No one guessed it this time."
    : `It's a match! ${list(matched.map((g) => players[g]))} score${matched.length === 1 ? "s" : ""} a point${matched.length === 1 ? "" : " each"}.`;
  return (
    <QuestionCard eyebrow="The reveal" text={question.text}>
      <div className="mt-5 space-y-3">
        {row("secret", `${answerer} picked`, secret as number, "border-plum-300 bg-plum-50", <Eye aria-hidden className="size-6 shrink-0 text-plum-700 dark:text-onplum-soft" />)}
        {guessers.map((g, i) => {
          const ok = guesses[g] === secret;
          return row(`guess-${g}`, `${players[g]} guessed`, guesses[g] as number,
            ok ? "border-emerald-500 bg-emerald-50" : "border-coral-500 bg-coral-50",
            ok ? <Check aria-hidden className="size-6 shrink-0 text-emerald-700" /> : <X aria-hidden className="size-6 shrink-0 text-coral-700" />,
            450 + i * 200);
        })}
      </div>
      <p role="status" className={`mt-5 rounded-2xl p-4 text-lg font-extrabold ${matched.length ? "bg-emerald-50 text-emerald-900" : "bg-coral-50 text-coral-700"}`}>{summary}</p>
      <button type="button" onClick={onNext} className={`${primary} mt-5 w-full sm:w-auto`}>{isLast ? "See final scores" : "Next round"}</button>
    </QuestionCard>
  );
}

function Final({ state, onReplay, onSetup }: { state: game.GuessState; onReplay: () => void; onSetup: () => void }) {
  const top = game.winners(state);
  const { players, scores } = state;
  const everyone = top.length === players.length;
  const headline = everyone ? "It's a tie!" : top.length === 1 ? `${players[top[0]]} wins!` : `${list(top.map((i) => players[i]))} tie for the lead!`;
  const each = state.questions.length / players.length;
  const cols = players.length <= 2 ? "grid-cols-2" : players.length === 4 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-3";
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{headline}</h2>
      <p className="mx-auto mt-2 max-w-md text-lg text-muted">
        {everyone ? "You all know each other equally well." : "That's how well you know each other."}
      </p>
      <div role="group" aria-label="Final scores" className={`mx-auto mt-6 grid max-w-xl gap-3 ${cols}`}>
        {players.map((name, i) => (
          <div key={i} className={`rounded-2xl p-4 ${top.includes(i) ? "bg-plum-100" : "bg-plum-50"}`}>
            <p className="text-4xl font-extrabold text-plum-800">{scores[i]}</p>
            <p className="truncate text-sm font-semibold text-muted">{name}</p>
          </div>
        ))}
      </div>
      {Number.isInteger(each) && <p className="mt-3 text-sm text-muted">out of {each * (players.length - 1)} possible points each</p>}
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={onReplay} className={primary}><RotateCcw aria-hidden className="size-5" /> Play again</button>
        <button type="button" onClick={onSetup} className={secondary}>Change players or theme</button>
      </div>
    </div>
  );
}
