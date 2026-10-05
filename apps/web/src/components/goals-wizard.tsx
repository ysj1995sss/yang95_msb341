"use client";

import { useState } from "react";
import { Alert, Button, Checkbox, RadioGroup, TextField, cx, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import type { ProfileResponse } from "@/lib/types";

type Answer = "yes" | "no" | "later";
const toAnswer = (v: boolean | null | undefined): Answer => (v === true ? "yes" : v === false ? "no" : "later");
const fromAnswer = (a: Answer) => (a === "yes" ? true : a === "no" ? false : null);
const YES_NO_LATER: Array<{ value: Answer; label: string }> = [
  { value: "yes", label: "Yes" }, { value: "no", label: "No" }, { value: "later", label: "I'll answer later" },
];

function ToggleList({ legend, options, value, onChange }: {
  legend: string; options: string[]; value: string[]; onChange: (v: string[]) => void;
}) {
  return (
    <fieldset>
      <legend className="sr-only">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = value.includes(o);
          return (
            <button key={o} type="button" aria-pressed={on}
              onClick={() => onChange(on ? value.filter((v) => v !== o) : [...value, o])}
              className={cx("min-h-11 rounded-full border px-4 text-[15px] font-semibold capitalize transition-colors duration-150 cursor-pointer",
                on ? "border-primary bg-primary-soft text-primary" : "border-line-strong bg-paper text-ink hover:bg-canvas")}>
              {o}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

/** One question at a time; only the role is required (same steps as the Streamlit wizard). */
export function GoalsWizard({ profile, onSaved, onCancel, doneLabel = "Save my goals" }: {
  profile: ProfileResponse; onSaved: (p: ProfileResponse) => void; onCancel?: () => void; doneLabel?: string;
}) {
  const toast = useToast();
  const prefs = profile.preferences;
  const steps = profile.goal_options.steps;
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [goals, setGoals] = useState({
    job_title: prefs.job_title ?? "",
    location: prefs.location ?? "",
    relocation_willing: Boolean(prefs.relocation_willing),
    remote_preference: prefs.remote_preference ?? "any",
    experience_level: prefs.experience_level ?? [],
    min_salary: prefs.min_salary ?? 0,
    industries: prefs.industries ?? [],
    authorized: toAnswer(profile.authorization.authorized_to_work),
    sponsorship: toAnswer(profile.authorization.sponsorship_required),
  });
  const current = steps[step];
  const last = step === steps.length - 1;
  const valid = !current.required || goals.job_title.trim().length > 0;
  const set = (patch: Partial<typeof goals>) => setGoals((g) => ({ ...g, ...patch }));

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const saved = await api<ProfileResponse>("/profile/goals", {
        method: "PUT",
        json: {
          job_title: goals.job_title, location: goals.location, relocation_willing: goals.relocation_willing,
          remote_preference: goals.remote_preference, experience_level: goals.experience_level,
          min_salary: goals.min_salary, industries: goals.industries,
          authorized_to_work: fromAnswer(goals.authorized), sponsorship_required: fromAnswer(goals.sponsorship),
        },
      });
      toast("Goals saved.");
      onSaved(saved);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-[14px] text-muted">Question {step + 1} of {steps.length}</p>
        <div className="mt-2 h-1.5 rounded-full bg-line" role="progressbar" aria-label="Goals progress"
          aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={step + 1}>
          <div className="h-1.5 rounded-full bg-primary transition-[width] duration-200" style={{ width: `${((step + 1) / steps.length) * 100}%` }} />
        </div>
        <h2 className="mt-4 text-[22px] font-semibold">{current.title}</h2>
        <p className="text-muted">{current.help}</p>
      </div>

      {current.key === "job_title" && (
        <div className="flex flex-col gap-3">
          {profile.goal_options.suggested_titles.length > 0 && (
            <div>
              <p className="mb-2 text-[14px] text-muted">From your resume:</p>
              <div className="flex flex-wrap gap-2">
                {profile.goal_options.suggested_titles.map((t) => (
                  <Button key={t} onClick={() => set({ job_title: t })}>{t}</Button>
                ))}
              </div>
            </div>
          )}
          <TextField label="Job title" value={goals.job_title} placeholder="e.g. Product Marketing Manager"
            onChange={(e) => set({ job_title: e.target.value })} />
        </div>
      )}
      {current.key === "location" && (
        <div className="flex flex-col gap-2">
          <TextField label="Location" value={goals.location} placeholder="e.g. Salt Lake City, UT"
            onChange={(e) => set({ location: e.target.value })} />
          <Checkbox label="I'm open to relocating" checked={goals.relocation_willing}
            onChange={(v) => set({ relocation_willing: v })} />
        </div>
      )}
      {current.key === "remote_preference" && (
        <RadioGroup legend="Work mode" name="work-mode" value={goals.remote_preference}
          options={profile.goal_options.work_modes} onChange={(v) => set({ remote_preference: v })} />
      )}
      {current.key === "experience_level" && (
        <ToggleList legend="Level" options={profile.goal_options.experience_levels} value={goals.experience_level}
          onChange={(v) => set({ experience_level: v })} />
      )}
      {current.key === "min_salary" && (
        <TextField label="Minimum yearly salary (USD)" type="number" min={0} max={1000000} step={5000}
          value={goals.min_salary} onChange={(e) => set({ min_salary: Math.max(0, Number(e.target.value) || 0) })} />
      )}
      {current.key === "industries" && (
        <ToggleList legend="Industries" options={profile.goal_options.industries} value={goals.industries}
          onChange={(v) => set({ industries: v })} />
      )}
      {current.key === "authorization" && (
        <div className="flex flex-col gap-4">
          <RadioGroup legend="Are you legally authorized to work in the country where you're searching?"
            name="authorized" value={goals.authorized} options={YES_NO_LATER} onChange={(v) => set({ authorized: v })} />
          <RadioGroup legend="Will you now or in the future need an employer to sponsor a work visa?"
            name="sponsorship" value={goals.sponsorship} options={YES_NO_LATER} onChange={(v) => set({ sponsorship: v })} />
        </div>
      )}

      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => (step === 0 ? onCancel?.() : setStep(step - 1))} disabled={step === 0 && !onCancel}>
          {step === 0 && onCancel ? "Cancel" : "Back"}
        </Button>
        {!current.required && !last && <Button variant="ghost" onClick={() => setStep(step + 1)}>Skip</Button>}
        <Button variant="primary" disabled={!valid} busy={busy} className="ml-auto"
          onClick={() => (last ? save() : setStep(step + 1))}>
          {last ? doneLabel : "Continue"}
        </Button>
      </div>
    </div>
  );
}
