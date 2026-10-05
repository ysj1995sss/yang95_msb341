"use client";

import { ArrowRight, CheckCircle2, Circle, CircleAlert } from "lucide-react";
import { GoalsWizard } from "@/components/goals-wizard";
import { ResumeUpload } from "@/components/resume-upload";
import { Card, ErrorBox, LinkButton, PageHeader, Spinner, cx } from "@/components/ui";
import { useResource } from "@/lib/api";
import type { HomeResponse, Item, NextAction, ProfileResponse } from "@/lib/types";

const STATE_ICONS = {
  ready: { icon: CheckCircle2, className: "text-verified", label: "Ready" },
  attention: { icon: CircleAlert, className: "text-review", label: "Needs attention" },
  not_started: { icon: Circle, className: "text-line-strong", label: "Not started" },
} as const;

function NextStep({ action, onDone }: { action: NextAction; onDone: () => void }) {
  const profile = useResource<ProfileResponse>(action.inline === "goals" ? "/profile" : null);
  return (
    <Card aria-labelledby="next-step" className="border-primary/40">
      <p className="text-[14px] font-semibold tracking-wide text-primary uppercase">Your next step</p>
      <h2 id="next-step" className="mt-1 text-[24px] font-semibold">{action.title}</h2>
      <p className="mt-1">{action.why}</p>
      <p className="mt-1 text-muted">{action.value}</p>
      <div className="mt-5">
        {action.inline === "upload" && <ResumeUpload onImported={onDone} />}
        {action.inline === "goals" && (profile.data
          ? <GoalsWizard profile={profile.data} onSaved={onDone} doneLabel="Save goals and continue" />
          : <Spinner label="Loading your goals" />)}
        {!action.inline && action.page && (
          <LinkButton href={action.page} variant="primary">
            {action.label} <ArrowRight aria-hidden className="size-4" />
          </LinkButton>
        )}
      </div>
    </Card>
  );
}

function ItemList({ title, items, empty }: { title: string; items: Item[]; empty: string }) {
  return (
    <Card>
      <h2 className="text-[18px] font-semibold">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-2 text-muted">{empty}</p>
      ) : (
        <ul className="mt-3 divide-y divide-line">
          {items.map((item) => (
            <li key={`${item.title}-${item.detail}`}>
              <a href={item.page || "#"} className="flex min-h-11 items-center justify-between gap-3 py-2 hover:text-primary">
                <span>
                  <span className="font-semibold">{item.title}</span>
                  {item.detail && <span className="block text-[14px] text-muted">{item.detail}</span>}
                </span>
                <ArrowRight aria-hidden className="size-4 shrink-0 text-muted" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function HomePage() {
  const { data, error, loading, reload } = useResource<HomeResponse>("/home");
  if (error) return <ErrorBox error={error} retry={reload} />;
  if (loading && !data) return <Spinner label="Loading your workspace" />;
  if (!data) return null;
  const { view } = data;

  if (view.mode === "first_time") {
    return (
      <>
        <PageHeader title="Welcome to Job Copilot"
          description="Truthful tailored resumes for real jobs. Five steps, in any order; here's the one that helps most now." />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <NextStep action={view.next_action} onDone={reload} />
          <Card aria-labelledby="checklist">
            <h2 id="checklist" className="text-[18px] font-semibold">Getting set up</h2>
            <p className="text-[14px] text-muted">{view.completed} of {view.checklist.length} done</p>
            <ol className="mt-4 flex flex-col gap-3">
              {view.checklist.map((entry) => {
                const s = STATE_ICONS[entry.state as keyof typeof STATE_ICONS] ?? STATE_ICONS.not_started;
                const Icon = s.icon;
                return (
                  <li key={entry.label} className="flex gap-3">
                    <Icon aria-hidden className={cx("mt-0.5 size-5 shrink-0", s.className)} />
                    <span>
                      <span className="font-semibold">{entry.label}</span>
                      <span className="sr-only"> — {s.label}</span>
                      {entry.detail && <span className="block text-[14px] text-muted">{entry.detail}</span>}
                    </span>
                  </li>
                );
              })}
            </ol>
          </Card>
        </div>
      </>
    );
  }

  const goal = data.weekly_goal;
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  return (
    <>
      <PageHeader title={data.first_name ? `Welcome back, ${data.first_name}` : "Welcome back"}
        description={`${today}. Here's what needs you.`} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div className="flex flex-col gap-6">
          <NextStep action={view.next_action} onDone={reload} />
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ItemList title="Follow-ups due" items={view.followups_due} empty="Nothing due. Add next steps in Tracker." />
            <ItemList title="Ready to finish" items={view.ready_to_finish} empty="No staged applications waiting." />
            <ItemList title="Resumes awaiting your decisions" items={view.drafts} empty="No tailoring drafts open." />
            <ItemList title="Saved jobs" items={view.saved_jobs} empty="No saved jobs. Save roles from Jobs to compare later." />
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <Card aria-labelledby="week">
            <h2 id="week" className="text-[18px] font-semibold">This week</h2>
            <p className="mt-2 font-[family-name:var(--font-heading)] text-[40px] leading-none font-semibold">{data.weekly.applied}</p>
            <p className="text-muted">applications sent</p>
            {goal > 0 ? (
              <>
                <div className="mt-3 h-2 rounded-full bg-line" role="progressbar" aria-label="Weekly goal"
                  aria-valuemin={0} aria-valuemax={goal} aria-valuenow={Math.min(data.weekly.applied, goal)}>
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, (data.weekly.applied / goal) * 100)}%` }} />
                </div>
                <p className="mt-2 text-[14px] text-muted">{data.weekly.applied} of your goal of {goal}. A steady pace beats a burst.</p>
              </>
            ) : (
              <p className="mt-2 text-[14px] text-muted">Set a weekly goal in Career Profile → Job goals if it helps you pace yourself.</p>
            )}
            <p className="mt-3 text-[14px]">{data.weekly.interviews} in interviews · {data.weekly.saved} saved</p>
          </Card>
          <Card aria-labelledby="recent">
            <h2 id="recent" className="text-[18px] font-semibold">Recent activity</h2>
            {data.recent.length === 0 ? <p className="mt-2 text-muted">Nothing yet.</p> : (
              <ul className="mt-3 flex flex-col gap-2 text-[15px]">
                {data.recent.map((r) => (
                  <li key={`${r.date}-${r.role}-${r.company}`}>
                    <span className="text-muted">{new Date(r.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })} · </span>
                    {r.role} at {r.company}: <span className="font-semibold">{r.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
