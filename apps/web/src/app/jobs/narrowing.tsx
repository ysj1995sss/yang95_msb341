"use client";

// Spec 013: when a search finds few roles, say which filters are hiding roles and offer broader
// titles. Each button is the person's own choice to search again; nothing changes by itself.

import { Button, Card } from "@/components/ui";
import type { JobForm, JobsList, Narrowing } from "@/lib/types";

const CLEARED: Partial<Record<keyof JobForm, JobForm[keyof JobForm]>> = {
  location: "", remote_preference: "any", sponsorship_required: false, experience_level: [], industries: [],
  employment_type: [], min_salary: 0, target_companies: "", exclude_companies: "",
};

export function withoutFilter(form: JobForm, key: Narrowing["key"]): JobForm {
  return key in CLEARED ? { ...form, [key]: CLEARED[key] } : form;
}

export function SearchHelpPanel({ data, form, busy, onSearch }: {
  data: JobsList; form: JobForm; busy: boolean; onSearch: (form: JobForm) => void;
}) {
  const hasHelp = data.narrowing.length > 0 || data.broader_titles.length > 0 || data.company_notes.length > 0;
  if (!hasHelp) return null;
  return (
    <Card className="mb-4" aria-labelledby="narrowing-heading">
      <h2 id="narrowing-heading" className="text-[18px] font-semibold">What&apos;s narrowing your results</h2>
      {data.company_notes.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {data.company_notes.map((n) => <li key={n} className="text-[15px]">{n}</li>)}
        </ul>
      )}
      {data.narrowing.length > 0 && (
        <ul className="mt-3 flex flex-col gap-2">
          {data.narrowing.map((n) => (
            <li key={n.key} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-[15px]">{n.text}</span>
              <Button busy={busy} onClick={() => onSearch(withoutFilter(form, n.key))}>Search without this filter</Button>
            </li>
          ))}
        </ul>
      )}
      {data.broader_titles.length > 0 && (
        <div className="mt-4">
          <p className="text-[15px]">{data.help.title_rule} Broader titles to try:</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.broader_titles.map((t) => (
              <Button key={t} busy={busy} onClick={() => onSearch({ ...form, job_title: t })}>Search “{t}”</Button>
            ))}
          </div>
        </div>
      )}
      <p className="mt-4 text-[14px] text-muted">{data.help.paste}</p>
    </Card>
  );
}
