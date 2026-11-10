import { ArrowRight, Check, SkipForward, X } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
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
export function OpenStep({ question, eyebrow, isLast, onSkip, onNext }: {
  question: OpenQuestion;
  eyebrow: ReactNode;
  isLast: boolean;
  onSkip: () => void;
  onNext: () => void;
}) {
  return (
    <QuestionCard eyebrow={eyebrow} text={question.text}
      action={<CardActions id={question.id} speak={question.text} />}>
      {question.depth === 4 ? (
        <p className="mt-4 rounded-2xl bg-coral-50 px-4 py-2.5 text-sm font-semibold text-coral-700">
          Bold questions are always optional. Skip this one any time you like.
        </p>
      ) : (
        <p className="mt-4 text-[15px] text-muted">Read it out loud and talk it over. Move on when you're ready.</p>
      )}
      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
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
export function TriviaStep({ question, eyebrow, isLast, onSubmitted, onSkip, onNext }: {
  question: TriviaQuestion;
  eyebrow: ReactNode;
  isLast: boolean;
  onSubmitted: (correct: boolean) => void;
  onSkip: () => void;
  onNext: () => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const groupName = useId();
  const correct = choice === question.answer;

  function submit() {
    if (choice === null || submitted) return;
    setSubmitted(true);
    onSubmitted(choice === question.answer);
  }

  const spoken = `${question.text} ${question.options.map((option, i) => `${"ABCD"[i]}. ${option}.`).join(" ")}`;

  return (
    <QuestionCard eyebrow={eyebrow} text={question.text} action={<CardActions id={question.id} speak={spoken} />}>
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
