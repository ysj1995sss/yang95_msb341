"use client";

import { Download, LogOut, Trash2 } from "lucide-react";
import { useState } from "react";
import { Alert, Button, Card, TextField, useToast } from "@/components/ui";
import { api } from "@/lib/api";

/** Download everything, sign out on every device, delete everything (decision 030). */
export function YourData({ signedIn }: { signedIn: boolean }) {
  const toast = useToast();
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function signOutEverywhere() {
    setBusy("signout");
    try {
      await api("/account/sign-out-everywhere", { method: "POST" });
      window.location.assign(new URL("/signin", window.location.origin).href);
    } catch (e) {
      toast((e as Error).message);
      setBusy(null);
    }
  }

  async function deleteEverything() {
    setBusy("delete");
    try {
      await api("/account", { method: "DELETE", json: { confirm } });
      if (signedIn) await fetch("/api/auth/signout", { method: "POST" });
      window.location.assign(new URL(signedIn ? "/signin" : "/", window.location.origin).href);
    } catch (e) {
      toast((e as Error).message);
      setBusy(null);
    }
  }

  return (
    <Card aria-labelledby="your-data" className="mt-6">
      <h2 id="your-data" className="text-[20px] font-semibold">Your data</h2>
      <p className="mt-1 text-[15px] text-muted">
        Everything Job Copilot keeps for you: your Career Profile and resume versions, jobs, applications, tailored
        resumes and saved answers. Download it any time; it&apos;s also your own backup.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {/* A file download, so a plain link (with the download attribute) rather than client navigation. */}
        <a href="/api/backend/account/export" download
          className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] border border-line-strong bg-paper px-4 text-[15px] font-semibold hover:bg-canvas">
          <Download aria-hidden className="size-4" /> Download my data
        </a>
        {signedIn && (
          <Button busy={busy === "signout"} onClick={signOutEverywhere}>
            <LogOut aria-hidden className="size-4" /> Sign out on every device
          </Button>
        )}
      </div>
      <details className="mt-5 rounded-[var(--radius-card)] border border-blocked/30 p-4">
        <summary className="cursor-pointer font-semibold text-blocked">Delete my account and data</summary>
        <div className="mt-3 flex flex-col gap-3">
          <Alert tone="blocked">This permanently deletes everything above. It can&apos;t be undone. Download your data first if you want a copy.</Alert>
          <TextField label="Type DELETE to confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" />
          <Button variant="danger" className="self-start" disabled={confirm !== "DELETE"} busy={busy === "delete"} onClick={deleteEverything}>
            <Trash2 aria-hidden className="size-4" /> Delete everything
          </Button>
        </div>
      </details>
    </Card>
  );
}
