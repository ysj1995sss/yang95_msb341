"use client";

// Spec 013: add a company's public career board, see each added board's last result, remove one.
// A board is saved only after its platform confirms it exists; the wording comes from the API
// (ui/search_help.py), so Streamlit says the same.

import { useState } from "react";
import { Alert, Button, Chip, SelectField, TextField, toneOf } from "@/components/ui";
import { api } from "@/lib/api";
import type { CustomBoard, SearchHelp } from "@/lib/types";

type Added = { message: string; board: CustomBoard; custom_boards: CustomBoard[] };

export function CompanyBoards({ boards, max, help, industries, onChange }: {
  boards: CustomBoard[]; max: number; help: SearchHelp; industries: string[];
  onChange: (boards: CustomBoard[]) => void;
}) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const full = boards.length >= max;

  async function add() {
    if (!url.trim() || busy) return;
    setBusy(true);
    setResult(null);
    try {
      const added = await api<Added>("/boards", { method: "POST", json: { url, name, industry } });
      onChange(added.custom_boards);
      setResult({ ok: true, text: added.message });
      setUrl("");
      setName("");
      setIndustry("");
    } catch (e) {
      setResult({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function remove(board: CustomBoard) {
    setRemoving(board.id);
    try {
      const left = await api<{ custom_boards: CustomBoard[] }>(`/boards/${encodeURIComponent(board.id)}`, { method: "DELETE" });
      onChange(left.custom_boards);
      setResult({ ok: true, text: `Removed ${board.name}. Jobs you already found from it stay in your lists.` });
    } catch (e) {
      setResult({ ok: false, text: (e as Error).message });
    } finally {
      setRemoving(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {boards.length > 0 && (
        <div>
          <h3 className="text-[15px] font-semibold">Your added boards ({boards.length} of {max})</h3>
          <ul className="mt-2 divide-y divide-line rounded-[var(--radius-card)] border border-line">
            {boards.map((b) => (
              <li key={b.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold">
                    {b.name} <span className="font-normal text-muted">· {b.platform}{b.industry !== "Not specified" ? ` · ${b.industry}` : ""}</span>
                  </p>
                  <p className="mt-1 flex flex-wrap items-center gap-2 text-[14px]">
                    <Chip tone={toneOf(b.tone)}>{b.tone === "blocked" ? "Not found" : b.tone === "review" ? "Didn't answer" : "Live board"}</Chip>
                    <span className="text-muted">{b.status}</span>
                  </p>
                </div>
                <Button variant="ghost" busy={removing === b.id} onClick={() => remove(b)} aria-label={`Remove ${b.name}`}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div
        className="flex flex-col gap-3"
        // Enter adds the board here instead of submitting the search form around it.
        onKeyDown={(e) => { if (e.key === "Enter" && (e.target as HTMLElement).tagName === "INPUT") { e.preventDefault(); add(); } }}
      >
        <h3 className="text-[15px] font-semibold">Add a company career board</h3>
        <p className="text-[14px] text-muted">{help.add_board}</p>
        <TextField label="Career board link" value={url} disabled={full} inputMode="url"
          placeholder="e.g. https://job-boards.greenhouse.io/company" onChange={(e) => setUrl(e.target.value)} />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <TextField label="Company name (optional)" help="Shown on its jobs. Taken from the board when it says." value={name}
            disabled={full} onChange={(e) => setName(e.target.value)} />
          <SelectField label="Industry (optional)" value={industry} disabled={full}
            options={[{ value: "", label: "Not specified" }, ...industries.map((i) => ({ value: i, label: i }))]}
            onChange={(e) => setIndustry(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={add} busy={busy} disabled={!url.trim() || full}>{busy ? "Checking the board" : "Check and add board"}</Button>
          {full && <p className="text-[14px] text-muted">{help.limit} Remove one to add another.</p>}
        </div>
        {result && (
          <Alert tone={result.ok ? "verified" : "blocked"} role={result.ok ? "status" : "alert"}>{result.text}</Alert>
        )}
      </div>
    </div>
  );
}
