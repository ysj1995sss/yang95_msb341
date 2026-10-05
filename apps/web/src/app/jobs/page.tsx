"use client";

import { ArrowLeft, Search } from "lucide-react";
import { useState } from "react";
import { Alert, Button, Card, Chip, ErrorBox, PageHeader, Spinner, cx, toneOf } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { JobForm, JobsList, JobsSetup } from "@/lib/types";
import { JobDetailPanel } from "./job-detail";
import { SearchForm } from "./search-form";

const VIEWS = [
  { key: "best", label: "Best matches" },
  { key: "newest", label: "Newest" },
  { key: "saved", label: "Saved" },
] as const;

const ASIDE = (
  <Card>
    <h2 className="text-[18px] font-semibold">What you get</h2>
    <p className="mt-2 text-muted">Each role shows why it may fit you, what is genuinely missing, and what the posting doesn&apos;t say.</p>
    <p className="mt-2 text-muted">Nothing is submitted from here. Choosing a role opens Tailor with the posting loaded.</p>
  </Card>
);

export default function JobsPage() {
  const setup = useResource<JobsSetup>("/jobs/setup");
  const [view, setView] = useState<"best" | "newest" | "saved">("best");
  const list = useResource<JobsList>(setup.data && (setup.data.searched || view === "saved") ? `/jobs?view=${view}` : null);
  const [editing, setEditing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false); // phones: list or detail, one at a time
  const [more, setMore] = useState<{ key: string; rows: JobsList["rows"] }>({ key: "", rows: [] });
  const [loadingMore, setLoadingMore] = useState(false);

  async function search(form: JobForm) {
    setSearching(true);
    setSearchError(null);
    try {
      const result = await api<JobsList>("/jobs/search", { method: "POST", json: form });
      setView("best");
      list.set(result);
      setSelected(null);
      setEditing(false);
      setup.reload();
    } catch (e) {
      setSearchError((e as Error).message);
    } finally {
      setSearching(false);
    }
  }

  const header = <PageHeader title="Jobs" description="Find a real role worth preparing an application for. Nothing is submitted from here." />;
  if (setup.error) return <>{header}<ErrorBox error={setup.error} retry={setup.reload} /></>;
  if (!setup.data) return <>{header}<Spinner label="Loading your search" /></>;
  const s = setup.data;

  const form = (compact: boolean) => (
    <SearchForm key={s.summary_line} setup={s} busy={searching} error={searchError} onSearch={search}
      onCancel={compact ? () => setEditing(false) : undefined} />
  );

  if (!s.searched && view !== "saved") {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <Card>
            {s.has_goals && !editing ? (
              <>
                <p className="text-[14px] font-semibold tracking-wide text-primary uppercase">Your search</p>
                <h2 className="mt-1 text-[22px] font-semibold">{s.summary_line}</h2>
                <p className="mt-1 text-muted">Live openings from {s.board_count} company boards on Greenhouse, Lever, Ashby and SmartRecruiters.</p>
                {searchError && <div className="mt-3"><Alert tone="blocked" role="alert">{searchError}</Alert></div>}
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button variant="primary" busy={searching} onClick={() => search(s.form)}>
                    <Search aria-hidden className="size-4" /> {searching ? `Searching ${s.board_count} company boards` : "Find matching jobs"}
                  </Button>
                  <Button onClick={() => setEditing(true)}>Edit search</Button>
                  {s.saved_count > 0 && <Button variant="ghost" onClick={() => setView("saved")}>View {s.saved_count} saved</Button>}
                </div>
              </>
            ) : (
              <>
                <h2 className="text-[22px] font-semibold">Find a role worth preparing for</h2>
                <p className="mb-5 text-muted">Live openings from {s.board_count} company boards on Greenhouse, Lever, Ashby and SmartRecruiters.</p>
                {form(s.has_goals)}
              </>
            )}
          </Card>
          {ASIDE}
        </div>
      </>
    );
  }

  const data = list.data;
  // Extra pages belong to the list they were loaded for (same view, same search time).
  const listKey = `${view}|${data?.searched_at ?? ""}|${data?.total ?? 0}`;
  const rows = [...(data?.rows ?? []), ...(more.key === listKey ? more.rows : [])];
  const total = data?.total ?? 0;
  async function showMore() {
    setLoadingMore(true);
    try {
      const next = await api<JobsList>(`/jobs?view=${view}&offset=${rows.length}`);
      setMore({ key: listKey, rows: [...(more.key === listKey ? more.rows : []), ...next.rows] });
    } catch (e) {
      setSearchError((e as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }
  const current = rows.find((r) => r.job_id === selected)?.job_id ?? rows[0]?.job_id ?? null;
  const meta = data ? (view === "saved"
    ? [`${total} saved ${total === 1 ? "job" : "jobs"}`]
    : [`${total} matching ${total === 1 ? "role" : "roles"}`,
      data.searched_at ? `searched ${new Date(data.searched_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}` : "",
      data.source_note]).filter(Boolean).join(" · ") : "";

  return (
    <>
      {header}
      <div className="mb-4 flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-paper p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-semibold">{data?.summary_line || s.summary_line}</p>
          <p className={cx("text-[14px]", data?.partial_failure ? "font-semibold text-review" : "text-muted")}>{meta}</p>
          {data?.coverage_notes.map((n) => <p key={n} className="text-[14px] text-muted">{n}</p>)}
        </div>
        <div className="flex shrink-0 gap-2">
          <Button onClick={() => setEditing(!editing)} aria-expanded={editing}>Edit search</Button>
          <Button variant="primary" busy={searching} disabled={!s.has_goals} onClick={() => search(s.form)}>Search again</Button>
        </div>
      </div>
      {searching && <div className="mb-4"><Alert tone="primary" role="status">Searching {s.board_count} company boards… Your current results stay here until the new ones arrive.</Alert></div>}
      {searchError && !editing && <div className="mb-4"><Alert tone="blocked" role="alert">{searchError}</Alert></div>}
      {editing && <Card className="mb-6"><h2 className="mb-4 text-[18px] font-semibold">Edit search</h2>{form(true)}</Card>}

      <div role="group" aria-label="Show" className="mb-4 inline-flex rounded-[var(--radius-control)] border border-line-strong bg-paper p-1">
        {VIEWS.map((v) => (
          <button key={v.key} aria-pressed={view === v.key} type="button"
            onClick={() => { setView(v.key); setSelected(null); setShowDetail(false); }}
            className={cx("min-h-10 rounded-[3px] px-4 text-[15px] font-semibold transition-colors duration-150 cursor-pointer",
              view === v.key ? "bg-primary text-on-primary" : "text-muted hover:text-ink")}>
            {v.label}
          </button>
        ))}
      </div>

      {list.error ? <ErrorBox error={list.error} retry={list.reload} /> : !data ? <Spinner label="Loading jobs" /> : rows.length === 0 ? (
        <Card>
          {view === "saved" ? (
            <p><span className="font-semibold">No saved jobs yet.</span> Choose <span className="font-semibold">Save</span> on a role to keep it here.</p>
          ) : (
            <>
              <p><span className="font-semibold">No open postings matched this search.</span> Try a broader role name, another location, or no work-mode preference.</p>
              <Button variant="primary" className="mt-4" onClick={() => setEditing(true)}>Edit search</Button>
            </>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,0.62fr)_minmax(0,1fr)]">
          <Card className={cx("p-0 sm:p-0 lg:block", showDetail && "hidden")} aria-labelledby="results-heading">
            <h2 id="results-heading" className="sr-only">Results</h2>
            <ul className="max-h-[70vh] divide-y divide-line overflow-y-auto">
              {rows.map((r) => {
                const active = r.job_id === current;
                return (
                  <li key={r.job_id}>
                    <button type="button" aria-current={active ? "true" : undefined}
                      onClick={() => { setSelected(r.job_id); setShowDetail(true); window.scrollTo({ top: 0 }); }}
                      className={cx("flex w-full flex-col gap-1 border-l-4 px-4 py-3 text-left transition-colors duration-150 cursor-pointer",
                        active ? "border-primary bg-primary-soft" : "border-transparent hover:bg-canvas", r.status === "Passed" && "opacity-60")}>
                      <span className="font-semibold">{r.title}</span>
                      <span className="text-[14px] text-muted">
                        {[r.company, r.location, r.work_mode !== "Work mode not stated" ? r.work_mode : "", r.salary !== "No salary stated" ? r.salary : "", r.freshness].filter(Boolean).join(" · ")}
                      </span>
                      <span className="flex flex-wrap gap-1.5">
                        <Chip tone={toneOf(r.fit_tone)}>{r.fit}</Chip>
                        {["Saved", "Passed", "Preparing application"].includes(r.status) && <Chip tone="primary">{r.status}</Chip>}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {rows.length < total && (
              <div className="border-t border-line p-3">
                <Button className="w-full" busy={loadingMore} onClick={showMore}>
                  Show more ({total - rows.length} left)
                </Button>
              </div>
            )}
          </Card>
          <div className={cx("lg:block", !showDetail && "hidden")}>
            <Button variant="ghost" className="mb-3 lg:hidden" onClick={() => setShowDetail(false)}>
              <ArrowLeft aria-hidden className="size-4" /> Back to results
            </Button>
            {current && (
              <Card>
                <JobDetailPanel key={current} jobId={current} onChanged={list.reload} />
              </Card>
            )}
          </div>
        </div>
      )}
    </>
  );
}
