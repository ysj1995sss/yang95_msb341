import { ArrowRight, Check, Lightbulb, SkipForward, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { sourceUrl } from "../data/trivia/bank";
import type { OpenQuestion, TriviaQuestion } from "../types";
import { FavoriteButton } from "./FavoriteButton";
import { SpeakButton } from "./SpeakButton";
import { QuestionCard } from "./QuestionCard";
import { primary, quiet } from "./ui";

/** The buttons at the top right of a question card: read aloud, and the favorite heart. */
function CardActions({ id, speak }: { id: string; speak: string }) {
  return (
    <div className="flex shrink-0 items-center">
      <SpeakButton text={speak} />
      <FavoriteButton questionId={id} />
    </div>
  );
}

/** A conversation question: read it out, talk it over, then move on or skip. Nothing to type. */
export function OpenStep({ question, eyebrow, tone, isLast, onSkip, onNext }: {
  question: OpenQuestion;
  eyebrow: ReactNode;
  tone?: string;
  isLast: boolean;
  onSkip: () => void;
  onNext: () => void;
}) {
  return (
    <QuestionCard eyebrow={eyebrow} text={question.text} tone={tone}
      action={<CardActions id={question.id} speak={question.text} />}>
      {question.depth === 4 ? (
        <p className="mt-4 rounded-2xl bg-coral-50 px-4 py-2.5 text-sm font-semibold text-coral-700">
          Bold questions are always optional. Skip this one any time you like.
        </p>
      ) : (
        <p className="mt-4 text-[15px] text-muted max-[399px]:hidden">Read it out loud and talk it over. Move on when you're ready.</p>
      )}
      <div className="mt-6 flex flex-col-reverse gap-3 max-[399px]:mt-4 max-[399px]:gap-1 sm:flex-row sm:items-center sm:justify-between">
        <button type="button" onClick={onSkip} className={quiet}>
          <SkipForward aria-hidden className="size-5" /> Skip
        </button>
        <button type="button" onClick={onNext} className={primary}>
          {isLast ? "Finish" : "Next question"} <ArrowRight aria-hidden className="size-5" />
        </button>
      </div>
    </QuestionCard>
  );
}

/** A trivia question: pick, submit once, see the right answer and why. */
export function TriviaStep({ question, eyebrow, tone, isLast, onSubmitted, onSkip, onNext }: {
  question: TriviaQuestion;
  eyebrow: ReactNode;
  tone?: string;
  isLast: boolean;
  onSubmitted: (correct: boolean) => void;
  onSkip: () => void;
  onNext: () => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const groupName = useId();
  const correct = choice === question.answer;

  // The Submit button goes away once used, so focus moves to the reveal and is never lost.
  const reveal = useRef<HTMLDivElement>(null);
  useEffect(() => { if (!submitted) return; reveal.current?.focus({ preventScroll: true }); reveal.current?.scrollIntoView({ block: "nearest" }); }, [submitted]);

  function submit() {
    if (choice === null || submitted) return;
    setSubmitted(true);
    onSubmitted(choice === question.answer);
  }

  const spoken = `${question.text} ${question.options.map((option, i) => `${"ABCD"[i]}. ${option}.`).join(" ")}`;

  return (
    <QuestionCard eyebrow={eyebrow} text={question.text} tone={tone} action={<CardActions id={question.id} speak={spoken} />}>
      <fieldset className="mt-6" disabled={submitted}>
        <legend className="sr-only">Choose an answer</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {question.options.map((option, i) => {
            const isAnswer = i === question.answer;
            const isChosen = i === choice;
            const state = !submitted
              ? isChosen ? "border-plum-500 bg-plum-50 ring-2 ring-plum-200" : "border-plum-100 bg-surface hover:border-plum-300"
              : isAnswer ? "border-emerald-500 bg-emerald-50" : isChosen ? "border-coral-500 bg-coral-50" : "border-plum-100 bg-surface opacity-60";
            return (
              <label key={option} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 p-4 font-semibold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${submitted && isAnswer ? "animate-pop" : ""} ${state}`}>
                <input type="radio" name={groupName} value={i} checked={isChosen} onChange={() => setChoice(i)} className="sr-only" />
                <span aria-hidden className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${
                  submitted && isAnswer ? "bg-emerald-600 text-white" : submitted && isChosen ? "bg-coral-600 text-white" : isChosen ? "bg-plum-600 text-white" : "bg-plum-100 text-plum-800"}`}>
                  {submitted && isAnswer ? <Check className="size-4" /> : submitted && isChosen ? <X className="size-4" /> : "ABCD"[i]}
                </span>
                <span className="min-w-0">
                  {option}
                  {submitted && (isAnswer || isChosen) && (
                    <span className={`block text-xs font-bold ${isAnswer ? "text-emerald-700" : "text-coral-700"}`}>
                      {isAnswer ? (isChosen ? "Your answer, and correct" : "Correct answer") : "Your answer"}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {submitted && (
        <div ref={reveal} tabIndex={-1} role="group" aria-label="The answer" className="mt-5 scroll-mb-28 scroll-mt-20 animate-fade-up overflow-hidden rounded-3xl border border-plum-100 bg-surface outline-none">
          <p role="status" className={`flex items-center gap-3 px-5 py-3.5 text-lg font-extrabold ${correct ? "bg-emerald-50 text-emerald-900" : "bg-coral-50 text-coral-700"}`}>
            <span aria-hidden className={`animate-pop flex size-9 shrink-0 items-center justify-center rounded-full text-white ${correct ? "bg-emerald-600" : "bg-coral-600"}`}>
              {correct ? <Check className="size-5" /> : <X className="size-5" />}
            </span>
            {correct ? "Correct! Nice one." : `Not quite. The answer is ${question.options[question.answer]}.`}
          </p>
          <div className="px-5 py-4">
            <p className="flex items-center gap-2 text-sm font-bold text-muted"><Lightbulb aria-hidden className="size-4" /> Did you know?</p>
            <p className="mt-1 text-lg leading-relaxed text-ink">{question.explanation}</p>
            <a href={sourceUrl(question)} target="_blank" rel="noreferrer"
              className="mt-1 inline-flex min-h-11 items-center text-sm font-semibold text-muted underline underline-offset-4 hover:text-ink">
              Read more<span className="sr-only"> about this on Wikipedia (opens in a new tab)</span>
            </a>
          </div>
        </div>
      )}

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
