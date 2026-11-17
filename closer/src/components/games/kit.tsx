import { ArrowLeft, Eye, EyeOff, Minus, Plus, RotateCcw, Trophy } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { GameInfo } from "../../data/games";
import { createDeck, type Deck } from "../../utils/games/deck";
import { cleanNames, MAX_NAME } from "../../utils/games/players";
import { leaders, outcomeLine } from "../../utils/games/scores";
import { href } from "../../utils/router";
import { primary, quiet, secondary } from "../ui";

// The parts every game is built from, so all nineteen look and behave alike: the page frame, the
// player setup form, the "pass the phone" screen, scoreboards and the final screen.

/** A deck that lives as long as the screen does. */
export function useDeck<T>(items: readonly T[]): Deck<T> {
  const [deck] = useState(() => createDeck(items));
  return deck;
}

/** The card every screen of a game sits on. */
export const panel = "animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-10";
export const field = "mt-2 w-full rounded-2xl border border-plum-100 bg-page/60 p-3.5 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400";
const stepper = "inline-flex size-11 cursor-pointer items-center justify-center rounded-full border-2 border-plum-200 bg-surface text-plum-800 transition hover:bg-plum-50 disabled:cursor-not-allowed disabled:opacity-40";

/** A ref for an element that takes keyboard focus whenever `key` changes (not on first render), so
 *  people using a keyboard or a screen reader land on each new screen. */
function useFocusOn(key: string) {
  const ref = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    ref.current?.focus({ preventScroll: true });
  }, [key]);
  return ref;
}

/** The area where one game's screens change. Wrap the screens of a round in it, with a `focusKey`
 *  that changes with each screen. */
export function Stage({ focusKey, children }: { focusKey: string; children: ReactNode }) {
  const ref = useFocusOn(focusKey);
  return <div ref={ref} tabIndex={-1} className="rounded-[2rem] outline-none">{children}</div>;
}

/** The page around one game: back link, title, and the stage. `focusKey` changes between setup and play. */
export function GameShell({ game, focusKey, children }: { game: GameInfo; focusKey: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-4 pb-4 pt-8 sm:px-6 sm:pt-12">
      <a href={href.games} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> Back to games
      </a>
      <div className="mt-4 flex items-center gap-4">
        <span aria-hidden className={`inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br ${game.gradient} text-white shadow-md`}>
          <game.icon className="size-8" />
        </span>
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">{game.title}</h1>
          <p className="mt-1 text-muted">{game.blurb}</p>
        </div>
      </div>
      <div className="mt-8"><Stage focusKey={focusKey}>{children}</Stage></div>
    </div>
  );
}

/** A number with plus and minus buttons. */
export function Stepper({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (n: number) => void }) {
  const id = useId();
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span id={id} className="text-sm font-semibold text-muted">{label}</span>
      <button type="button" aria-label={`Fewer: ${label}`} disabled={value <= min} onClick={() => onChange(value - 1)} className={stepper}>
        <Minus aria-hidden className="size-5" />
      </button>
      <output aria-labelledby={id} className="min-w-8 text-center text-2xl font-extrabold">{value}</output>
      <button type="button" aria-label={`More: ${label}`} disabled={value >= max} onClick={() => onChange(value + 1)} className={stepper}>
        <Plus aria-hidden className="size-5" />
      </button>
    </div>
  );
}

/** A labelled drop-down in the setup form. */
export function Select<T extends string | number>({ label, value, options, onChange }: {
  label: string; value: T; options: readonly { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="text-sm font-semibold text-muted">{label}</label>
      <select id={id} value={value} className={field}
        onChange={(e) => onChange((typeof value === "number" ? Number(e.target.value) : e.target.value) as T)}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

/** The setup form: how to play, how many players, their names. Names stay in memory and are never saved. */
export function PlayerSetup({ min, max, start = min, rules, extra, button = "Start the game", onStart }: {
  min: number; max: number; start?: number;
  /** A short numbered list of how the game goes. */
  rules: readonly string[];
  /** More fields (rounds, difficulty) shown under the names. */
  extra?: ReactNode;
  button?: string;
  onStart: (names: string[]) => void;
}) {
  const id = useId();
  const [count, setCount] = useState(start);
  const [raw, setRaw] = useState<string[]>(() => Array.from({ length: max }, () => ""));
  return (
    <form className={panel} onSubmit={(e) => { e.preventDefault(); onStart(cleanNames(raw, count)); }}>
      <h2 className="text-2xl font-extrabold">How to play</h2>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">{rules.map((r) => <li key={r}>{r}</li>)}</ol>
      {min !== max && <div className="mt-6"><Stepper label="Players" value={count} min={min} max={max} onChange={setCount} /></div>}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {Array.from({ length: count }, (_, i) => (
          <div key={i}>
            <label htmlFor={`${id}-p${i}`} className="text-sm font-semibold text-muted">Player {i + 1}</label>
            <input id={`${id}-p${i}`} type="text" maxLength={MAX_NAME} placeholder={`Player ${i + 1}`} value={raw[i]} autoComplete="off"
              onChange={(e) => setRaw((r) => r.map((n, j) => (j === i ? e.target.value : n)))} className={field} />
          </div>
        ))}
      </div>
      {extra && <div className="mt-4 grid gap-4 sm:grid-cols-2">{extra}</div>}
      <p className="mt-4 text-sm text-muted">Names are only used while you play. Nothing is saved.</p>
      <button type="submit" className={`${primary} mt-5 w-full sm:w-auto`}>{button}</button>
    </form>
  );
}

/** The screen that stands between players so something private stays private, or a turn is handed on. */
export function Handoff({ title, text, button, onReady, locked }: { title: string; text: string; button: string; onReady: () => void; locked?: boolean }) {
  return (
    <div className={`${panel} text-center sm:p-12`}>
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-plum-100 text-plum-700 dark:text-onplum-soft">
        {locked ? <EyeOff className="size-8" /> : <Eye className="size-8" />}
      </span>
      <h2 className="mt-5 text-2xl font-extrabold sm:text-3xl">{title}</h2>
      <p className="mx-auto mt-3 max-w-md text-lg text-muted">{text}</p>
      <button type="button" onClick={onReady} className={`${primary} mt-8`}>{button}</button>
    </div>
  );
}

const gridFor = (n: number) => (n <= 2 ? "grid-cols-2" : n === 4 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-3");

/** Everyone's points (or lives) in a row of small cards, with the person whose turn it is marked. */
export function Scoreboard({ names, values, highlight, label = "Scores", suffix = "" }: {
  names: readonly string[]; values: readonly (number | string)[]; highlight?: number | null; label?: string; suffix?: string;
}) {
  return (
    <div role="group" aria-label={label} className={`grid gap-3 ${gridFor(names.length)}`}>
      {names.map((name, i) => (
        <div key={i} className={`rounded-2xl border-2 p-3 text-center ${i === highlight ? "border-plum-300 bg-plum-50" : "border-plum-100 bg-surface"}`}>
          <p className="truncate text-sm font-semibold text-muted">{name}</p>
          <p className="text-2xl font-extrabold text-plum-800">{values[i]}{suffix}</p>
        </div>
      ))}
    </div>
  );
}

/** The end of a game: who won, everyone's score, and ways to go again. */
export function FinalScreen({ headline, text, names, scores, unit, onReplay, onSetup }: {
  headline?: string; text?: string; names: readonly string[]; scores: readonly number[]; unit?: string; onReplay: () => void; onSetup: () => void;
}) {
  const top = leaders(scores);
  return (
    <div className={`${panel} text-center sm:p-12`}>
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{headline ?? `${outcomeLine(names, scores)}!`}</h2>
      {text && <p className="mx-auto mt-2 max-w-md text-lg text-muted">{text}</p>}
      <div role="group" aria-label="Final scores" className={`mx-auto mt-6 grid max-w-xl gap-3 ${gridFor(names.length)}`}>
        {names.map((name, i) => (
          <div key={i} className={`rounded-2xl p-4 ${top.includes(i) ? "bg-plum-100" : "bg-plum-50"}`}>
            <p className="text-4xl font-extrabold text-plum-800">{scores[i]}</p>
            <p className="truncate text-sm font-semibold text-muted">{name}</p>
          </div>
        ))}
      </div>
      {unit && <p className="mt-3 text-sm text-muted">{unit}</p>}
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={onReplay} className={primary}><RotateCcw aria-hidden className="size-5" /> Play again</button>
        <button type="button" onClick={onSetup} className={secondary}>Change players</button>
      </div>
    </div>
  );
}

/** "It's Ana's turn", big, above the prompt. */
export function TurnLabel({ name, children }: { name: string; children?: ReactNode }) {
  return (
    <p className="flex flex-wrap items-baseline gap-x-3 text-sm font-bold uppercase tracking-wider text-coral-700">
      <span className="break-words">{name}'s turn</span>
      {children && <span className="whitespace-nowrap normal-case tracking-normal text-muted">{children}</span>}
    </p>
  );
}

/** The big text of a prompt card. */
export function Prompt({ children, small }: { children: ReactNode; small?: boolean }) {
  return <p className={`mt-4 font-extrabold leading-tight tracking-tight text-ink ${small ? "text-2xl sm:text-3xl" : "text-3xl sm:text-4xl"}`}>{children}</p>;
}

/** A line announcing a result; read out by screen readers when it appears. */
export function Verdict({ good, children }: { good: boolean; children: ReactNode }) {
  return (
    <p role="status" className={`mt-5 rounded-2xl p-4 text-lg font-extrabold ${good ? "bg-emerald-50 text-emerald-900" : "bg-coral-50 text-coral-700"}`}>{children}</p>
  );
}

/** Pick one of a few options, shown as big lettered rows. Not a form: it reports every tap. */
export function ChoiceGrid({ options, chosen, onChoose, columns = 2, disabled, mark }: {
  options: readonly string[]; chosen: number | null; onChoose: (i: number) => void; columns?: 1 | 2; disabled?: boolean;
  /** After the reveal: "right" or "wrong" for an option, to show it in color with a word as well. */
  mark?: (i: number) => "right" | "wrong" | undefined;
}) {
  const group = useId();
  return (
    <fieldset className="mt-5" disabled={disabled}>
      <legend className="sr-only">Choose one</legend>
      <div className={`grid gap-3 ${columns === 2 ? "sm:grid-cols-2" : ""}`}>
        {options.map((option, i) => {
          const on = i === chosen;
          const m = mark?.(i);
          const look = m === "right" ? "border-emerald-500 bg-emerald-50" : m === "wrong" ? "border-coral-500 bg-coral-50"
            : on ? "border-plum-500 bg-plum-50 ring-2 ring-plum-200" : "border-plum-100 bg-surface hover:border-plum-300";
          return (
            <label key={option} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 p-4 font-semibold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${look}`}>
              <input type="radio" name={group} value={i} checked={on} onChange={() => onChoose(i)} className="sr-only" />
              <span aria-hidden className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${on ? "bg-plum-600 text-white" : "bg-plum-100 text-plum-800"}`}>{"ABCD"[i]}</span>
              <span className="flex-1">{option}</span>
              {m && <span className="text-sm font-bold">{m === "right" ? "Right answer" : "Wrong"}</span>}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** A row of toggle pills (budget, mood): any number can be on at once. */
export function Pills<T extends string>({ label, options, value, onChange }: {
  label: string; options: readonly { value: T; label: string }[]; value: readonly T[]; onChange: (next: T[]) => void;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-semibold text-muted">{label}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((o) => {
          const on = value.includes(o.value);
          return (
            <button key={o.value} type="button" aria-pressed={on}
              onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}
              className={`inline-flex min-h-11 cursor-pointer items-center rounded-full border-2 px-4 font-bold transition ${on ? "border-plum-600 bg-plum-600 text-white" : "border-plum-200 bg-surface text-plum-800 hover:border-plum-300"}`}>
              {o.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
