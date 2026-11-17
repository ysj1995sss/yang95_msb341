import { Pause, Play } from "lucide-react";
import { useId, useState } from "react";
import { ChoiceGrid, FinalScreen, GameShell, Handoff, panel, PlayerSetup, Prompt, Scoreboard, Select, Stage, TurnLabel, Verdict, field } from "../../components/games/kit";
import { QuestionCard } from "../../components/QuestionCard";
import { primary, quiet, secondary } from "../../components/ui";
import { useCountdown } from "../../hooks";
import { gameById } from "../../data/games";
import { captionScenes, productProblems, productTwists, storyStarters } from "../../data/games/creative";
import { createDeck } from "../../utils/games/deck";
import { award } from "../../utils/games/scores";
import { shuffle } from "../../utils/shuffle";

// ---------------------------------------------------------------- Story Chain

type Grain = "sentence" | "word";
const grainLabels = [{ value: "sentence" as Grain, label: "One sentence" }, { value: "word" as Grain, label: "One word (harder!)" }];
const turnChoices = [{ value: 2, label: "2 turns each" }, { value: 3, label: "3 turns each" }, { value: 4, label: "4 turns each" }];

export function StoryChain() {
  const [play, setPlay] = useState<{ names: string[]; grain: Grain; turns: number } | null>(null);
  const [grain, setGrain] = useState<Grain>("sentence");
  const [turns, setTurns] = useState(2);
  return (
    <GameShell game={gameById("story-chain")!} focusKey={play ? "play" : "setup"}>
      {play ? <StoryPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={2} max={8} start={3} onStart={(names) => setPlay({ names, grain, turns })}
          rules={["The phone gives the first line of a story.", "Take turns adding the next sentence (or just one word) and passing the phone on.", "At the end, read the whole story aloud."]}
          extra={<><Select label="Each turn adds" value={grain} options={grainLabels} onChange={setGrain} /><Select label="Turns" value={turns} options={turnChoices} onChange={setTurns} /></>} />
      )}
    </GameShell>
  );
}

const endsSentence = (t: string) => /[.!?…]["')\]]?$/.test(t);

function StoryPlay({ names, grain, turns, onSetup }: { names: string[]; grain: Grain; turns: number; onSetup: () => void }) {
  const id = useId();
  const [starter, setStarter] = useState(() => shuffle(storyStarters)[0]!);
  const [pieces, setPieces] = useState<string[]>([]);
  const [text, setText] = useState("");
  const total = names.length * turns;
  const done = pieces.length >= total;
  const story = [starter, ...pieces].join(" ");
  const add = () => {
    const cleaned = grain === "word" ? (text.trim().split(/\s+/)[0] ?? "") : text.trim();
    if (!cleaned) return;
    const closes = grain === "sentence" || pieces.length + 1 >= total;
    setPieces((p) => [...p, closes && !endsSentence(cleaned) ? `${cleaned}.` : cleaned]);
    setText("");
  };
  const again = () => { setStarter(shuffle(storyStarters.filter((s) => s !== starter))[0]!); setPieces([]); setText(""); };

  if (done) {
    return (
      <Stage focusKey="story">
        <div className={panel}>
          <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Your story</p>
          <p className="mt-4 text-xl leading-relaxed sm:text-2xl">{story}</p>
          <p className="mt-4 text-muted">Now read it out loud, with all the voices.</p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={again} className={primary}>New story</button>
            <button type="button" onClick={onSetup} className={secondary}>Change players</button>
          </div>
        </div>
      </Stage>
    );
  }
  const name = names[pieces.length % names.length]!;
  return (
    <Stage focusKey={String(pieces.length)}>
      <form className={panel} onSubmit={(e) => { e.preventDefault(); add(); }}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">{pieces.length + 1} of {total}</p>
        <p className="mt-4 text-xl leading-relaxed sm:text-2xl">{story}</p>
        <TurnLabel name={name} />
        <label htmlFor={id} className="mt-2 block text-lg font-extrabold">{grain === "word" ? "Add one word" : "Add the next sentence"}</label>
        <input id={id} type="text" value={text} maxLength={grain === "word" ? 24 : 160} autoComplete="off" autoFocus={pieces.length > 0}
          onChange={(e) => setText(e.target.value)} className={field} />
        <button type="submit" disabled={!text.trim()} className={`${primary} mt-4 w-full sm:w-auto`}>Add and pass the phone</button>
        <p className="mt-3 text-sm text-muted">The story is only kept while you play.</p>
      </form>
    </Stage>
  );
}

// ---------------------------------------------------------------- Caption This

const captionRounds = [{ value: 2, label: "2 scenes" }, { value: 3, label: "3 scenes" }, { value: 5, label: "5 scenes" }];

export function CaptionThis() {
  const [play, setPlay] = useState<{ names: string[]; rounds: number } | null>(null);
  const [rounds, setRounds] = useState(3);
  return (
    <GameShell game={gameById("caption-this")!} focusKey={play ? "play" : "setup"}>
      {play ? <CaptionPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={3} max={8} start={4} onStart={(names) => setPlay({ names, rounds })}
          rules={["A made-up scene appears.", "Everyone writes a funny caption for it in secret, passing the phone on.", "The captions are shown mixed up. The group picks the funniest, and that writer scores."]}
          extra={<Select label="Length" value={rounds} options={captionRounds} onChange={setRounds} />} />
      )}
    </GameShell>
  );
}

type CaptionPhase = "write" | "handoff" | "judge" | "reveal";

function CaptionPlay({ names, rounds, onSetup }: { names: string[]; rounds: number; onSetup: () => void }) {
  const id = useId();
  const [scenes, setScenes] = useState(() => shuffle(captionScenes).slice(0, rounds));
  const [round, setRound] = useState(0);
  const [phase, setPhase] = useState<CaptionPhase>("handoff");
  const [writer, setWriter] = useState(0);
  const [text, setText] = useState("");
  const [captions, setCaptions] = useState<{ author: number; text: string }[]>([]);
  const [choice, setChoice] = useState<number | null>(null);
  const [scores, setScores] = useState<number[]>(() => names.map(() => 0));
  const [done, setDone] = useState(false);
  const scene = scenes[round]!;

  const lock = () => {
    const clean = text.trim();
    if (!clean) return;
    const all = [...captions, { author: writer, text: clean }];
    setText("");
    if (writer + 1 < names.length) { setCaptions(all); setWriter(writer + 1); setPhase("handoff"); return; }
    setCaptions(shuffle(all)); setChoice(null); setPhase("judge");
  };
  const nextRound = () => {
    if (round + 1 >= scenes.length) { setDone(true); return; }
    setRound(round + 1); setCaptions([]); setWriter(0); setChoice(null); setPhase("handoff");
  };
  const replay = () => { setScenes(shuffle(captionScenes).slice(0, rounds)); setRound(0); setCaptions([]); setWriter(0); setChoice(null); setScores(names.map(() => 0)); setPhase("handoff"); setDone(false); };

  if (done) return <FinalScreen text="Points are for the captions the group liked best." names={names} scores={scores} unit="funniest captions" onReplay={replay} onSetup={onSetup} />;

  const sceneCard = (
    <div className="rounded-2xl bg-plum-50 p-4 text-center">
      <p aria-hidden className="text-5xl">{scene.emoji}</p>
      <p className="mt-2 text-lg font-bold">{scene.setup}</p>
    </div>
  );
  return (
    <Stage focusKey={`${round}-${phase}-${writer}`}>
      <Scoreboard names={names} values={scores} label="Funniest captions" />
      <div className="mt-5">
        {phase === "handoff" && (
          <Handoff title={`${names[writer]}'s turn`} text={writer === 0 ? `Scene ${round + 1} of ${scenes.length}. Pass the phone to ${names[writer]}. Everyone else, look away.` : `Caption locked. Pass the phone to ${names[writer]} and no peeking at the others.`}
            locked={writer > 0} button={`I'm ${names[writer]}, show the scene`} onReady={() => setPhase("write")} />
        )}
        {phase === "write" && (
          <form className={panel} onSubmit={(e) => { e.preventDefault(); lock(); }}>
            <TurnLabel name={names[writer]!}>Scene {round + 1} of {scenes.length}</TurnLabel>
            <div className="mt-4">{sceneCard}</div>
            <label htmlFor={id} className="mt-4 block text-lg font-extrabold">Your caption</label>
            <input id={id} type="text" maxLength={120} value={text} onChange={(e) => setText(e.target.value)} autoComplete="off" className={field} />
            <button type="submit" disabled={!text.trim()} className={`${primary} mt-4 w-full sm:w-auto`}>{writer + 1 < names.length ? "Lock it in and pass on" : "Lock it in and show them all"}</button>
          </form>
        )}
        {phase === "judge" && (
          <QuestionCard eyebrow="Which is funniest?" text={scene.setup}>
            <p className="mt-3 text-muted">Read them all out. Talk it over, and don't vote for your own.</p>
            <ChoiceGrid columns={1} options={captions.map((c) => c.text)} chosen={choice} onChoose={setChoice} />
            <button type="button" disabled={choice === null} onClick={() => { if (choice !== null) setScores((s) => award(s, captions[choice]!.author)); setPhase("reveal"); }} className={`${primary} mt-5 w-full sm:w-auto`}>This one wins</button>
          </QuestionCard>
        )}
        {phase === "reveal" && choice !== null && (
          <QuestionCard eyebrow="The winner" text={captions[choice]!.text}>
            <Verdict good>{names[captions[choice]!.author]} wrote that one and scores a point!</Verdict>
            <p className="mt-4 text-muted">All the captions: {captions.map((c) => `"${c.text}" (${names[c.author]})`).join(", ")}</p>
            <button type="button" onClick={nextRound} className={`${primary} mt-5 w-full sm:w-auto`}>{round + 1 >= scenes.length ? "See the scores" : "Next scene"}</button>
          </QuestionCard>
        )}
      </div>
    </Stage>
  );
}

// ---------------------------------------------------------------- Invent a Product

const PITCH_SECONDS = 60;
const productRounds = [{ value: 1, label: "1 problem" }, { value: 2, label: "2 problems" }, { value: 3, label: "3 problems" }];
const twistChoices = [{ value: "yes", label: "Yes, add a twist" }, { value: "no", label: "No twist" }];

export function InventAProduct() {
  const [play, setPlay] = useState<{ names: string[]; rounds: number; twist: boolean } | null>(null);
  const [rounds, setRounds] = useState(2);
  const [twist, setTwist] = useState("yes");
  return (
    <GameShell game={gameById("invent-a-product")!} focusKey={play ? "play" : "setup"}>
      {play ? <InventPlay {...play} onSetup={() => setPlay(null)} /> : (
        <PlayerSetup min={2} max={8} start={3} onStart={(names) => setPlay({ names, rounds, twist: twist === "yes" })}
          rules={["A random problem appears, and maybe a twist your invention must have.", `Each player pitches a solution in up to ${PITCH_SECONDS} seconds, out loud.`, "Then the room votes for the best pitch. That inventor scores."]}
          extra={<><Select label="Problems" value={rounds} options={productRounds} onChange={setRounds} /><Select label="Twist" value={twist} options={twistChoices} onChange={setTwist} /></>} />
      )}
    </GameShell>
  );
}

function InventPlay({ names, rounds, twist, onSetup }: { names: string[]; rounds: number; twist: boolean; onSetup: () => void }) {
  const [problems] = useState(() => createDeck(productProblems));
  const [twists] = useState(() => createDeck(productTwists));
  const draw = () => ({ problem: problems.draw(), twist: twist ? twists.draw() : null });
  const [round, setRound] = useState(0);
  const [brief, setBrief] = useState(draw);
  const [pitcher, setPitcher] = useState(0);
  const [voting, setVoting] = useState(false);
  const [scores, setScores] = useState<number[]>(() => names.map(() => 0));
  const [done, setDone] = useState(false);
  const clock = useCountdown(PITCH_SECONDS, `${round}-${pitcher}`);

  const vote = (i: number) => {
    setScores((s) => award(s, i));
    if (round + 1 >= rounds) { setDone(true); return; }
    setRound(round + 1); setBrief(draw()); setPitcher(0); setVoting(false);
  };
  const replay = () => { setScores(names.map(() => 0)); setRound(0); setBrief(draw()); setPitcher(0); setVoting(false); setDone(false); };
  if (done) return <FinalScreen text="Points are for the pitches the room liked best." names={names} scores={scores} unit="winning pitches" onReplay={replay} onSetup={onSetup} />;

  return (
    <Stage focusKey={`${round}-${pitcher}-${voting}`}>
      <Scoreboard names={names} values={scores} highlight={voting ? null : pitcher} label="Winning pitches" />
      <div className={`${panel} mt-5`}>
        <p className="text-sm font-bold uppercase tracking-wider text-coral-700">Problem {round + 1} of {rounds}</p>
        <Prompt>{brief.problem}</Prompt>
        {brief.twist && <p className="mt-3 rounded-2xl bg-plum-50 p-3 text-lg font-bold text-plum-800">Twist: {brief.twist}</p>}
        {!voting ? (
          <>
            <p className="mt-5 text-xl font-extrabold">{names[pitcher]}, pitch your invention!</p>
            <p className="mt-1 text-muted" aria-label={`${clock.left} seconds left`}>{clock.left}s left</p>
            {clock.finished && <Verdict good={false}>Time is up. Wrap it up!</Verdict>}
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <button type="button" onClick={clock.running ? clock.pause : clock.start} className={secondary}>
                {clock.running ? <><Pause aria-hidden className="size-5" /> Pause the clock</> : <><Play aria-hidden className="size-5" /> {clock.left < PITCH_SECONDS ? "Resume" : "Start the clock"}</>}
              </button>
              <button type="button" onClick={() => { clock.pause(); if (pitcher + 1 >= names.length) setVoting(true); else setPitcher(pitcher + 1); }} className={primary}>
                {pitcher + 1 >= names.length ? "All pitched, vote!" : `Done, ${names[pitcher + 1]} is next`}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-5 text-xl font-extrabold">Which pitch was best?</p>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2">
              {names.map((n, i) => (
                <li key={i}><button type="button" onClick={() => vote(i)} className="flex min-h-14 w-full cursor-pointer items-center rounded-2xl border-2 border-plum-100 bg-surface px-4 font-bold transition hover:border-plum-300"><span className="truncate">{n}</span></button></li>
              ))}
            </ul>
          </>
        )}
      </div>
      <button type="button" onClick={onSetup} className={`${quiet} mt-4`}>End the game</button>
    </Stage>
  );
}
