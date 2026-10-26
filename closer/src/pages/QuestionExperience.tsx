import { ArrowLeft, ArrowRight, Check, RotateCcw, SkipForward, Trophy, X } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { CategoryIcon } from "../components/CategoryIcon";
import { ProgressBar } from "../components/ProgressBar";
import { QuestionCard } from "../components/QuestionCard";
import { categoryById } from "../data/categories";
import { questionsFor } from "../data/questions";
import type { Category, OpenQuestion, TriviaQuestion } from "../types";
import { href } from "../utils/router";
import { sessionOrder } from "../utils/session";
import { loadAnswers, saveAnswer } from "../utils/storage";

const ROUND_SIZE = 10;

const primary = "inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-full bg-plum-600 px-6 font-bold text-white shadow-md shadow-plum-600/20 transition hover:bg-plum-700 disabled:cursor-not-allowed disabled:opacity-50";
const secondary = "inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-full border-2 border-plum-200 bg-white px-6 font-bold text-plum-800 transition hover:border-plum-300 hover:bg-plum-50 disabled:cursor-not-allowed disabled:opacity-50";
const quiet = "inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-full px-5 font-bold text-muted transition hover:bg-sand hover:text-ink";

export function QuestionExperience({ categoryId }: { categoryId: string }) {
  const category = categoryById(categoryId);
  const [round, setRound] = useState(0);
  if (!category) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">We couldn't find that experience</h1>
        <p className="mt-3 text-muted">It may have moved. Pick one of the ten experiences instead.</p>
        <a href={href.explore} className={`${primary} mt-6`}>See all experiences</a>
      </div>
    );
  }
  // A new key starts a fresh round: new order, empty tallies.
  return <Round key={`${category.id}-${round}`} category={category} onRestart={() => setRound((r) => r + 1)} />;
}

function Round({ category, onRestart }: { category: Category; onRestart: () => void }) {
  const pool = useMemo(() => questionsFor(category.id), [category.id]);
  const order = useMemo(
    () => sessionOrder(pool.map((q) => q.id), ROUND_SIZE).map((id) => pool.find((q) => q.id === id)!),
    [pool],
  );
  const [index, setIndex] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [skipped, setSkipped] = useState(0);
  const [score, setScore] = useState(0);
  const headingRef = useRef<HTMLDivElement>(null);
  const done = index >= order.length;

  // Each new question (and the results) gets keyboard and screen-reader focus.
  useEffect(() => {
    if (index > 0) headingRef.current?.focus();
  }, [index]);

  const next = () => setIndex((i) => i + 1);

  return (
    <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6 sm:pt-12">
      <a href={href.explore} className={`${quiet} -ml-3`}>
        <ArrowLeft aria-hidden className="size-5" /> Back to categories
      </a>
      <div className="mt-4 flex items-center gap-4">
        <CategoryIcon category={category} size="lg" />
        <div>
          <h1 tabIndex={-1} className="text-2xl font-extrabold tracking-tight sm:text-3xl">{category.name}</h1>
          <p className="mt-1 text-muted">{category.description}</p>
        </div>
      </div>

      <div className="mt-8">
        <ProgressBar current={done ? order.length : index + 1} total={order.length}
          label={done ? "Round complete" : `Question ${index + 1} of ${order.length}`} />
      </div>

      <div ref={headingRef} tabIndex={-1} className="mt-6 rounded-[2rem] outline-none">
        {done ? (
          <Results category={category} total={order.length} answered={answered} skipped={skipped} score={score}
            onRestart={onRestart} />
        ) : order[index].kind === "trivia" ? (
          <TriviaStep key={order[index].id} question={order[index] as TriviaQuestion} isLast={index === order.length - 1}
            onSubmitted={(correct) => { if (correct) setScore((s) => s + 1); setAnswered((a) => a + 1); }}
            onSkip={() => { setSkipped((s) => s + 1); next(); }} onNext={next} />
        ) : (
          <OpenStep key={order[index].id} question={order[index] as OpenQuestion} isLast={index === order.length - 1}
            onSaved={(first) => { if (first) setAnswered((a) => a + 1); }}
            onSkip={() => { setSkipped((s) => s + 1); next(); }} onNext={next} />
        )}
      </div>
    </div>
  );
}

function OpenStep({ question, isLast, onSaved, onSkip, onNext }: {
  question: OpenQuestion; isLast: boolean; onSaved: (first: boolean) => void; onSkip: () => void; onNext: () => void;
}) {
  const earlier = useMemo(() => loadAnswers()[question.id]?.text ?? "", [question.id]);
  const [text, setText] = useState(earlier);
  const [status, setStatus] = useState<"idle" | "saved" | "failed">("idle");
  const [savedOnce, setSavedOnce] = useState(false);
  const fieldId = useId();

  function save() {
    const ok = saveAnswer(question.id, text.trim());
    setStatus(ok ? "saved" : "failed");
    onSaved(!savedOnce);
    setSavedOnce(true);
  }

  return (
    <QuestionCard eyebrow="Your question" text={question.text}>
      <label htmlFor={fieldId} className="mt-6 block text-sm font-semibold text-muted">Your answer (optional)</label>
      <textarea id={fieldId} rows={4} value={text} maxLength={2000}
        onChange={(e) => { setText(e.target.value); setStatus("idle"); }}
        placeholder="Talk it out, or write it down here…"
        className="mt-2 w-full resize-y rounded-2xl border border-plum-100 bg-cream/60 p-4 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400" />
      {earlier && status === "idle" && text === earlier && (
        <p className="mt-2 text-sm text-muted">This is the answer you saved last time.</p>
      )}
      <p role="status" className="mt-2 min-h-5 text-sm font-semibold text-plum-700">
        {status === "saved" && <span className="inline-flex items-center gap-1"><Check aria-hidden className="size-4" /> Saved on this device.</span>}
        {status === "failed" && <span className="text-coral-700">Your browser isn't letting this page save, so this answer won't be kept.</span>}
      </p>
      <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button type="button" onClick={onSkip} className={quiet}>
          <SkipForward aria-hidden className="size-5" /> Skip
        </button>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={save} disabled={!text.trim() || status === "saved"} className={secondary}>
            Save answer
          </button>
          <button type="button" onClick={onNext} className={primary}>
            {isLast ? "See how you did" : "Next question"} <ArrowRight aria-hidden className="size-5" />
          </button>
        </div>
      </div>
    </QuestionCard>
  );
}

function TriviaStep({ question, isLast, onSubmitted, onSkip, onNext }: {
  question: TriviaQuestion; isLast: boolean; onSubmitted: (correct: boolean) => void; onSkip: () => void; onNext: () => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const groupName = useId();
  const correct = choice === question.answer;

  function submit() {
    if (choice === null) return;
    setSubmitted(true);
    onSubmitted(choice === question.answer);
  }

  return (
    <QuestionCard eyebrow={question.topic} text={question.text}>
      <fieldset className="mt-6" disabled={submitted}>
        <legend className="sr-only">Choose an answer</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {question.options.map((option, i) => {
            const isAnswer = i === question.answer;
            const isChosen = i === choice;
            const state = !submitted
              ? isChosen ? "border-plum-500 bg-plum-50 ring-2 ring-plum-200" : "border-plum-100 bg-white hover:border-plum-300"
              : isAnswer ? "border-emerald-500 bg-emerald-50" : isChosen ? "border-coral-500 bg-coral-50" : "border-plum-100 bg-white opacity-60";
            return (
              <label key={option} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 p-4 font-semibold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${state}`}>
                <input type="radio" name={groupName} value={i} checked={isChosen} onChange={() => setChoice(i)} className="sr-only" />
                <span aria-hidden className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${
                  submitted && isAnswer ? "bg-emerald-600 text-white" : submitted && isChosen ? "bg-coral-600 text-white" : isChosen ? "bg-plum-600 text-white" : "bg-plum-100 text-plum-800"}`}>
                  {submitted && isAnswer ? <Check className="size-4" /> : submitted && isChosen ? <X className="size-4" /> : "ABCD"[i]}
                </span>
                <span>{option}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div role="status" className="mt-5">
        {submitted && (
          <div className={`animate-fade-up rounded-2xl p-4 ${correct ? "bg-emerald-50 text-emerald-900" : "bg-coral-50 text-coral-700"}`}>
            <p className="font-extrabold">{correct ? "Correct! Nice one." : `Not quite. The answer is ${question.options[question.answer]}.`}</p>
            <p className="mt-1 text-ink">{question.explanation}</p>
          </div>
        )}
      </div>

      <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        {!submitted ? (
          <button type="button" onClick={onSkip} className={quiet}>
            <SkipForward aria-hidden className="size-5" /> Skip
          </button>
        ) : <span />}
        {!submitted ? (
          <button type="button" onClick={submit} disabled={choice === null} className={primary}>Submit answer</button>
        ) : (
          <button type="button" onClick={onNext} className={primary}>
            {isLast ? "See your score" : "Next question"} <ArrowRight aria-hidden className="size-5" />
          </button>
        )}
      </div>
    </QuestionCard>
  );
}

function Results({ category, total, answered, skipped, score, onRestart }: {
  category: Category; total: number; answered: number; skipped: number; score: number; onRestart: () => void;
}) {
  const trivia = category.id === "trivia";
  const headline = trivia ? `You scored ${score} out of ${total}` : "Round complete!";
  const message = trivia
    ? score >= 8 ? "Brilliant. You're a trivia natural." : score >= 5 ? "Solid round. A rematch could push you higher." : "Every round teaches you something. Try again?"
    : `You answered ${answered} and skipped ${skipped} of ${total} questions. Good conversations take time.`;
  return (
    <div className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-8 text-center shadow-lg sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-500 to-coral-500 text-white shadow-md">
        <Trophy className="size-8" />
      </span>
      <h2 className="mt-5 text-3xl font-extrabold tracking-tight">{headline}</h2>
      <p className="mx-auto mt-3 max-w-md text-lg text-muted">{message}</p>
      {trivia && skipped > 0 && <p className="mt-1 text-sm text-muted">{`You skipped ${skipped}.`}</p>}
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <button type="button" onClick={onRestart} className={primary}>
          <RotateCcw aria-hidden className="size-5" /> Play another round
        </button>
        <a href={href.explore} className={secondary}>Explore another category</a>
      </div>
    </div>
  );
}

