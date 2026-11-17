import { Bomb, Check, Hand, SkipForward } from "lucide-react";
import { useEffect, useState } from "react";
import { FinalScreen, GameShell, panel, PlayerSetup, Prompt, Scoreboard, Select, Stage, TurnLabel, Verdict, useDeck } from "../../components/games/kit";
import { primary, quiet, secondary } from "../../components/ui";
import { useCountdown } from "../../hooks";
import { gameById } from "../../data/games";
import { dares, lastWordTopics, mostLikelyTo, neverHaveIEver, rapidFire } from "../../data/games/party";
import { spiceLabels, truthPool, type Spice } from "../../data/games/pools";
import { fuseSeconds, FUSE_RANGES, type FuseLength } from "../../utils/games/bomb";
import { award } from "../../utils/games/scores";
import { createRoster, isOver, loseLife, nextIn, stillIn, winner, type Roster } from "../../utils/games/roster";
import { nextSeat } from "../../utils/games/players";

const options = <T extends string>(labels: Record<T, string>) => (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value] }));

// ---------------------------------------------------------------- Truth or Dare

export function TruthOrDare() {
  const [play, setPlay] = useState<{ names: string[]; spice: Spice } | null>(null);
  const [spice, setSpice] = useState<Spice>("medium");
  return (
    <GameShell game={gameById("truth-or-dare")!} focusKey={play ? "play" : "setup"}>
      {play ? <TruthOrDarePlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={2} max={8} start={3}
          rules={["On your turn, choose Truth or Dare.", "Truth is a question from the library. Dare is a short, silly task.", "Do it, then pass the phone on. Skip any you don't want."]}
          extra={<Select label="How bold" value={spice} options={options(spiceLabels)} onChange={setSpice} />}
          onStart={(names) => setPlay({ names, spice })} />
      )}
    </GameShell>
  );
}

function TruthOrDarePlay({ names, spice, onSetup }: { names: string[]; spice: Spice; onSetup: () => void }) {
  const truths = useDeck(truthPool(spice));
  const dareDeck = useDeck(dares);
  const [turn, setTurn] = useState(0);
  const [taken, setTaken] = useState(0);
  const [card, setCard] = useState<{ kind: "truth" | "dare"; text: string } | null>(null);
  const draw = (kind: "truth" | "dare") => setCard({ kind, text: (kind === "truth" ? truths : dareDeck).draw() });
  const next = () => { setCard(null); setTurn((t) => nextSeat(t, names.length)); setTaken((n) => n + 1); };
  return (
    <Stage focusKey={`${turn}-${taken}-${card?.kind ?? "choose"}`}>
      <div className={panel}>
        <TurnLabel name={names[turn]!}>Turn {taken + 1}</TurnLabel>
        {!card ? (
          <>
            <Prompt>Truth or dare?</Prompt>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <button type="button" onClick={() => draw("truth")} className={`${primary} min-h-20 text-xl`}>Truth</button>
              <button type="button" onClick={() => draw("dare")} className={`${primary} min-h-20 bg-coral-600 text-xl hover:bg-coral-700`}>Dare</button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-4 inline-flex rounded-full bg-plum-100 px-4 py-1 text-sm font-extrabold uppercase tracking-wider text-plum-800">{card.kind}</p>
            <Prompt small>{card.text}</Prompt>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button type="button" onClick={next} className={primary}><Check aria-hidden className="size-5" /> Done, next player</button>
              <button type="button" onClick={() => draw(card.kind)} className={secondary}><SkipForward aria-hidden className="size-5" /> Give me another</button>
            </div>
          </>
        )}
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>End the game</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- Never Have I Ever

const FINGERS = 3;

export function NeverHaveIEver() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("never-have-i-ever")!} focusKey={names ? "play" : "setup"}>
      {names ? <NeverPlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={2} max={8} start={3} onStart={setNames}
          rules={["Everyone starts with three fingers up.", "A statement appears. Tap everyone who HAS done it.", "They put a finger down. Last one with fingers up wins."]} />
      )}
    </GameShell>
  );
}

function NeverPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const deck = useDeck(neverHaveIEver);
  const [roster, setRoster] = useState<Roster>(() => createRoster(names, FINGERS));
  const [statement, setStatement] = useState(() => deck.draw());
  const [done, setDone] = useState<number[]>([]);
  const [round, setRound] = useState(1);
  const [finished, setFinished] = useState(false);
  const restart = () => { setRoster(createRoster(names, FINGERS)); setDone([]); setRound(1); setFinished(false); setStatement(deck.draw()); };
  const next = () => {
    const after = done.reduce((r, i) => loseLife(r, i), roster);
    setRoster(after); setDone([]);
    if (isOver(after)) { setFinished(true); return; }
    setStatement(deck.draw()); setRound((n) => n + 1);
  };
  if (finished) {
    const w = winner(roster);
    return <FinalScreen headline={w === null ? "Everyone went down together!" : `${names[w]} wins!`} text={w === null ? "Nobody has any fingers left." : "The last one with fingers up."}
      names={names} scores={roster.lives} unit="fingers left" onReplay={restart} onSetup={onSetup} />;
  }
  return (
    <Stage focusKey={`r${round}`}>
      <Scoreboard names={names} values={roster.lives} label="Fingers left" />
      <div className={`${panel} mt-5`}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Statement {round}</p>
        <Prompt>{statement}</Prompt>
        <p className="mt-4 text-muted">Tap everyone who has done it.</p>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {names.map((name, i) => {
            const out = (roster.lives[i] ?? 0) <= 0;
            const on = done.includes(i);
            return (
              <li key={i}>
                <button type="button" aria-pressed={on} disabled={out}
                  onClick={() => setDone((d) => (on ? d.filter((x) => x !== i) : [...d, i]))}
                  className={`flex min-h-14 w-full cursor-pointer items-center justify-between gap-2 rounded-2xl border-2 px-4 font-bold transition disabled:cursor-not-allowed disabled:opacity-40 ${on ? "border-coral-500 bg-coral-50 text-coral-700" : "border-plum-100 bg-surface hover:border-plum-300"}`}>
                  <span className="truncate">{name}</span>
                  <span className="text-sm">{out ? "Out" : on ? "Has done it" : ""}</span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={next} className={primary}>{done.length ? `Put ${done.length === 1 ? "a finger" : "fingers"} down, next` : "Nobody, next statement"}</button>
          <button type="button" onClick={() => setFinished(true)} className={secondary}>End the game</button>
        </div>
      </div>
    </Stage>
  );
}

// ---------------------------------------------------------------- Pass the Bomb

const BOMB_LIVES = 3;

interface BombState {
  roster: Roster;
  holder: number;
  phase: "ready" | "burning" | "boom" | "over";
  question: string;
  /** Changes with every lit fuse, so a new fuse starts a new timer. */
  fuse: number;
  seconds: number;
}

export function PassTheBomb() {
  const [play, setPlay] = useState<{ names: string[]; length: FuseLength } | null>(null);
  const [length, setLength] = useState<FuseLength>("medium");
  const lengths = { short: `Short (about ${FUSE_RANGES.short.min} to ${FUSE_RANGES.short.max} seconds)`, medium: `Medium (about ${FUSE_RANGES.medium.min} to ${FUSE_RANGES.medium.max} seconds)`, long: `Long (about ${FUSE_RANGES.long.min} to ${FUSE_RANGES.long.max} seconds)` };
  return (
    <GameShell game={gameById("pass-the-bomb")!} focusKey={play ? "play" : "setup"}>
      {play ? <BombPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={2} max={8} start={4}
          rules={["Light the fuse, then pass the phone round the group. Nobody knows how long it is.", "Whoever holds it when it goes off loses a life and answers a question.", "Three lives each. The last one standing wins."]}
          extra={<Select label="Fuse" value={length} options={options(lengths)} onChange={setLength} />}
          onStart={(names) => setPlay({ names, length })} />
      )}
    </GameShell>
  );
}

function BombPlay({ names, length, onSetup }: { names: string[]; length: FuseLength; onSetup: () => void }) {
  const questions = useDeck(truthPool("medium"));
  const fresh = (): BombState => ({ roster: createRoster(names, BOMB_LIVES), holder: 0, phase: "ready", question: "", fuse: 0, seconds: 0 });
  const [s, setS] = useState<BombState>(fresh);

  useEffect(() => {
    if (s.phase !== "burning") return;
    const id = window.setTimeout(() => setS((b) => (b.phase !== "burning" ? b : { ...b, phase: "boom", roster: loseLife(b.roster, b.holder) })), s.seconds * 1000);
    return () => window.clearTimeout(id);
  }, [s.phase, s.fuse, s.seconds]);
  useEffect(() => { if (s.phase === "boom") navigator.vibrate?.([200, 80, 300]); }, [s.phase]);

  const light = () => setS((b) => ({ ...b, phase: "burning", fuse: b.fuse + 1, seconds: fuseSeconds(FUSE_RANGES[length].min, FUSE_RANGES[length].max), question: questions.draw() }));
  const pass = () => setS((b) => ({ ...b, holder: nextIn(b.roster, b.holder) ?? b.holder }));
  const carryOn = () => setS((b) => (isOver(b.roster) ? { ...b, phase: "over" } : { ...b, phase: "ready", holder: nextIn(b.roster, b.holder) ?? b.holder }));

  if (s.phase === "over") {
    const w = winner(s.roster);
    return <FinalScreen headline={w === null ? "Nobody is left standing!" : `${names[w]} wins!`} names={names} scores={s.roster.lives} unit="lives left"
      onReplay={() => setS(fresh())} onSetup={onSetup} />;
  }
  const holder = names[s.holder]!;
  const upNext = names[nextIn(s.roster, s.holder) ?? s.holder]!;
  return (
    <Stage focusKey={`${s.phase}-${s.fuse}-${s.holder}`}>
      <Scoreboard names={names} values={s.roster.lives} highlight={s.holder} label="Lives left" />
      <div className={`${panel} mt-5 text-center`}>
        {s.phase === "ready" && (
          <>
            <Bomb aria-hidden className="mx-auto size-16 text-plum-700 dark:text-onplum-soft" />
            <h2 className="mt-4 text-2xl font-extrabold sm:text-3xl">{holder} has the bomb</h2>
            <p className="mx-auto mt-2 max-w-md text-lg text-muted">Light the fuse, then keep the phone moving. Nobody knows when it goes off.</p>
            <button type="button" onClick={light} className={`${primary} mt-6`}>Light the fuse</button>
          </>
        )}
        {s.phase === "burning" && (
          <>
            <Bomb aria-hidden className="mx-auto size-20 text-coral-600 motion-safe:animate-pulse" />
            <h2 className="mt-4 text-3xl font-extrabold">{holder} has it. Quick!</h2>
            <p className="mx-auto mt-2 max-w-md text-lg text-muted">Pass the phone to {upNext}, then tap the button.</p>
            <button type="button" onClick={pass} className={`${primary} mt-6 min-h-20 w-full text-xl`}>Passed to {upNext}</button>
          </>
        )}
        {s.phase === "boom" && (
          <>
            <p role="status" className="text-5xl font-extrabold text-coral-600">BOOM!</p>
            <h2 className="mt-3 text-2xl font-extrabold sm:text-3xl">{holder} was holding it</h2>
            <p className="mt-2 text-muted">{(s.roster.lives[s.holder] ?? 0) > 0 ? `${s.roster.lives[s.holder]} ${s.roster.lives[s.holder] === 1 ? "life" : "lives"} left. Answer this:` : "That was the last life. Answer this one last question:"}</p>
            <Prompt small>{s.question}</Prompt>
            <button type="button" onClick={carryOn} className={`${primary} mt-6`}>{stillIn(s.roster).length <= 1 ? "See who won" : "Answered, next bomb"}</button>
          </>
        )}
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>End the game</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- Most Likely To

export function MostLikelyTo() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("most-likely-to")!} focusKey={names ? "play" : "setup"}>
      {names ? <LikelyPlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={3} max={10} start={4} onStart={setNames}
          rules={["A \"who is most likely to…\" prompt appears.", "On three, everyone points at the person they pick.", "Tap who got the most fingers. The phone keeps count."]} />
      )}
    </GameShell>
  );
}

function LikelyPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const deck = useDeck(mostLikelyTo);
  const [prompt, setPrompt] = useState(() => deck.draw());
  const [tally, setTally] = useState<number[]>(() => names.map(() => 0));
  const [round, setRound] = useState(1);
  const [pointed, setPointed] = useState(false);
  const [finished, setFinished] = useState(false);
  const again = () => { setPrompt(deck.draw()); setRound((n) => n + 1); setPointed(false); };
  if (finished) {
    return <FinalScreen headline="The votes are in" text="Most fingers pointed at you across all the prompts." names={names} scores={tally} unit="times picked"
      onReplay={() => { setTally(names.map(() => 0)); setRound(1); setPointed(false); setFinished(false); setPrompt(deck.draw()); }} onSetup={onSetup} />;
  }
  return (
    <Stage focusKey={`${round}-${pointed}`}>
      <div className={panel}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Prompt {round}</p>
        <Prompt>{prompt}</Prompt>
        {!pointed ? (
          <button type="button" onClick={() => setPointed(true)} className={`${primary} mt-6 min-h-16 w-full text-xl sm:w-auto`}><Hand aria-hidden className="size-6" /> Everyone points!</button>
        ) : (
          <>
            <p className="mt-5 font-semibold text-muted">Who got the most fingers?</p>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2">
              {names.map((name, i) => (
                <li key={i}>
                  <button type="button" onClick={() => { setTally((t) => award(t, i)); again(); }}
                    className="flex min-h-14 w-full cursor-pointer items-center justify-between gap-2 rounded-2xl border-2 border-plum-100 bg-surface px-4 font-bold transition hover:border-plum-300">
                    <span className="truncate">{name}</span><span className="text-sm text-muted">{tally[i]} so far</span>
                  </button>
                </li>
              ))}
            </ul>
            <button type="button" onClick={again} className={`${secondary} mt-4`}>A tie, skip it</button>
          </>
        )}
      </div>
      <button type="button" onClick={() => setFinished(true)} className={`${quiet} mt-4`}>Finish and see the tally</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- Last Word

const THINK_SECONDS = 5;

export function LastWord() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("last-word")!} focusKey={names ? "play" : "setup"}>
      {names ? <LastWordPlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={2} max={8} start={3} onStart={setNames}
          rules={["A topic appears, like \"things in a kitchen\".", `Take turns saying one word that fits. You have ${THINK_SECONDS} seconds.`, "Hesitate or repeat a word and you are out. The last player wins the round."]} />
      )}
    </GameShell>
  );
}

function LastWordPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const topics = useDeck(lastWordTopics);
  const [topic, setTopic] = useState(() => topics.draw());
  const [roster, setRoster] = useState<Roster>(() => createRoster(names, 1));
  const [current, setCurrent] = useState(0);
  const [turn, setTurn] = useState(0);
  const [wins, setWins] = useState<number[]>(() => names.map(() => 0));
  const [over, setOver] = useState(false);
  const clock = useCountdown(THINK_SECONDS, turn);
  useEffect(() => { if (!over) clock.start(); }, [turn, over]);

  const said = () => { setCurrent((c) => nextIn(roster, c) ?? c); setTurn((t) => t + 1); };
  const knockOut = () => {
    const after = loseLife(roster, current);
    setRoster(after);
    if (isOver(after)) {
      const w = winner(after);
      if (w !== null) setWins((x) => award(x, w));
      setOver(true);
      return;
    }
    setCurrent(nextIn(after, current) ?? current);
    setTurn((t) => t + 1);
  };
  const nextTopic = () => { setTopic(topics.draw()); setRoster(createRoster(names, 1)); setCurrent(0); setTurn((t) => t + 1); setOver(false); };

  if (over) {
    const w = winner(roster);
    return <FinalScreen headline={w === null ? "Nobody left standing!" : `${names[w]} wins the round!`} names={names} scores={wins} unit="rounds won"
      onReplay={nextTopic} onSetup={onSetup} />;
  }
  const name = names[current]!;
  return (
    <Stage focusKey={`${topic}-${turn}`}>
      <Scoreboard names={names} values={roster.lives.map((l) => (l > 0 ? "In" : "Out"))} highlight={current} label="Who is still in" />
      <div className={`${panel} mt-5`}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Topic</p>
        <Prompt>{topic}</Prompt>
        <p className="mt-5 text-xl font-extrabold">{name}, your word!</p>
        <div aria-hidden className="mt-3 h-3 overflow-hidden rounded-full bg-plum-100">
          <div className={`h-full rounded-full transition-[width] duration-200 ease-linear ${clock.left <= 2 ? "bg-coral-500" : "bg-plum-500"}`} style={{ width: `${(clock.left / THINK_SECONDS) * 100}%` }} />
        </div>
        {clock.finished ? <Verdict good={false}>Time! {name} hesitated.</Verdict> : <p className="mt-2 text-sm text-muted">{clock.left} {clock.left === 1 ? "second" : "seconds"} left</p>}
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          {!clock.finished && <button type="button" onClick={said} className={primary}><Check aria-hidden className="size-5" /> They said a word</button>}
          <button type="button" onClick={knockOut} className={clock.finished ? primary : secondary}>{name} is out</button>
        </div>
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>End the game</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- Rapid Fire

const FIRE_SECONDS = 60;
const FIRE_QUESTIONS = 10;

export function RapidFire() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("rapid-fire")!} focusKey={names ? "play" : "setup"}>
      {names ? <FirePlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={1} max={6} start={2} onStart={setNames}
          rules={[`You get ${FIRE_QUESTIONS} questions in ${FIRE_SECONDS} seconds.`, "Answer each with one word only, out loud.", "Tap Right for a good quick answer, Skip if you can't. Most right answers wins."]} />
      )}
    </GameShell>
  );
}

function FirePlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const deck = useDeck(rapidFire);
  const [player, setPlayer] = useState(0);
  const [phase, setPhase] = useState<"ready" | "run" | "result" | "final">("ready");
  const [scores, setScores] = useState<number[]>(() => names.map(() => 0));
  const [asked, setAsked] = useState(0);
  const [question, setQuestion] = useState("");
  const [attempt, setAttempt] = useState(0);
  const clock = useCountdown(FIRE_SECONDS, attempt);
  useEffect(() => { if (phase === "run") clock.start(); }, [phase, attempt]);
  useEffect(() => { if (phase === "run" && clock.finished) setPhase("result"); }, [phase, clock.finished]);

  const begin = () => { setAsked(0); setAttempt((a) => a + 1); setQuestion(deck.draw()); setPhase("run"); };
  const answer = (right: boolean) => {
    if (right) setScores((s) => award(s, player));
    if (asked + 1 >= FIRE_QUESTIONS) { clock.pause(); setPhase("result"); return; }
    setAsked(asked + 1); setQuestion(deck.draw());
  };
  const move = () => { if (player + 1 >= names.length) setPhase("final"); else { setPlayer(player + 1); setPhase("ready"); } };
  const replay = () => { setScores(names.map(() => 0)); setPlayer(0); setPhase("ready"); };

  if (phase === "final") {
    return <FinalScreen headline={names.length === 1 ? `You got ${scores[0]} of ${FIRE_QUESTIONS}!` : undefined} names={names} scores={scores}
      unit={`right answers out of ${FIRE_QUESTIONS}`} onReplay={replay} onSetup={onSetup} />;
  }
  const name = names[player]!;
  return (
    <Stage focusKey={`${phase}-${player}`}>
      {names.length > 1 && <Scoreboard names={names} values={scores} highlight={player} />}
      {phase === "ready" && (
        <div className={`${panel} mt-5 text-center`}>
          <h2 className="text-2xl font-extrabold sm:text-3xl">{name}, are you ready?</h2>
          <p className="mx-auto mt-3 max-w-md text-lg text-muted">{FIRE_QUESTIONS} questions, {FIRE_SECONDS} seconds, one-word answers. The clock starts when you tap.</p>
          <button type="button" onClick={begin} className={`${primary} mt-6`}>Start the clock</button>
        </div>
      )}
      {phase === "run" && (
        <div className={`${panel} mt-5`}>
          <p className="flex items-center justify-between text-sm font-bold uppercase tracking-wider text-coral-700">
            <span>Question {asked + 1} of {FIRE_QUESTIONS}</span><span className="text-xl normal-case tracking-normal text-ink" aria-label={`${clock.left} seconds left`}>{clock.left}s</span>
          </p>
          <Prompt>{question}</Prompt>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button type="button" onClick={() => answer(true)} className={`${primary} min-h-16 text-lg`}><Check aria-hidden className="size-5" /> Right</button>
            <button type="button" onClick={() => answer(false)} className={`${secondary} min-h-16 text-lg`}><SkipForward aria-hidden className="size-5" /> Skip</button>
          </div>
        </div>
      )}
      {phase === "result" && (
        <div className={`${panel} mt-5 text-center`}>
          <h2 className="text-2xl font-extrabold sm:text-3xl">{name} got {scores[player]} right</h2>
          <p className="mt-2 text-lg text-muted">{clock.finished ? "Time's up." : "All ten done."}</p>
          <button type="button" onClick={move} className={`${primary} mt-6`}>{player + 1 >= names.length ? "See the scores" : `Pass to ${names[player + 1]}`}</button>
        </div>
      )}
    </Stage>
  );
}
