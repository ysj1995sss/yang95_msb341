"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";
import { GoalsWizard } from "@/components/goals-wizard";
import {
  Alert, Button, Checkbox, RadioGroup, SelectField, TextArea, TextField, useToast,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { Education, ProfileResponse, SavedAnswer } from "@/lib/types";

type EditorProps = { data: ProfileResponse; onSaved: (p: ProfileResponse) => void };
const lines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);
const edited = (data: ProfileResponse, path: string) => data.edited.includes(path);
const tag = (label: string, data: ProfileResponse, path: string) => (edited(data, path) ? `${label} · edited by you` : label);

function useSave(onSaved: (p: ProfileResponse) => void) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(path: string, json: unknown, message?: (p: ProfileResponse & { changed?: number }) => string) {
    setBusy(true);
    setError(null);
    try {
      const saved = await api<ProfileResponse & { changed?: number }>(path, { method: "PUT", json });
      toast(message ? message(saved) : "Saved.");
      onSaved(saved);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, save };
}

const changedMessage = (p: { changed?: number }) =>
  p.changed ? `Saved. ${p.changed} ${p.changed === 1 ? "fact" : "facts"} marked as edited by you.` : "Saved.";

function Actions({ busy, error, label }: { busy: boolean; error: string | null; label: string }) {
  return (
    <div className="flex flex-col gap-3">
      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
      <Button type="submit" variant="primary" busy={busy} className="self-start">{label}</Button>
    </div>
  );
}

export function ContactEditor({ data, onSaved }: EditorProps) {
  const c = data.profile.contact_info;
  const [form, setForm] = useState({ name: c.name ?? "", email: c.email ?? "", phone: c.phone ?? "", location: c.location ?? "" });
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void save("/profile/contact", form, changedMessage); }}>
      <div className="grid gap-4 sm:grid-cols-2">
        {(["name", "email", "phone", "location"] as const).map((k) => (
          <TextField key={k} label={tag(k[0].toUpperCase() + k.slice(1), data, `contact_info.${k}`)} value={form[k]}
            type={k === "email" ? "email" : k === "phone" ? "tel" : "text"} autoComplete={k === "name" ? "name" : k === "email" ? "email" : k === "phone" ? "tel" : "address-level2"}
            onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
        ))}
      </div>
      <Actions busy={busy} error={error} label="Save contact" />
    </form>
  );
}

export function SummaryEditor({ data, onSaved }: EditorProps) {
  const [summary, setSummary] = useState(data.profile.summary ?? "");
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void save("/profile/summary", { summary }, changedMessage); }}>
      <TextArea label={tag("Summary", data, "summary")} rows={6} value={summary} onChange={(e) => setSummary(e.target.value)}
        help="Optional. Used only if your resume has a summary section." />
      <Actions busy={busy} error={error} label="Save summary" />
    </form>
  );
}

export function WorkEditor({ data, onSaved }: EditorProps) {
  const jobs = data.profile.work_experience;
  const [index, setIndex] = useState(0);
  const { busy, error, save } = useSave(onSaved);
  const job = jobs[index];
  const [form, setForm] = useState(() => roleForm(job));
  if (!jobs.length) {
    return <Alert tone="review">No roles were found in your resume. Re-import a Word version, or check its layout.</Alert>;
  }
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => {
      e.preventDefault();
      void save("/profile/work", { index, ...form, bullets: lines(form.bullets) }, changedMessage);
    }}>
      <SelectField label="Role" value={String(index)}
        options={jobs.map((j, i) => ({ value: String(i), label: `${j.title || "Role"} · ${j.employer || "Employer"}` }))}
        onChange={(e) => { const i = Number(e.target.value); setIndex(i); setForm(roleForm(jobs[i])); }} />
      <div className="grid gap-4 sm:grid-cols-[2fr_2fr_1.4fr]">
        <TextField label={tag("Title", data, `work_experience[${index}]`)} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <TextField label="Employer" value={form.employer} onChange={(e) => setForm({ ...form, employer: e.target.value })} />
        <TextField label="Dates" value={form.dates} placeholder="e.g. Jan 2021 – Present" onChange={(e) => setForm({ ...form, dates: e.target.value })} />
      </div>
      <TextArea label="Bullet points (one per line)" rows={8} value={form.bullets} onChange={(e) => setForm({ ...form, bullets: e.target.value })} />
      <Actions busy={busy} error={error} label="Save role" />
    </form>
  );
}

function roleForm(job: ProfileResponse["profile"]["work_experience"][number] | undefined) {
  return {
    title: job?.title ?? "", employer: job?.employer ?? "", dates: job?.dates ?? "",
    bullets: [...(job?.responsibilities ?? []), ...(job?.accomplishments ?? [])].join("\n"),
  };
}

export function EducationEditor({ data, onSaved }: EditorProps) {
  const [entries, setEntries] = useState<Education[]>(data.profile.education.map((e) => ({ ...e })));
  const [none, setNone] = useState(data.no_education);
  const { busy, error, save } = useSave(onSaved);
  const update = (i: number, patch: Partial<Education>) => setEntries(entries.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); void save("/profile/education", { entries, no_education: none }, changedMessage); }}>
      {entries.map((entry, i) => (
        <fieldset key={i} className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-4">
          <legend className="px-1 font-semibold">{entry.institution || "Education"}{edited(data, `education[${i}]`) ? " · edited by you" : ""}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField label="Degree" value={entry.degree} onChange={(e) => update(i, { degree: e.target.value })} />
            <TextField label="Field" value={entry.field} onChange={(e) => update(i, { field: e.target.value })} />
            <TextField label="School" value={entry.institution} onChange={(e) => update(i, { institution: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <TextField label="Year" inputMode="numeric" value={entry.year ? String(entry.year) : ""}
                onChange={(e) => update(i, { year: Number(e.target.value.replace(/\D/g, "")) || null })} />
              <TextField label="GPA" placeholder="Optional" value={entry.gpa ?? ""} onChange={(e) => update(i, { gpa: e.target.value })} />
            </div>
          </div>
        </fieldset>
      ))}
      <Checkbox label="I have no degree to list" checked={none} onChange={setNone} />
      <Actions busy={busy} error={error} label="Save education" />
    </form>
  );
}

export function SkillsEditor({ data, onSaved }: EditorProps) {
  const [skills, setSkills] = useState(data.profile.skills.join("\n"));
  const [tools, setTools] = useState(data.profile.tools.join("\n"));
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void save("/profile/skills", { skills: lines(skills), tools: lines(tools) }, changedMessage); }}>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextArea label={tag("Skills (one per line)", data, "skills")} rows={10} value={skills} onChange={(e) => setSkills(e.target.value)} />
        <TextArea label={tag("Tools (one per line)", data, "tools")} rows={10} value={tools} onChange={(e) => setTools(e.target.value)} />
      </div>
      <Actions busy={busy} error={error} label="Save skills and tools" />
    </form>
  );
}

export function CertificationsEditor({ data, onSaved }: EditorProps) {
  const [certs, setCerts] = useState(data.profile.certifications.join("\n"));
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void save("/profile/certifications", { certifications: lines(certs) }, changedMessage); }}>
      <TextArea label={tag("Certifications (one per line)", data, "certifications")} rows={5} value={certs} onChange={(e) => setCerts(e.target.value)} />
      <Actions busy={busy} error={error} label="Save certifications" />
    </form>
  );
}

export function LinksEditor({ data, onSaved }: EditorProps) {
  const [links, setLinks] = useState({ linkedin: data.links.linkedin ?? "", portfolio: data.links.portfolio ?? "", github: data.links.github ?? "" });
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void save("/profile/links", links, () => "Links saved."); }}>
      <TextField label="LinkedIn" type="url" value={links.linkedin} onChange={(e) => setLinks({ ...links, linkedin: e.target.value })} />
      <TextField label="Portfolio or website" type="url" value={links.portfolio} onChange={(e) => setLinks({ ...links, portfolio: e.target.value })} />
      <TextField label="GitHub" type="url" value={links.github} onChange={(e) => setLinks({ ...links, github: e.target.value })} />
      <Actions busy={busy} error={error} label="Save links" />
    </form>
  );
}

type Answer = "yes" | "no" | "later";
const toAnswer = (v: boolean | null): Answer => (v === true ? "yes" : v === false ? "no" : "later");
const fromAnswer = (a: Answer) => (a === "yes" ? true : a === "no" ? false : null);
const YES_NO_LATER: Array<{ value: Answer; label: string }> = [
  { value: "yes", label: "Yes" }, { value: "no", label: "No" }, { value: "later", label: "I'll answer later" },
];

export function AuthorizationEditor({ data, onSaved }: EditorProps) {
  const [authorized, setAuthorized] = useState(toAnswer(data.authorization.authorized_to_work));
  const [sponsorship, setSponsorship] = useState(toAnswer(data.authorization.sponsorship_required));
  const { busy, error, save } = useSave(onSaved);
  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => {
      e.preventDefault();
      void save("/profile/authorization", { authorized_to_work: fromAnswer(authorized), sponsorship_required: fromAnswer(sponsorship) }, () => "Answers saved.");
    }}>
      <p className="text-[15px] text-muted">
        Employers ask these on most applications. Only you can answer them. Job Copilot never infers or drafts work
        authorization, sponsorship, criminal-history, disability or demographic answers.
      </p>
      <RadioGroup legend="Are you legally authorized to work in the country where you're searching?" name="cp-authorized"
        value={authorized} options={YES_NO_LATER} onChange={setAuthorized} />
      <RadioGroup legend="Will you now or in the future need an employer to sponsor a work visa?" name="cp-sponsorship"
        value={sponsorship} options={YES_NO_LATER} onChange={setSponsorship} />
      <Actions busy={busy} error={error} label="Save answers" />
    </form>
  );
}

export function GoalsEditor({ data, onSaved }: EditorProps) {
  const [editing, setEditing] = useState(!data.preferences.job_title);
  if (editing) {
    return <GoalsWizard profile={data} onSaved={(p) => { setEditing(false); onSaved(p); }}
      onCancel={data.preferences.job_title ? () => setEditing(false) : undefined} doneLabel="Save goals" />;
  }
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-[minmax(0,10rem)_1fr] gap-x-4 gap-y-2">
        {data.goals_summary.map((row) => (
          <div key={row.label} className="contents">
            <dt className="text-muted">{row.label}</dt>
            <dd className="font-semibold">{row.value}</dd>
          </div>
        ))}
      </dl>
      <Button className="self-start" onClick={() => setEditing(true)}>Edit goals</Button>
    </div>
  );
}

export function AnswersEditor({ data, onSaved }: EditorProps) {
  const toast = useToast();
  const [answers, setAnswers] = useState<SavedAnswer[]>(data.answers);
  const [draft, setDraft] = useState({ question: "", answer: "" });
  const [error, setError] = useState<string | null>(null);

  async function run(promise: Promise<{ answers: SavedAnswer[] }>, message: string) {
    setError(null);
    try {
      const result = await promise;
      setAnswers(result.answers);
      onSaved({ ...data, answers: result.answers });
      toast(message);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[15px] text-muted">
        Answers you wrote and approved for application questions. Job Copilot reuses them for the same question and
        never writes an answer for you.
      </p>
      {answers.map((a) => (
        <SavedAnswerRow key={a.question_key} entry={a}
          onSave={(text) => run(api("/answers", { method: "POST", json: { question: a.question, answer: text } }), "Answer saved.")}
          onDelete={() => run(api(`/answers/${encodeURIComponent(a.question_key)}`, { method: "DELETE" }), "That answer won't be reused.")} />
      ))}
      <form className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-4" onSubmit={(e) => {
        e.preventDefault();
        void run(api("/answers", { method: "POST", json: draft }), "Answer saved.").then(() => setDraft({ question: "", answer: "" }));
      }}>
        <h3 className="font-semibold">Add an answer</h3>
        <TextField label="Question, as employers ask it" value={draft.question} onChange={(e) => setDraft({ ...draft, question: e.target.value })} />
        <TextArea label="Your answer" rows={3} value={draft.answer} onChange={(e) => setDraft({ ...draft, answer: e.target.value })} />
        <Button type="submit" variant="primary" className="self-start" disabled={!draft.question.trim() || !draft.answer.trim()}>Add answer</Button>
      </form>
      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
    </div>
  );
}

function SavedAnswerRow({ entry, onSave, onDelete }: { entry: SavedAnswer; onSave: (t: string) => void; onDelete: () => void }) {
  const [text, setText] = useState(entry.answer);
  return (
    <details className="rounded-[var(--radius-card)] border border-line p-4">
      <summary className="cursor-pointer font-semibold">{entry.question}</summary>
      <div className="mt-3 flex flex-col gap-3">
        <TextArea label="Your answer" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" onClick={() => onSave(text)} disabled={!text.trim()}>Save answer</Button>
          <Button variant="danger" onClick={onDelete}><Trash2 aria-hidden className="size-4" /> Stop reusing this answer</Button>
        </div>
      </div>
    </details>
  );
}

export const EDITORS: Record<string, (p: EditorProps) => React.JSX.Element> = {
  contact: ContactEditor, summary: SummaryEditor, work: WorkEditor, education: EducationEditor,
  skills: SkillsEditor, certifications: CertificationsEditor, links: LinksEditor, goals: GoalsEditor,
  authorization: AuthorizationEditor, answers: AnswersEditor,
};
