"use client";

import { useId, useState } from "react";
import { Alert, Button, Checkbox, MultiSelect, SelectField, TextField } from "@/components/ui";
import type { CustomBoard, JobForm, JobsSetup } from "@/lib/types";
import { CompanyBoards } from "./boards";

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
  const placesId = useId();
  const places = setup.options.locations ?? []; // absent on older servers: a plain text box
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
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[2fr_1fr]">
        <TextField label="Target role" required value={form.job_title} placeholder="e.g. Product marketing manager"
          help={help.title_rule} onChange={(e) => set({ job_title: e.target.value })} />
        <SelectField label="Work mode" value={form.remote_preference} options={setup.options.work_modes}
          className="md:self-end"
          onChange={(e) => set({ remote_preference: e.target.value, work_mode_stated_only: e.target.value === "remote" })} />
        {form.remote_preference !== "any" && (
          // Most job boards don't state a work mode. Remote starts with only jobs that say so (a city-only
          // listing is rarely remote; dogfood, 2026-10-13); untick to include "Work mode not stated" jobs.
          // Sits in the Work mode column, under the choice it belongs to.
          <div className="-mt-3 md:col-start-2">
            <Checkbox label={`Only jobs that say they're ${setup.options.work_modes.find((m) => m.value === form.remote_preference)?.label.toLowerCase() ?? form.remote_preference}`}
              checked={Boolean(form.work_mode_stated_only)} onChange={(v) => set({ work_mode_stated_only: v })} />
          </div>
        )}
      </div>
      {/* The main filters as dropdowns (2026-10-13). Location suggests places real postings name, and any
          typed text still works; the others open tick boxes, so several can be chosen. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <TextField label="Location" value={form.location} placeholder="City, state or country"
          list={places.length ? placesId : undefined} autoComplete="off"
          onChange={(e) => set({ location: e.target.value })} />
        {places.length > 0 && <datalist id={placesId}>{places.map((p) => <option key={p} value={p} />)}</datalist>}
        <MultiSelect label="Level" options={setup.options.experience_levels} value={form.experience_level}
          onChange={(v) => set({ experience_level: v })} />
        <MultiSelect label="Job type" options={setup.options.employment_types} value={form.employment_type}
          onChange={(v) => set({ employment_type: v })} />
        <MultiSelect label="Industry" options={setup.options.industries} value={form.industries}
          onChange={(v) => set({ industries: v })} />
      </div>
      <details className="rounded-[var(--radius-card)] border border-line p-4">
        <summary className="cursor-pointer font-semibold">More filters</summary>
        <div className="mt-4 flex flex-col gap-5">
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
