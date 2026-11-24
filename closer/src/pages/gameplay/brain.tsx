import { useEffect, useState } from "react";
import { QuestionCard } from "../../components/QuestionCard";
import { ChoiceGrid, FinalScreen, GameShell, PlayerSetup, Scoreboard, Select, Stage, Verdict, panel } from "../../components/games/kit";
import { primary, quiet } from "../../components/ui";
import { gameById } from "../../data/games";
import { claims, factGroups, priceItems } from "../../data/games/brain";
import { duelQuestions } from "../../data/games/pools";
import { inTopicGroup, topicGroups } from "../../data/triviaTopics";
import { pickMany } from "../../utils/games/deck";
import { resolveTap, type Seat } from "../../utils/games/duel";
import { formatValue, isRight, pickPair } from "../../utils/games/higherLower";
import { award } from "../../utils/games/scores";
import { triviaSeen } from "../../utils/seen";
import { shuffle } from "../../utils/shuffle";
import { planRound } from "../../utils/triviaRound";

// ---------------------------------------------------------------- Trivia Duel

const duelRoundChoices = [{ value: 5, label: "5 questions" }, { value: 10, label: "10 questions" }, { value: 15, label: "15 questions" }];
/** Easy to hard, but no Expert questions: a race is no fun when nobody knows the answer. */
const duelPool = duelQuestions.filter((q) => q.depth <= 3);
const duelTopics = [{ value: "all", label: "All topics" }, ...topicGroups.map((g) => ({ value: g.id, label: g.label }))];
/** The questions for one duel: new ones first, starting easy. */
const planDuel = (topic: string, rounds: number) =>
  planRound(duelPool.filter((q) => inTopicGroup(q, topic)), { length: rounds, seen: triviaSeen.all() });

export function TriviaDuel() {
  const [play, setPlay] = useState<{ names: string[]; rounds: number; topic: string } | null>(null);
  const [rounds, setRounds] = useState(10);
  const [topic, setTopic] = useState("all");
  return (
    <GameShell game={gameById("trivia-duel")!} focusKey={play ? "play" : "setup"}>
      {play ? <DuelPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={2} max={2} onStart={(names) => setPlay({ names, rounds, topic })} button="Start the duel"
          rules={["Lay the phone flat between you. Each player has their own four buttons.", "Tap your answer first. A right answer scores a point.", "Tap a wrong one and the point goes to the other player."]}
          extra={<><Select label="Topic" value={topic} options={duelTopics} onChange={setTopic} /><Select label="Length" value={rounds} options={duelRoundChoices} onChange={setRounds} /></>} />
      )}
    </GameShell>
  );
}

type DuelQuestion = (typeof duelQuestions)[number];

function Pad({ name, question, tap, seat, onTap, flipped }: {
  name: string; question: DuelQuestion; tap: { seat: Seat; choice: number } | null; seat: Seat; onTap: (choice: number) => void; flipped?: boolean;
}) {
  return (
    <section aria-label={`${name}'s answer buttons`} className={`rounded-3xl border-2 border-plum-100 bg-surface p-4 ${flipped ? "rotate-180" : ""}`}>
      <h3 className="text-center text-sm font-extrabold uppercase tracking-wider text-coral-700">{name}</h3>
      <p className="mt-1 text-center text-lg font-extrabold leading-snug">{question.text}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {question.options.map((option, i) => {
          const right = tap && i === question.answer;
          const wrong = tap && tap.seat === seat && tap.choice === i && i !== question.answer;
          return (
            <button key={option} type="button" disabled={tap !== null} onClick={() => onTap(i)}
              className={`min-h-14 cursor-pointer rounded-2xl border-2 px-2 py-2 text-[15px] font-bold leading-tight transition disabled:cursor-not-allowed ${
                right ? "border-emerald-500 bg-emerald-50" : wrong ? "border-coral-500 bg-coral-50" : "border-plum-100 bg-page hover:border-plum-300 disabled:opacity-60"}`}>
              {option}{right && <span className="sr-only"> (right answer)</span>}{wrong && <span className="sr-only"> (wrong)</span>}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DuelPlay({ names, rounds, topic, onSetup }: { names: string[]; rounds: number; topic: string; onSetup: () => void }) {
  const [questions, setQuestions] = useState(() => planDuel(topic, rounds));
  const [i, setI] = useState(0);
  const [tap, setTap] = useState<{ seat: Seat; choice: number } | null>(null);
  const [scores, setScores] = useState([0, 0]);
  const [done, setDone] = useState(false);
  const q = questions[i]!;
  useEffect(() => triviaSeen.add(q.id), [q.id]);
  const result = tap ? resolveTap(tap.seat, tap.choice === q.answer) : null;

  const press = (seat: Seat) => (choice: number) => {
    if (tap) return;
    setTap({ seat, choice });
    setScores((s) => award(s, resolveTap(seat, choice === q.answer).winner));
  };
  const replay = () => { setQuestions(planDuel(topic, rounds)); setI(0); setTap(null); setScores([0, 0]); setDone(false); };
  if (done) return <FinalScreen names={names} scores={scores} unit={`out of ${questions.length} questions`} onReplay={replay} onSetup={onSetup} />;

  return (
    <Stage focusKey={`${i}-${tap ? "answered" : "open"}`}>
      <Scoreboard names={names} values={scores} label="Scores" />
      <div className="mt-5 space-y-3">
        <Pad name={names[1]!} question={q} tap={tap} seat={1} onTap={press(1)} flipped />
        <div className={`${panel} p-4 text-center sm:p-6`}>
          <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Question {i + 1} of {questions.length}</p>
          {!result ? <p className="mt-1 text-muted">Tap first. A wrong answer gives the point away.</p> : (
            <>
              <Verdict good={!result.byMistake}>{result.byMistake ? `${names[tap!.seat]} tapped a wrong answer. ${names[result.winner]} scores.` : `${names[result.winner]} got it!`}</Verdict>
              <p className="mt-3 text-muted">{q.explanation}</p>
              <button type="button" onClick={() => { if (i + 1 >= questions.length) setDone(true); else { setI(i + 1); setTap(null); } }} className={`${primary} mt-4`}>
                {i + 1 >= questions.length ? "See the result" : "Next question"}
              </button>
            </>
          )}
        </div>
        <Pad name={names[0]!} question={q} tap={tap} seat={0} onTap={press(0)} />
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>End the duel</button>
    </Stage>
  );
}

// ---------------------------------------------------------------- One question each: Fact or Fiction, Higher or Lower, Guess the Price

interface QuizItem {
  /** Which kind of question this is, shown in the Mix. */
  tag: string;
  eyebrow?: string;
  prompt: string;
  sub?: string;
  options: readonly string[];
  answer: number;
  why: string;
}

const eachChoices = [{ value: 3, label: "3 turns each" }, { value: 5, label: "5 turns each" }, { value: 8, label: "8 turns each" }];

type QuizKind = "mix" | "fact" | "higher" | "price";
const kindChoices = [
  { value: "mix" as QuizKind, label: "Mix of all three" },
  { value: "fact" as QuizKind, label: "Fact or Fiction" },
  { value: "higher" as QuizKind, label: "Higher or Lower" },
  { value: "price" as QuizKind, label: "Guess the Price" },
];

/** The questions for a game: one kind, or a shuffled mix of all three. */
function buildQuiz(kind: QuizKind, count: number): QuizItem[] {
  if (kind === "fact") return factItems(count);
  if (kind === "higher") return higherLowerItems(count);
  if (kind === "price") return priceQuizItems(count);
  const each = Math.ceil(count / 3);
  return shuffle([...factItems(each), ...higherLowerItems(each), ...priceQuizItems(each)]).slice(0, count);
}

export function BrainQuiz() {
  const [play, setPlay] = useState<{ names: string[]; kind: QuizKind; each: number; items: QuizItem[] } | null>(null);
  const [kind, setKind] = useState<QuizKind>("mix");
  const [each, setEach] = useState(5);
  return (
    <GameShell game={gameById("brain-quiz")!} focusKey={play ? "play" : "setup"}>
      {play ? <QuizPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={1} max={6} start={2}
          rules={["Each turn is one question: is this fact true or made up, is the next number higher or lower, or which price is closest.", "The player whose turn it is picks an answer, then the phone shows the right one and why.", "A right answer scores a point."]}
          onStart={(names) => setPlay({ names, kind, each, items: buildQuiz(kind, names.length * each) })}
          extra={<><Select label="Questions" value={kind} options={kindChoices} onChange={setKind} /><Select label="Turns" value={each} options={eachChoices} onChange={setEach} /></>} />
      )}
    </GameShell>
  );
}

function QuizPlay({ names, items: first, kind, each, onSetup }: { names: string[]; items: QuizItem[]; kind: QuizKind; each: number; onSetup: () => void }) {
  const [items, setItems] = useState(first);
  const [round, setRound] = useState(0);
  const [choice, setChoice] = useState<number | null>(null);
  const [locked, setLocked] = useState(false);
  const [scores, setScores] = useState<number[]>(() => names.map(() => 0));
  const [done, setDone] = useState(false);
  const item = items[round]!;
  const player = round % names.length;
  const right = choice === item.answer;

  const lock = () => { if (choice === null) return; if (right) setScores((s) => award(s, player)); setLocked(true); };
  const next = () => { if (round + 1 >= items.length) setDone(true); else { setRound(round + 1); setChoice(null); setLocked(false); } };
  const replay = () => { setItems(buildQuiz(kind, names.length * each)); setRound(0); setChoice(null); setLocked(false); setScores(names.map(() => 0)); setDone(false); };

  if (done) {
    const turns = Math.ceil(items.length / names.length);
    return <FinalScreen headline={names.length === 1 ? `You got ${scores[0]} of ${items.length}!` : undefined} names={names} scores={scores} unit={`right answers (up to ${turns} each)`} onReplay={replay} onSetup={onSetup} />;
  }
  return (
    <Stage focusKey={`${round}-${locked}`}>
      {names.length > 1 && <Scoreboard names={names} values={scores} highlight={player} />}
      <div className="mt-5">
        <QuestionCard eyebrow={<>{names.length > 1 ? `${names[player]}'s turn` : `Question ${round + 1}`}<span className="text-muted">{item.tag}</span><span className="text-muted">{round + 1} of {items.length}</span></>} text={item.prompt}>
          {item.eyebrow && <p className="mt-2 font-semibold text-muted">{item.eyebrow}</p>}
          {item.sub && <p className="mt-2 text-lg font-bold">{item.sub}</p>}
          <ChoiceGrid options={item.options} chosen={choice} onChoose={setChoice} disabled={locked}
            mark={locked ? (i) => (i === item.answer ? "right" : i === choice ? "wrong" : undefined) : undefined} />
          {!locked ? (
            <button type="button" disabled={choice === null} onClick={lock} className={`${primary} mt-5 w-full sm:w-auto`}>Lock in the answer</button>
          ) : (
            <>
              <Verdict good={right}>{right ? "Right!" : "Not this time."} {item.why}</Verdict>
              <button type="button" onClick={next} className={`${primary} mt-5 w-full sm:w-auto`}>{round + 1 >= items.length ? "See the scores" : "Next"}</button>
            </>
          )}
        </QuestionCard>
      </div>
    </Stage>
  );
}

const factItems = (count: number): QuizItem[] =>
  pickMany(claims, count).map((c) => ({ tag: "Fact or Fiction", prompt: c.text, options: ["True", "Made up"], answer: c.isTrue ? 0 : 1, why: c.why }));

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

const higherLowerItems = (count: number): QuizItem[] => {
  const order = shuffle(factGroups);
  return Array.from({ length: Math.min(count, 60) }, (_, n) => {
    const group = order[n % order.length]!;
    const [known, other] = pickPair(group);
    const higher = isRight("higher", known, other);
    return {
      tag: "Higher or Lower",
      eyebrow: group.question,
      prompt: `${known.name}: ${formatValue(known.value, group.unit)}`,
      sub: `Is ${other.name} ${group.higher} or ${group.lower}?`,
      options: [cap(group.higher), cap(group.lower)],
      answer: higher ? 0 : 1,
      why: `${other.name}: ${formatValue(other.value, group.unit)}.`,
    };
  });
};

const priceQuizItems = (count: number): QuizItem[] =>
  pickMany(priceItems, count).map((p) => ({
    tag: "Guess the Price", prompt: p.item, sub: "Which price is closest? Rough typical US prices.", options: p.options, answer: p.answer,
    why: `A typical price is about ${p.options[p.answer]}.`,
  }));

