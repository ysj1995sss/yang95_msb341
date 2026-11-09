import { ArrowRight, Check, SkipForward, X } from "lucide-react";
import { useId, useMemo, useState, type ReactNode } from "react";
import type { OpenQuestion, TriviaQuestion } from "../types";
import { loadAnswers, saveAnswer } from "../utils/storage";
import { FavoriteButton } from "./FavoriteButton";
import { QuestionCard } from "./QuestionCard";
import { primary, quiet, secondary } from "./ui";

/** A conversation question: think it over, optionally write an answer, skip or move on. */
export function OpenStep({ question, eyebrow, isLast, onSaved, onSkip, onNext }: {
  question: OpenQuestion;
  eyebrow: ReactNode;
  isLast: boolean;
  onSaved: () => void;
  onSkip: () => void;
  onNext: () => void;
}) {
  const earlier = useMemo(() => loadAnswers()[question.id]?.text ?? "", [question.id]);
  const [text, setText] = useState(earlier);
  const [status, setStatus] = useState<"idle" | "saved" | "failed">("idle");
  const fieldId = useId();

  function save() {
    setStatus(saveAnswer(question.id, text.trim()) ? "saved" : "failed");
    onSaved();
  }

  return (
    <QuestionCard eyebrow={eyebrow} text={question.text} action={<FavoriteButton questionId={question.id} />}>
      {question.depth === 4 && (
        <p className="mt-3 rounded-2xl bg-coral-50 px-4 py-2.5 text-sm font-semibold text-coral-700">
          Bold questions are always optional. Skip this one any time you like.
        </p>
      )}
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
            {isLast ? "Finish" : "Next question"} <ArrowRight aria-hidden className="size-5" />
          </button>
        </div>
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

  return (
    <QuestionCard eyebrow={eyebrow} text={question.text} action={<FavoriteButton questionId={question.id} />}>
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
