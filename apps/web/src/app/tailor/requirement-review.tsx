"use client";

import { CircleAlert, CircleCheck, CircleMinus, CircleX } from "lucide-react";
import { Chip, cx } from "@/components/ui";
import type { Readability, RequirementReviewView, RequirementRowView } from "@/lib/types";

/** Spec 010: each requirement with the exact posting text and the exact evidence behind it. */
export function RequirementReview({ review }: { review: RequirementReviewView }) {
  return (
    <section aria-labelledby="requirement-review" className="flex flex-col gap-3">
      <h3 id="requirement-review" className="text-[18px] font-semibold">Requirement review</h3>
      <p className="text-[15px] text-muted">
        {review.summary}. Each line shows the posting&apos;s words and the exact fact behind the status. Only
        requirements with direct or transferable evidence are made clearer; the rest are never added.
      </p>
      {review.note && <p className="text-[14px] text-muted">{review.note}</p>}
      {review.groups.map((group) => (
        <div key={group.section}>
          <h4 className="mb-1.5 text-[14px] font-semibold tracking-wide text-muted uppercase">{group.label}</h4>
          <ul className="flex flex-col gap-1.5">{group.rows.map((row) => <Row key={row.id} row={row} />)}</ul>
        </div>
      ))}
    </section>
  );
}

function Row({ row }: { row: RequirementRowView }) {
  return (
    <li>
      <details className="rounded-[var(--radius-control)] border border-line bg-paper px-3 py-2">
        <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-[15px]">
          <Chip tone={row.tone}>{row.label}</Chip>
          {row.hard_gate && row.status === "none" && <Chip tone="blocked">Hard requirement</Chip>}
          <span className="min-w-0 flex-1">{row.text}</span>
          {row.shown_in_resume === true && <span className="text-[14px] text-verified">Shown in this resume</span>}
          {row.shown_in_resume === false && <span className="text-[14px] text-muted">Not shown yet</span>}
        </summary>
        <div className="mt-2 flex flex-col gap-2 text-[15px]">
          <p className="text-muted">{row.reason}</p>
          {row.evidence.map((e) => (
            <blockquote key={e.source + e.text} className="border-l-4 border-line-strong pl-3">
              <p>&ldquo;{e.text}&rdquo;</p>
              <p className="text-[14px] text-muted">{e.source}{e.confirmed ? " · confirmed by you" : " · not confirmed yet"}</p>
            </blockquote>
          ))}
        </div>
      </details>
    </li>
  );
}

const STATE_ICON = {
  ok: { icon: CircleCheck, className: "text-verified", word: "Passed" },
  warn: { icon: CircleAlert, className: "text-review", word: "Warning" },
  fail: { icon: CircleX, className: "text-blocked", word: "Failed" },
  not_checked: { icon: CircleMinus, className: "text-muted", word: "Not checked for this version" },
} as const;

/** Spec 010: what the local readability check found, line by line. */
export function ReadabilityCheck({ readability }: { readability: Readability }) {
  const problems = readability.items.some((i) => i.state === "fail" || i.state === "warn");
  return (
    <details open={problems} className="rounded-[var(--radius-card)] border border-line bg-paper p-4 text-[15px]">
      <summary className="cursor-pointer font-semibold">Readability check</summary>
      <p className="mt-2 text-[14px] text-muted">{readability.note}</p>
      <ul className="mt-2 flex flex-col gap-1.5">
        {readability.items.map((item) => {
          const s = STATE_ICON[item.state];
          return (
            <li key={item.label} className="flex gap-2">
              <s.icon aria-hidden className={cx("mt-0.5 size-4 shrink-0", s.className)} />
              <span><span className="sr-only">{s.word}: </span>{item.label}{item.message && <span className="block text-[14px] text-muted">{item.message}</span>}</span>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
