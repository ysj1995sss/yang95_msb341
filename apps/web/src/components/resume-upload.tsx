"use client";

import { UploadCloud } from "lucide-react";
import { useId, useState } from "react";
import { Alert, Button, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { ProfileResponse } from "@/lib/types";

/** Import (or replace) the resume behind the Career Profile. */
export function ResumeUpload({ onImported, label = "Your resume (Word or PDF)", cta = "Import resume" }: {
  onImported: (profile: ProfileResponse) => void; label?: string; cta?: string;
}) {
  const id = useId();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch("/api/backend/profile/resume", { method: "POST", body });
      if (!response.ok) {
        const detail = (await response.json().catch(() => ({})))?.detail;
        throw new ApiError(typeof detail === "string" ? detail : "We couldn't read that file.", response.status);
      }
      onImported((await response.json()) as ProfileResponse);
      toast("Resume imported. Review what needs attention.");
      setFile(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <label htmlFor={id}
        className="flex cursor-pointer flex-col items-center gap-2 rounded-[var(--radius-card)] border-2 border-dashed border-line-strong bg-canvas px-4 py-8 text-center hover:border-primary">
        <UploadCloud aria-hidden className="size-8 text-primary" />
        <span className="font-semibold">{file ? file.name : label}</span>
        <span className="text-[14px] text-muted">.docx or .pdf, up to 10 MB. Word keeps your exact layout in tailored versions.</span>
        <input id={id} type="file" accept=".docx,.pdf" className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </label>
      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
      <Button variant="primary" onClick={submit} disabled={!file} busy={busy} className="self-start">
        {busy ? "Reading your resume" : cta}
      </Button>
    </div>
  );
}
