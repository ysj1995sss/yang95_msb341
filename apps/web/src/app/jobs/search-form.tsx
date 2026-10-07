"use client";

import { useState } from "react";
import { Alert, Button, Checkbox, SelectField, TextField, cx } from "@/components/ui";
import type { CustomBoard, JobForm, JobsSetup } from "@/lib/types";
import { CompanyBoards } from "./boards";

function Toggles({ legend, options, value, onChange }: {
  legend: string; options: string[]; value: string[]; onChange: (v: string[]) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-[15px] font-semibold">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = value.includes(o);
          return (
            <button key={o} type="button" aria-pressed={on}
              onClick={() => onChange(on ? value.filter((v) => v !== o) : [...value, o])}
              className={cx("min-h-11 rounded-full border px-3.5 text-[14px] font-semibold capitalize transition-colors duration-150 cursor-pointer",
                on ? "border-primary bg-primary-soft text-primary" : "border-line-strong bg-paper hover:bg-canvas")}>
              {o}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

/** Boards a search with these choices asks (spec 013): curated boards on the ticked sources plus added ones. */
export function boardsInScope(setup: JobsSetup, form: JobForm, boards: CustomBoard[]) {
  const curated = setup.options.sources.filter((s) => form.sources.includes(s.value)).reduce((n, s) => n + s.curated_count, 0);
  return curated + (form.include_custom ? boards.length : 0);
}

export function SearchForm({ setup, busy, error, onSearch, onCancel, onBoardsChanged }: {
  setup: JobsSetup; busy: boolean; error: string | null;
  onSearch: (form: JobForm) => void; onCancel?: () => void; onBoardsChanged?: () => void;
}) {
  const [form, setForm] = useState<JobForm>(setup.form);
  const [boards, setBoards] = useState<CustomBoard[]>(setup.custom_boards);
  const set = (patch: Partial<JobForm>) => setForm((f) => ({ ...f, ...patch }));
  const roleMissing = !form.job_title.trim();
  const count = boardsInScope(setup, form, boards);
  const help = setup.help;
  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); if (!roleMissing) onSearch(form); }}>
      {setup.suggested_titles.length > 0 && (
        <div>
          <p className="mb-2 text-[14px] text-muted">From your work history:</p>
          <div className="flex flex-wrap gap-2">
            {setup.suggested_titles.map((t) => <Button key={t} onClick={() => set({ job_title: t })}>{t}</Button>)}
          </div>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.4fr_1.2fr_1fr]">
        <TextField label="Target role" required value={form.job_title} placeholder="e.g. Product marketing manager"
          help={help.title_rule} onChange={(e) => set({ job_title: e.target.value })} />
        <TextField label="Location" value={form.location} placeholder="City, state or country"
          onChange={(e) => set({ location: e.target.value })} />
        <SelectField label="Work mode" value={form.remote_preference} options={setup.options.work_modes}
          onChange={(e) => set({ remote_preference: e.target.value })} />
      </div>
      <details className="rounded-[var(--radius-card)] border border-line p-4">
        <summary className="cursor-pointer font-semibold">More filters</summary>
        <div className="mt-4 flex flex-col gap-5">
          <Toggles legend="Level" options={setup.options.experience_levels} value={form.experience_level} onChange={(v) => set({ experience_level: v })} />
          <Toggles legend="Industry" options={setup.options.industries} value={form.industries} onChange={(v) => set({ industries: v })} />
          <Toggles legend="Job type" options={setup.options.employment_types} value={form.employment_type} onChange={(v) => set({ employment_type: v })} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <TextField label="Minimum salary (USD)" type="number" min={0} step={5000} value={form.min_salary}
              onChange={(e) => set({ min_salary: Math.max(0, Number(e.target.value) || 0) })} />
            <div className="flex flex-col justify-end">
              <Checkbox label="I need visa sponsorship" checked={form.sponsorship_required} onChange={(v) => set({ sponsorship_required: v })} />
              <p className="mb-1 text-[14px] text-muted">{help.sponsorship}</p>
              <Checkbox label="I'm open to relocating" checked={form.relocation_willing} onChange={(v) => set({ relocation_willing: v })} />
            </div>
            <TextField label="Only these companies" help={help.company_filter} value={form.target_companies}
              onChange={(e) => set({ target_companies: e.target.value })} />
            <TextField label="Skip these companies" help="Comma-separated" value={form.exclude_companies}
              onChange={(e) => set({ exclude_companies: e.target.value })} />
          </div>
        </div>
      </details>
      <details className="rounded-[var(--radius-card)] border border-line p-4">
        <summary className="cursor-pointer font-semibold">
          Company boards <span className="font-normal text-muted">· {count} will be searched{boards.length ? ` · ${boards.length} you added` : ""}</span>
        </summary>
        <div className="mt-4 flex flex-col gap-5">
          <fieldset className="flex flex-col gap-1">
            <legend className="text-[15px] font-semibold">Sources</legend>
            <p className="text-[14px] text-muted">{help.sources}</p>
            {setup.options.sources.map((s) => (
              <Checkbox key={s.value} label={s.label} checked={form.sources.includes(s.value)}
                onChange={(on) => set({ sources: on ? [...form.sources, s.value] : form.sources.filter((v) => v !== s.value) })} />
            ))}
            {boards.length > 0 && (
              <Checkbox label={`Your added boards: ${boards.length}`} checked={form.include_custom}
                onChange={(on) => set({ include_custom: on })} />
            )}
          </fieldset>
          <CompanyBoards boards={boards} max={setup.max_custom_boards} help={help} industries={setup.options.industries}
            onChange={(next) => { setBoards(next); onBoardsChanged?.(); }} />
          <p className="text-[14px] text-muted">{help.paste}</p>
        </div>
      </details>
      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" busy={busy} disabled={roleMissing || count === 0}>
          {busy ? `Searching ${count} company ${count === 1 ? "board" : "boards"}` : "Find matching jobs"}
        </Button>
        {onCancel && <Button onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}
