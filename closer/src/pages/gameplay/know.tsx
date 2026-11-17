import { Check, X } from "lucide-react";
import { useId, useState } from "react";
import { QuestionCard } from "../../components/QuestionCard";
import { ChoiceGrid, FinalScreen, GameShell, Handoff, panel, PlayerSetup, Prompt, Scoreboard, Select, Stage, TurnLabel, Verdict, field, useDeck } from "../../components/games/kit";
import { primary, quiet, secondary } from "../../components/ui";
import { gameById } from "../../data/games";
import { compatibilityQuestions, matchPrompts, memoryLane, thisOrThat, type ChoicePrompt } from "../../data/games/know";
import { pickMany } from "../../utils/games/deck";
import { compatLabel, matchPercent } from "../../utils/games/matching";
import { joinNames, nextSeat } from "../../utils/games/players";
import { award, leaders } from "../../utils/games/scores";
import { shuffle } from "../../utils/shuffle";

/** One person (or the group) works through a list of this-or-that questions, one screen each, and
 *  hands back the picks. The picks are held only until the game moves on. */
function AnswerRun({ prompts, eyebrow, hint, lockLabel = "Lock in my answer", onDone }: {
  prompts: readonly ChoicePrompt[]; eyebrow: string; hint?: string; lockLabel?: string; onDone: (picks: number[]) => void;
}) {
  const [i, setI] = useState(0);
  const [picks, setPicks] = useState<number[]>([]);
  const [choice, setChoice] = useState<number | null>(null);
  const prompt = prompts[i]!;
  const last = i + 1 >= prompts.length;
  const lock = () => {
    if (choice === null) return;
    const next = [...picks, choice];
    if (last) { onDone(next); return; }
    setPicks(next); setChoice(null); setI(i + 1);
  };
  return (
    <Stage focusKey={`q${i}`}>
      <QuestionCard eyebrow={<>{eyebrow}{prompts.length > 1 && <span className="text-muted">Question {i + 1} of {prompts.length}</span>}</>} text={prompt.text}>
        {hint && <p className="mt-3 text-muted">{hint}</p>}
        <ChoiceGrid options={prompt.options} chosen={choice} onChoose={setChoice} />
        <button type="button" disabled={choice === null} onClick={lock} className={`${primary} mt-5 w-full sm:w-auto`}>{last ? lockLabel : "Lock in and continue"}</button>
      </QuestionCard>
    </Stage>
  );
}

/** A table of two answers per question: used at the reveal of Match Game and the Compatibility Quiz. */
function Compare({ prompts, aName, bName, a, b }: { prompts: readonly ChoicePrompt[]; aName: string; bName: string; a: readonly number[]; b: readonly number[] }) {
  return (
    <ul className="mt-5 space-y-3 text-left">
      {prompts.map((p, i) => {
        const same = a[i] === b[i];
        return (
          <li key={p.text} className={`rounded-2xl border-2 p-3 ${same ? "border-emerald-500 bg-emerald-50" : "border-plum-100 bg-surface"}`}>
            <p className="flex items-center gap-2 text-sm font-semibold text-muted">
              {same ? <Check aria-hidden className="size-4 text-emerald-700" /> : <X aria-hidden className="size-4 text-coral-700" />}
              {p.text} <span className="sr-only">{same ? "Same answer" : "Different answers"}</span>
            </p>
            <p className="mt-1 font-bold">{aName}: {p.options[a[i]!]} <span className="font-normal text-muted">·</span> {bName}: {p.options[b[i]!]}</p>
          </li>
        );
      })}
    </ul>
  );
}

// ---------------------------------------------------------------- How Well Do You Know Me?

const KNOW_QUESTIONS = 5;

export function HowWellDoYouKnowMe() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("how-well-do-you-know-me")!} focusKey={names ? "play" : "setup"}>
      {names ? <KnowPlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={2} max={6} start={3} onStart={setNames}
          rules={[`One person takes the hot seat and secretly answers ${KNOW_QUESTIONS} this-or-that questions.`, "Everyone else looks away, then guesses those answers together.", "Every right guess scores for the person in the hot seat. Then it is the next person's turn."]} />
      )}
    </GameShell>
  );
}

type KnowPhase = "handoff-answer" | "answer" | "handoff-guess" | "guess" | "reveal";

function KnowPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const [subject, setSubject] = useState(0);
  const [phase, setPhase] = useState<KnowPhase>("handoff-answer");
  const [prompts, setPrompts] = useState<ChoicePrompt[]>(() => pickMany(thisOrThat, KNOW_QUESTIONS));
  const [secret, setSecret] = useState<number[]>([]);
  const [guesses, setGuesses] = useState<number[]>([]);
  const [known, setKnown] = useState<number[]>(() => names.map(() => 0));
  const [done, setDone] = useState(false);
  const who = names[subject]!;
  const others = joinNames(names.filter((_, i) => i !== subject));

  const next = () => {
    if (subject + 1 >= names.length) { setDone(true); return; }
    setSubject(subject + 1); setPhase("handoff-answer"); setPrompts(pickMany(thisOrThat, KNOW_QUESTIONS));
  };
  const replay = () => { setKnown(names.map(() => 0)); setSubject(0); setPhase("handoff-answer"); setDone(false); setPrompts(pickMany(thisOrThat, KNOW_QUESTIONS)); };

  if (done) {
    const top = leaders(known);
    const all = top.length === names.length;
    return <FinalScreen headline={all ? "You all know each other equally well!" : `${joinNames(top.map((i) => names[i]!))} ${top.length === 1 ? "is" : "are"} the best known!`}
      text="Scores show how many of each person's answers the others guessed." names={names} scores={known} unit={`out of ${KNOW_QUESTIONS}`} onReplay={replay} onSetup={onSetup} />;
  }
  return (
    <Stage focusKey={`${subject}-${phase}`}>
      <Scoreboard names={names} values={known} highlight={subject} label="Known so far" />
      <div className="mt-5">
        {phase === "handoff-answer" && (
          <Handoff title={`${who} is in the hot seat`} text={`Pass the phone to ${who}. ${others}, look away: ${who} answers ${KNOW_QUESTIONS} questions in secret.`}
            button={`I'm ${who}, show the questions`} onReady={() => setPhase("answer")} />
        )}
        {phase === "answer" && (
          <AnswerRun prompts={prompts} eyebrow={`${who}: your answers, in secret`} hint={`Pick what is true for you. ${others} will try to guess.`}
            onDone={(p) => { setSecret(p); setPhase("handoff-guess"); }} />
        )}
        {phase === "handoff-guess" && (
          <Handoff locked title="Answers locked and hidden" text={`Pass the phone to ${others}. ${who}, look away, no hints! You guess ${who}'s answers together.`}
            button="We're ready to guess" onReady={() => setPhase("guess")} />
        )}
        {phase === "guess" && (
          <AnswerRun prompts={prompts} eyebrow={`Guess ${who}'s answers`} hint={`Talk it over, then one of you taps what ${who} picked.`} lockLabel="Lock in our last guess"
            onDone={(g) => { setGuesses(g); setKnown((k) => award(k, subject, g.filter((x, i) => x === secret[i]).length)); setPhase("reveal"); }} />
        )}
        {phase === "reveal" && (
          <div className={`${panel} text-center`}>
            <h2 className="text-2xl font-extrabold sm:text-3xl">{guesses.filter((g, i) => g === secret[i]).length} of {KNOW_QUESTIONS} guessed right</h2>
            <Compare prompts={prompts} aName={`${who} picked`} bName="You guessed" a={secret} b={guesses} />
            <button type="button" onClick={next} className={`${primary} mt-6`}>{subject + 1 >= names.length ? "See the scores" : `Next: ${names[subject + 1]}`}</button>
          </div>
        )}
      </div>
    </Stage>
  );
}

// ---------------------------------------------------------------- Match Game (two ways to play)

const MATCH_ROUNDS = 8;
const COMPAT_QUESTIONS = 12;

type MatchMode = "live" | "percent";
const matchModes = [
  { value: "live" as MatchMode, label: `Reveal after each question (${MATCH_ROUNDS} questions)` },
  { value: "percent" as MatchMode, label: `Percentage at the end (${COMPAT_QUESTIONS} questions)` },
];

export function MatchGame() {
  const [play, setPlay] = useState<{ names: string[]; mode: MatchMode } | null>(null);
  const [mode, setMode] = useState<MatchMode>("live");
  return (
    <GameShell game={gameById("match-game")!} focusKey={play ? "play" : "setup"}>
      {play ? (play.mode === "live" ? <MatchPlay names={play.names} onSetup={() => setPlay(null)} /> : <CompatPlay names={play.names} onSetup={() => setPlay(null)} />) : (
        <PlayerSetup min={2} max={2} onStart={(names) => setPlay({ names, mode })}
          rules={["Two players answer the same questions, each in secret.", "Reveal after each question: you see every match as you go. Percentage at the end: you answer them all, then get one compatibility score.", "Matching answers score. It is only a game, so every result is a kind one."]}
          extra={<Select label="How to play" value={mode} options={matchModes} onChange={setMode} />} />
      )}
    </GameShell>
  );
}

function MatchPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const [round, setRound] = useState(0);
  const [prompts, setPrompts] = useState(() => pickMany(matchPrompts, MATCH_ROUNDS));
  const [phase, setPhase] = useState<"a" | "handoff" | "b" | "reveal">("a");
  const [first, setFirst] = useState<number[]>([]);
  const [second, setSecond] = useState<number[]>([]);
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);
  const [aName, bName] = [names[0]!, names[1]!];
  const prompt = prompts[round]!;
  const matched = first[0] === second[0];

  const replay = () => { setRound(0); setPrompts(pickMany(matchPrompts, MATCH_ROUNDS)); setPhase("a"); setScore(0); setDone(false); };
  if (done) {
    const pct = Math.round((score / MATCH_ROUNDS) * 100);
    return (
      <div className={`${panel} text-center sm:p-12`}>
        <h2 className="text-3xl font-extrabold">{score} of {MATCH_ROUNDS} matched</h2>
        <p className="mt-2 text-lg text-muted">{pct >= 75 ? "You think alike!" : pct >= 40 ? "A nice mix of alike and different." : "Very different answers. That is what makes it fun."}</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <button type="button" onClick={replay} className={primary}>Play again</button>
          <button type="button" onClick={onSetup} className={secondary}>Change names</button>
        </div>
      </div>
    );
  }
  return (
    <Stage focusKey={`${round}-${phase}`}>
      <Scoreboard names={["Matches", "Round"]} values={[score, `${round + 1} of ${MATCH_ROUNDS}`]} label="Progress" />
      <div className="mt-5">
        {phase === "a" && <AnswerRun key={`a${round}`} prompts={[prompt]} eyebrow={`${aName}: pick in secret, ${bName} look away`} hint="Pick the one that is most like you. No hints!"
          onDone={(p) => { setFirst(p); setPhase("handoff"); }} />}
        {phase === "handoff" && <Handoff locked title="Answer locked" text={`Pass the phone to ${bName}. ${aName}, look away.`} button={`I'm ${bName}, show the question`} onReady={() => setPhase("b")} />}
        {phase === "b" && <AnswerRun key={`b${round}`} prompts={[prompt]} eyebrow={`${bName}: pick your own answer`}
          onDone={(p) => { setSecond(p); if (p[0] === first[0]) setScore((s) => s + 1); setPhase("reveal"); }} />}
        {phase === "reveal" && (
          <QuestionCard eyebrow="The reveal" text={prompt.text}>
            <Compare prompts={[prompt]} aName={aName} bName={bName} a={first} b={second} />
            <Verdict good={matched}>{matched ? "A match! You both score." : "No match this time."}</Verdict>
            <button type="button" onClick={() => { if (round + 1 >= MATCH_ROUNDS) setDone(true); else { setRound(round + 1); setPhase("a"); } }} className={`${primary} mt-5 w-full sm:w-auto`}>
              {round + 1 >= MATCH_ROUNDS ? "See the result" : "Next question"}
            </button>
          </QuestionCard>
        )}
      </div>
    </Stage>
  );
}

// ---------------------------------------------------------------- Match Game, percentage at the end

function CompatPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const [prompts, setPrompts] = useState(() => pickMany(compatibilityQuestions, COMPAT_QUESTIONS));
  const [phase, setPhase] = useState<"handoff-a" | "a" | "handoff-b" | "b" | "result">("handoff-a");
  const [a, setA] = useState<number[]>([]);
  const [b, setB] = useState<number[]>([]);
  const [aName, bName] = [names[0]!, names[1]!];
  const replay = () => { setPrompts(pickMany(compatibilityQuestions, COMPAT_QUESTIONS)); setPhase("handoff-a"); };
  const pct = matchPercent(a, b);
  return (
    <Stage focusKey={phase}>
      {phase === "handoff-a" && <Handoff title={`${aName}, you're first`} text={`${bName}, look away while ${aName} answers all ${COMPAT_QUESTIONS} questions. Pick what is most true for you.`} button={`I'm ${aName}, start`} onReady={() => setPhase("a")} />}
      {phase === "a" && <AnswerRun prompts={prompts} eyebrow={aName} onDone={(p) => { setA(p); setPhase("handoff-b"); }} />}
      {phase === "handoff-b" && <Handoff locked title="Answers locked" text={`Pass the phone to ${bName}. ${aName}, look away while ${bName} answers the same questions.`} button={`I'm ${bName}, start`} onReady={() => setPhase("b")} />}
      {phase === "b" && <AnswerRun prompts={prompts} eyebrow={bName} onDone={(p) => { setB(p); setPhase("result"); }} />}
      {phase === "result" && (
        <div className={`${panel} text-center sm:p-12`}>
          <p className="text-sm font-bold uppercase tracking-wider text-coral-700">{aName} and {bName}</p>
          <p className="mt-3 text-6xl font-extrabold text-plum-700 dark:text-onplum-soft">{pct}%</p>
          <h2 className="mt-2 text-2xl font-extrabold">{compatLabel(pct)}</h2>
          <p className="mt-2 text-muted">{a.filter((x, i) => x === b[i]).length} of {COMPAT_QUESTIONS} answers matched.</p>
          <Compare prompts={prompts} aName={aName} bName={bName} a={a} b={b} />
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <button type="button" onClick={replay} className={primary}>Try new questions</button>
            <button type="button" onClick={onSetup} className={secondary}>Change names</button>
          </div>
        </div>
      )}
    </Stage>
  );
}

// ---------------------------------------------------------------- Memory Lane

export function MemoryLane() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("memory-lane")!} focusKey={names ? "play" : "setup"}>
      {names ? <LanePlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={2} max={2} onStart={setNames}
          rules={["A \"remember…\" prompt appears.", "One of you tells your version of it, then the other tells theirs.", "Tap Next memory when you are ready. The one who starts changes each time."]} />
      )}
    </GameShell>
  );
}

function LanePlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const deck = useDeck(memoryLane);
  const [prompt, setPrompt] = useState(() => deck.draw());
  const [first, setFirst] = useState(0);
  const [n, setN] = useState(1);
  const second = nextSeat(first, 2);
  return (
    <Stage focusKey={String(n)}>
      <div className={panel}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Memory {n}</p>
        <Prompt small>{prompt}</Prompt>
        <p className="mt-5 text-lg text-muted"><span className="font-extrabold text-ink">{names[first]}</span> goes first, then <span className="font-extrabold text-ink">{names[second]}</span>.</p>
        <button type="button" onClick={() => { setPrompt(deck.draw()); setFirst(second); setN(n + 1); }} className={`${primary} mt-6 w-full sm:w-auto`}>Next memory</button>
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>Finish</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- Two Truths and a Lie

export function TwoTruthsAndALie() {
  const [names, setNames] = useState<string[] | null>(null);
  return (
    <GameShell game={gameById("two-truths-and-a-lie")!} focusKey={names ? "play" : "setup"}>
      {names ? <TruthsPlay names={names} onSetup={() => setNames(null)} /> : (
        <PlayerSetup min={3} max={8} start={4} onStart={setNames}
          rules={["On your turn, type three statements about yourself: two true, one a lie. Mark the lie.", "Pass the phone to the group. They vote on which one is the lie.", "Fool the group and you score a point."]} />
      )}
    </GameShell>
  );
}

type TruthsPhase = "handoff" | "write" | "vote" | "reveal";

function TruthsPlay({ names, onSetup }: { names: string[]; onSetup: () => void }) {
  const [author, setAuthor] = useState(0);
  const [phase, setPhase] = useState<TruthsPhase>("handoff");
  const [lines, setLines] = useState<{ text: string; lie: boolean }[]>([]);
  const [vote, setVote] = useState<number | null>(null);
  const [scores, setScores] = useState<number[]>(() => names.map(() => 0));
  const [done, setDone] = useState(false);
  const who = names[author]!;
  const lieAt = lines.findIndex((l) => l.lie);
  const fooled = vote !== null && vote !== lieAt;

  const advance = () => {
    if (author + 1 >= names.length) { setDone(true); return; }
    setAuthor(author + 1); setPhase("handoff"); setLines([]); setVote(null);
  };
  if (done) {
    return <FinalScreen text="Points are for fooling the group." names={names} scores={scores} unit="times fooled the group"
      onReplay={() => { setScores(names.map(() => 0)); setAuthor(0); setPhase("handoff"); setLines([]); setVote(null); setDone(false); }} onSetup={onSetup} />;
  }
  return (
    <Stage focusKey={`${author}-${phase}`}>
      <Scoreboard names={names} values={scores} highlight={author} label="Times fooled the group" />
      <div className="mt-5">
        {phase === "handoff" && <Handoff title={`${who}'s turn`} text={`Pass the phone to ${who}. Everyone else, look away while ${who} writes.`} button={`I'm ${who}, let me write`} onReady={() => setPhase("write")} />}
        {phase === "write" && <WriteThree name={who} onDone={(l) => { setLines(shuffle(l)); setVote(null); setPhase("vote"); }} />}
        {phase === "vote" && (
          <QuestionCard eyebrow={`${who}'s three statements`} text="Which one is the lie?">
            <p className="mt-3 text-muted">Talk it over, then one of you taps the group's choice.</p>
            <ChoiceGrid columns={1} options={lines.map((l) => l.text)} chosen={vote} onChoose={setVote} />
            <button type="button" disabled={vote === null} onClick={() => { if (vote !== null && vote !== lieAt) setScores((s) => award(s, author)); setPhase("reveal"); }} className={`${primary} mt-5 w-full sm:w-auto`}>Lock in our guess</button>
          </QuestionCard>
        )}
        {phase === "reveal" && (
          <QuestionCard eyebrow="The reveal" text={`The lie was: ${lines[lieAt]?.text}`}>
            <ChoiceGrid columns={1} options={lines.map((l) => l.text)} chosen={vote} onChoose={() => undefined} disabled mark={(i) => (i === lieAt ? "right" : undefined)} />
            <Verdict good={!fooled}>{fooled ? `${who} fooled the group and scores a point!` : "The group spotted it."}</Verdict>
            <button type="button" onClick={advance} className={`${primary} mt-5 w-full sm:w-auto`}>{author + 1 >= names.length ? "See the scores" : `Next: ${names[author + 1]}`}</button>
          </QuestionCard>
        )}
      </div>
    </Stage>
  );
}

/** The private form: three statements and which one is the lie. */
function WriteThree({ name, onDone }: { name: string; onDone: (lines: { text: string; lie: boolean }[]) => void }) {
  const id = useId();
  const [text, setText] = useState(["", "", ""]);
  const [lie, setLie] = useState<number | null>(null);
  const ready = text.every((t) => t.trim()) && lie !== null;
  return (
    <form className={panel} onSubmit={(e) => { e.preventDefault(); if (ready) onDone(text.map((t, i) => ({ text: t.trim(), lie: i === lie }))); }}>
      <TurnLabel name={name} />
      <h2 className="mt-3 text-2xl font-extrabold">Write two truths and one lie</h2>
      {text.map((t, i) => (
        <div key={i} className="mt-4">
          <label htmlFor={`${id}-${i}`} className="text-sm font-semibold text-muted">Statement {i + 1}</label>
          <input id={`${id}-${i}`} type="text" maxLength={140} value={t} autoComplete="off" className={field}
            onChange={(e) => setText((x) => x.map((v, j) => (j === i ? e.target.value : v)))} />
          <label className="mt-2 flex min-h-11 cursor-pointer items-center gap-2 font-semibold">
            <input type="radio" name={`${id}-lie`} checked={lie === i} onChange={() => setLie(i)} className="size-5 accent-plum-600" /> This one is the lie
          </label>
        </div>
      ))}
      <p className="mt-3 text-sm text-muted">Nothing you type is saved. It disappears when the turn ends.</p>
      <button type="submit" disabled={!ready} className={`${primary} mt-4 w-full sm:w-auto`}>Lock them in</button>
    </form>
  );
}
