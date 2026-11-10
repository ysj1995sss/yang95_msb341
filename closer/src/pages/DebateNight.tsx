import { ArrowLeft, Check, Mic, Pause, Play, RotateCcw, Shuffle, Trophy } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { ProgressBar } from "../components/ProgressBar";
import { QuestionCard } from "../components/QuestionCard";
import { primary, quiet, secondary } from "../components/ui";
import { debateMotions } from "../data/debateMotions";
import { useCountdown } from "../hooks";
import * as debate from "../utils/debateGame";
import { href } from "../utils/router";
import { formatClock, timerLabel } from "../utils/timer";

const ROUND_CHOICES = [3, 5, 7];
const SPEECH_CHOICES = [30, 60, 90, 120];

interface Setup {
  names: [string, string];
  rounds: number;
  seconds: number;
}

/** Two people, one device, a statement to argue about. Each speaks against the clock, then the room votes. */
export function DebateNight() {
  const [setup, setSetup] = useState<Setup>({ names: ["", ""], rounds: 5, seconds: 60 });
  const [state, setState] = useState<debate.DebateState | null>(null);

  const names = (s: Setup): [string, string] => [s.names[0].trim() || "Player 1", s.names[1].trim() || "Player 2"];
  const start = () => setState(debate.startDebate(names(setup), debateMotions, setup.rounds, setup.seconds));
  const update = (fn: (s: debate.DebateState) => debate.DebateState) => setState((s) => (s ? fn(s) : s));

  // Each new screen takes focus so keyboard and screen-reader users land on it.
  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    stage.current?.focus();
  }, [state?.phase, state?.round, state === null]);

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-8 sm:px-6 sm:pt-12">
      <a href={href.explore} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> Back to categories
      </a>
      <div className="mt-4 flex items-center gap-4">
        <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-plum-500 to-sky-400 text-white shadow-md">
          <Mic className="size-8" />
        </span>
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">Debate Night</h1>
          <p className="mt-1 text-muted">Two sides, a timer, and the room decides who argued better.</p>
        </div>
      </div>

      <div ref={stage} tabIndex={-1} className="mt-8 rounded-[2rem] outline-none">
        {!state ? (
          <SetupForm setup={setup} onChange={setSetup} onStart={start} />
        ) : (
          <Round state={state} update={update}
            onReplay={() => update((s) => debate.replay(s, debateMotions))}
            onSetup={() => setState(null)} />
        )}
      </div>
    </div>
  );
}

function SetupForm({ setup, onChange, onStart }: { setup: Setup; onChange: (s: Setup) => void; onStart: () => void }) {
  const id = useId();
  const field = "mt-2 w-full rounded-2xl border border-plum-100 bg-page/60 p-3.5 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400";
  return (
    <form className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-10"
      onSubmit={(e) => { e.preventDefault(); onStart(); }}>
      <h2 className="text-2xl font-extrabold">Set up the debate</h2>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">
        <li>Each round has a statement. One of you argues for it, the other against.</li>
        <li>You each get the same time on the clock.</li>
        <li>Everyone else votes on who argued better. Sides swap every round.</li>
      </ol>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i}>
            <label htmlFor={`${id}-p${i}`} className="text-sm font-semibold text-muted">Debater {i + 1}</label>
            <input id={`${id}-p${i}`} type="text" maxLength={20} placeholder={`Player ${i + 1}`} value={setup.names[i]}
              onChange={(e) => { const names: [string, string] = [...setup.names]; names[i] = e.target.value; onChange({ ...setup, names }); }}
              className={field} autoComplete="off" />
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`${id}-rounds`} className="text-sm font-semibold text-muted">Rounds</label>
          <select id={`${id}-rounds`} value={setup.rounds} onChange={(e) => onChange({ ...setup, rounds: Number(e.target.value) })} className={field}>
            {ROUND_CHOICES.map((n) => <option key={n} value={n}>{n} rounds</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${id}-time`} className="text-sm font-semibold text-muted">Time to speak</label>
          <select id={`${id}-time`} value={setup.seconds} onChange={(e) => onChange({ ...setup, seconds: Number(e.target.value) })} className={field}>
            {SPEECH_CHOICES.map((n) => <option key={n} value={n}>{timerLabel(n)} each</option>)}
          </select>
        </div>
      </div>

      <button type="submit" className={`${primary} mt-6 w-full sm:w-auto`}>Start the debate</button>
    </form>
  );
}

function Round({ state, update, onReplay, onSetup }: {
  state: debate.DebateState;
  update: (fn: (s: debate.DebateState) => debate.DebateState) => void;
  onReplay: () => void;
  onSetup: () => void;
}) {
  const { players, round, phase, scores, motions } = state;
  const total = motions.length;
  const countdown = useCountdown(state.seconds, `${round}-${phase}`);

  if (phase === "final") return <Final state={state} onReplay={onReplay} onSetup={onSetup} />;

  const forIdx = debate.forPlayerOf(round);
  const againstIdx = debate.againstPlayerOf(round);
  const motion = motions[round];
  const speaker = phase === "for" ? forIdx : phase === "against" ? againstIdx : null;

  return (
    <div className="space-y-5">
      <ProgressBar current={round + (phase === "result" ? 1 : 0)} total={total} label={`Round ${round + 1} of ${total}`} />
      <Scoreboard players={players} scores={scores} highlight={speaker} />

      {phase === "brief" && (
        <QuestionCard eyebrow="The statement" text={motion}>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Side label="For" name={players[forIdx]} tone="border-emerald-500 bg-emerald-50" />
            <Side label="Against" name={players[againstIdx]} tone="border-coral-500 bg-coral-50" />
          </div>
          <p className="mt-4 text-muted">{players[forIdx]} speaks first, then {players[againstIdx]}. Each gets {timerLabel(state.seconds)}.</p>
          <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button type="button" onClick={() => update(debate.reroll)} disabled={state.spare.length === 0} className={quiet}>
              <Shuffle aria-hidden className="size-5" /> Different statement
            </button>
            <button type="button" onClick={() => update(debate.beginSpeeches)} className={primary}>Start the debate</button>
          </div>
        </QuestionCard>
      )}

      {speaker !== null && (
        <QuestionCard eyebrow={`${players[speaker]} argues ${phase === "for" ? "for" : "against"}`} text={motion}>
          <Clock countdown={countdown} />
          <div className="mt-5 flex justify-end">
            <button type="button" onClick={() => update(debate.nextSpeaker)} className={primary}>
              <Check aria-hidden className="size-5" /> {phase === "for" ? `Done. ${players[againstIdx]}'s turn` : "Done. Time to vote"}
            </button>
          </div>
        </QuestionCard>
      )}

      {phase === "vote" && (
        <QuestionCard eyebrow="The room decides" text="Who argued better?">
          <p className="mt-2 text-muted">Everyone but the debaters votes. If it's too close to call, call it a draw.</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <button type="button" onClick={() => update((s) => debate.castVote(s, "for"))} className={secondary}>
              {players[forIdx]} <span className="text-muted">(for)</span>
            </button>
            <button type="button" onClick={() => update((s) => debate.castVote(s, "against"))} className={secondary}>
              {players[againstIdx]} <span className="text-muted">(against)</span>
            </button>
            <button type="button" onClick={() => update((s) => debate.castVote(s, "draw"))} className={secondary}>A draw</button>
          </div>
        </QuestionCard>
      )}

      {phase === "result" && (
        <QuestionCard eyebrow="The verdict" text={
          state.verdict === "draw" ? "It's a draw." : `${players[state.verdict === "for" ? forIdx : againstIdx]} wins the round.`}>
          <p role="status" className="mt-3 text-lg text-muted">
            {state.verdict === "draw" ? "No points this round." : "One point for the winner."}
          </p>
          <button type="button" onClick={() => update(debate.nextRound)} className={`${primary} mt-5 w-full sm:w-auto`}>
            {round + 1 >= total ? "See final scores" : "Next round"}
          </button>
        </QuestionCard>
      )}
    </div>
  );
}

function Side({ label, name, tone }: { label: string; name: string; tone: string }) {
  return (
    <div className={`rounded-2xl border-2 p-4 ${tone}`}>
      <p className="text-sm font-bold uppercase tracking-wider text-muted">{label}</p>
      <p className="truncate text-xl font-extrabold text-ink">{name}</p>
    </div>
  );
}

function Scoreboard({ players, scores, highlight }: { players: [string, string]; scores: [number, number]; highlight: number | null }) {
  return (
    <div role="group" aria-label="Scores" className="grid grid-cols-2 gap-3">
      {players.map((name, i) => (
        <div key={i} className={`rounded-2xl border-2 p-3 text-center ${i === highlight ? "border-plum-300 bg-plum-50" : "border-plum-100 bg-surface"}`}>
          <p className="truncate text-sm font-semibold text-muted">{name}</p>
          <p className="text-2xl font-extrabold text-plum-800">{scores[i]}</p>
        </div>
      ))}
    </div>
  );
}

/** The speaking clock: big numbers, start and pause. */
function Clock({ countdown }: { countdown: ReturnType<typeof useCountdown> }) {
  const { left, running, finished, start, pause, reset, seconds } = countdown;
  return (
    <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl bg-plum-50 p-4">
      <span role="timer" aria-label="Time left" className={`text-5xl font-extrabold tabular-nums ${finished ? "text-coral-600" : "text-plum-800"}`}>
        {formatClock(left)}
      </span>
      {running ? (
        <button type="button" onClick={pause} className={secondary}><Pause aria-hidden className="size-5" /> Pause</button>
      ) : (
        <button type="button" onClick={start} disabled={finished} className={primary}>
          <Play aria-hidden className="size-5" /> {left < seconds && left > 0 ? "Resume" : "Start the clock"}
        </button>
      )}
      <button type="button" onClick={reset} className={quiet}><RotateCcw aria-hidden className="size-5" /> Restart</button>
      <p role="status" className="min-w-24 text-xl font-extrabold text-coral-600">{finished ? "Time's up!" : ""}</p>
    </div>
  );
}

function Final({ state, onReplay, onSetup }: { state: debate.DebateState; onReplay: () => void; onSetup: () => void }) {
  const result = debate.winner(state);
  const { players, scores } = state;
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{result === "tie" ? "It's a tie!" : `${players[result]} wins the debate!`}</h2>
      <p className="mx-auto mt-2 max-w-md text-lg text-muted">
        {result === "tie" ? "Evenly matched. Time for a tiebreaker?" : "Best argued across the rounds, by the room's votes."}
      </p>
      <div role="group" aria-label="Final scores" className="mx-auto mt-6 grid max-w-md grid-cols-2 gap-3">
        {players.map((name, i) => (
          <div key={i} className={`rounded-2xl p-4 ${result === i ? "bg-plum-100" : "bg-plum-50"}`}>
            <p className="text-4xl font-extrabold text-plum-800">{scores[i]}</p>
            <p className="truncate text-sm font-semibold text-muted">{name}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={onReplay} className={primary}><RotateCcw aria-hidden className="size-5" /> Debate again</button>
        <button type="button" onClick={onSetup} className={secondary}>Change players or time</button>
      </div>
    </div>
  );
}
