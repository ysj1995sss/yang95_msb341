import { ArrowLeft, Check, Eye, EyeOff, RotateCcw, Trophy, Users, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { QuestionCard } from "../components/QuestionCard";
import { ProgressBar } from "../components/ProgressBar";
import { primary, quiet, secondary } from "../components/ui";
import { guessPool, guessThemes } from "../data/guessQuestions";
import type { GuessQuestion } from "../types";
import * as game from "../utils/guessGame";
import { href } from "../utils/router";

const ROUND_CHOICES = [4, 6, 8, 10];

interface Setup {
  names: [string, string];
  theme: string;
  rounds: number;
}

/** Two players, one device: one picks a secret answer, the other guesses it. Roles swap each round. */
export function GuessMyAnswer() {
  const [setup, setSetup] = useState<Setup>({ names: ["", ""], theme: "mix", rounds: 6 });
  const [state, setState] = useState<game.GuessState | null>(null);

  // Player names fall back to "Player 1" / "Player 2" when left blank.
  const names = (s: Setup): [string, string] => [s.names[0].trim() || "Player 1", s.names[1].trim() || "Player 2"];
  const start = () => setState(game.startGame(names(setup), guessPool(setup.theme), setup.rounds));

  // Each new screen takes focus so keyboard and screen-reader users land on it.
  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    stage.current?.focus();
  }, [state?.phase, state?.round, state === null]);

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
          <p className="mt-1 text-muted">Two players, one device. How well do you know each other?</p>
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
  const field = "mt-2 w-full rounded-2xl border border-plum-100 bg-cream/60 p-3.5 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400";
  return (
    <form className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-6 shadow-lg sm:p-10"
      onSubmit={(e) => { e.preventDefault(); onStart(); }}>
      <h2 className="text-2xl font-extrabold">Set up your game</h2>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">
        <li>One of you secretly picks the answer that fits them best.</li>
        <li>Pass the device. The other guesses which one it was.</li>
        <li>A right guess scores a point. Then you swap roles.</li>
      </ol>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i}>
            <label htmlFor={`${id}-p${i}`} className="text-sm font-semibold text-muted">Player {i + 1}</label>
            <input id={`${id}-p${i}`} type="text" maxLength={20} placeholder={`Player ${i + 1}`} value={setup.names[i]}
              onChange={(e) => { const names: [string, string] = [...setup.names]; names[i] = e.target.value; onChange({ ...setup, names }); }}
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
          <label htmlFor={`${id}-rounds`} className="text-sm font-semibold text-muted">Rounds</label>
          <select id={`${id}-rounds`} value={setup.rounds} onChange={(e) => onChange({ ...setup, rounds: Number(e.target.value) })} className={field}>
            {ROUND_CHOICES.map((n) => <option key={n} value={n}>{n} rounds</option>)}
          </select>
        </div>
      </div>
      <p className="mt-2 text-sm text-muted">
        {setup.theme === "mix" ? "Questions from all six themes." : guessThemes.find((t) => t.id === setup.theme)?.description}
      </p>

      <button type="submit" className={`${primary} mt-6 w-full sm:w-auto`}>Start the game</button>
    </form>
  );
}

function Game({ state, update, onReplay, onSetup }: {
  state: game.GuessState;
  update: (fn: (s: game.GuessState) => game.GuessState) => void;
  onReplay: () => void;
  onSetup: () => void;
}) {
  const { players, round, phase, scores } = state;
  const total = state.questions.length;

  if (phase === "final") return <Final state={state} onReplay={onReplay} onSetup={onSetup} />;

  const question = state.questions[round];
  const answerer = players[game.answererOf(round)];
  const guesser = players[game.guesserOf(round)];

  return (
    <div className="space-y-5">
      <ProgressBar current={round + (phase === "reveal" ? 1 : 0)} total={total} label={`Round ${round + 1} of ${total}`} />
      <Scoreboard players={players} scores={scores} highlight={game.guesserOf(round)} />

      {phase === "handoff-answer" && (
        <Handoff key="ha" name={answerer}
          text={`Pass the device to ${answerer}. ${guesser}, look away: ${answerer} is about to pick a secret answer.`}
          button={`I'm ${answerer}, show the question`} onReady={() => update(game.beginAnswering)} />
      )}
      {phase === "answering" && (
        <Pick key={`a${round}`} question={question} eyebrow={`${answerer}: pick your answer in secret`}
          hint={`Choose the one that fits you best. ${guesser} will try to guess it.`}
          button="Lock in my answer" onSubmit={(i) => update((s) => game.lockAnswer(s, i))} />
      )}
      {phase === "handoff-guess" && (
        <Handoff key="hg" name={guesser} locked
          text={`Answer locked and hidden. Pass the device to ${guesser}.`}
          button={`I'm ${guesser}, show the question`} onReady={() => update(game.beginGuessing)} />
      )}
      {phase === "guessing" && (
        <Pick key={`g${round}`} question={question} eyebrow={`${guesser}: guess ${answerer}'s answer`}
          hint={`Which one did ${answerer} pick?`}
          button="Lock in my guess" onSubmit={(i) => update((s) => game.submitGuess(s, i))} />
      )}
      {phase === "reveal" && state.secret !== null && state.guess !== null && (
        <Reveal key={`r${round}`} question={question} answerer={answerer} guesser={guesser} secret={state.secret}
          guess={state.guess} isLast={round + 1 >= total} onNext={() => update(game.nextRound)} />
      )}
    </div>
  );
}

function Scoreboard({ players, scores, highlight }: { players: [string, string]; scores: [number, number]; highlight: 0 | 1 }) {
  return (
    <div role="group" aria-label="Scores" className="grid grid-cols-2 gap-3">
      {players.map((name, i) => (
        <div key={i} className={`rounded-2xl border-2 p-3 text-center ${i === highlight ? "border-plum-300 bg-plum-50" : "border-plum-100 bg-white"}`}>
          <p className="truncate text-sm font-semibold text-muted">{name}</p>
          <p className="text-2xl font-extrabold text-plum-800">{scores[i]}</p>
        </div>
      ))}
    </div>
  );
}

/** The screen that stands between the two players so a secret answer stays secret. */
function Handoff({ name, text, button, onReady, locked }: { name: string; text: string; button: string; onReady: () => void; locked?: boolean }) {
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-plum-100 text-plum-700">
        {locked ? <EyeOff className="size-8" /> : <Eye className="size-8" />}
      </span>
      <h2 className="mt-5 text-2xl font-extrabold sm:text-3xl">{locked ? "Answer locked" : `${name}'s turn`}</h2>
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
                chosen ? "border-plum-500 bg-plum-50 ring-2 ring-plum-200" : "border-plum-100 bg-white hover:border-plum-300"}`}>
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

function Reveal({ question, answerer, guesser, secret, guess, isLast, onNext }: {
  question: GuessQuestion; answerer: string; guesser: string; secret: number; guess: number; isLast: boolean; onNext: () => void;
}) {
  const match = secret === guess;
  const row = (label: string, index: number, tone: string, icon: ReactNode) => (
    <div className={`flex items-center gap-3 rounded-2xl border-2 p-4 ${tone}`}>
      {icon}
      <div>
        <p className="text-sm font-semibold text-muted">{label}</p>
        <p className="text-lg font-extrabold">{question.options[index]}</p>
      </div>
    </div>
  );
  return (
    <QuestionCard eyebrow="The reveal" text={question.text}>
      <div className="mt-5 space-y-3">
        {row(`${answerer} picked`, secret, "animate-reveal border-plum-300 bg-plum-50", <Eye aria-hidden className="size-6 shrink-0 text-plum-700" />)}
        {row(`${guesser} guessed`, guess, match ? "animate-reveal [animation-delay:450ms] border-emerald-500 bg-emerald-50" : "animate-reveal [animation-delay:450ms] border-coral-500 bg-coral-50",
          match ? <Check aria-hidden className="size-6 shrink-0 text-emerald-700" /> : <X aria-hidden className="size-6 shrink-0 text-coral-700" />)}
      </div>
      <p role="status" className={`mt-5 rounded-2xl p-4 text-lg font-extrabold ${match ? "bg-emerald-50 text-emerald-900" : "bg-coral-50 text-coral-700"}`}>
        {match ? `It's a match! ${guesser} scores a point.` : `Not this time. ${guesser} guessed ${question.options[guess]}.`}
      </p>
      <button type="button" onClick={onNext} className={`${primary} mt-5 w-full sm:w-auto`}>{isLast ? "See final scores" : "Next round"}</button>
    </QuestionCard>
  );
}

function Final({ state, onReplay, onSetup }: { state: game.GuessState; onReplay: () => void; onSetup: () => void }) {
  const result = game.winner(state);
  const { players, scores } = state;
  const headline = result === "tie" ? "It's a tie!" : `${players[result]} wins!`;
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{headline}</h2>
      <p className="mx-auto mt-2 max-w-md text-lg text-muted">
        {result === "tie" ? "You know each other equally well." : "That's how well you know each other."}
      </p>
      <div role="group" aria-label="Final scores" className="mx-auto mt-6 grid max-w-md grid-cols-2 gap-3">
        {players.map((name, i) => (
          <div key={i} className={`rounded-2xl p-4 ${result === i ? "bg-plum-100" : "bg-plum-50"}`}>
            <p className="text-4xl font-extrabold text-plum-800">{scores[i]}</p>
            <p className="truncate text-sm font-semibold text-muted">{name}</p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-sm text-muted">out of {Math.ceil(state.questions.length / 2)} guesses each</p>
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={onReplay} className={primary}><RotateCcw aria-hidden className="size-5" /> Play again</button>
        <button type="button" onClick={onSetup} className={secondary}>Change players or theme</button>
      </div>
    </div>
  );
}
