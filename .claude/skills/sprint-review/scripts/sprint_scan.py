#!/usr/bin/env python3
"""Scan local Claude Code session transcripts for a sprint window.

Reads only what it is told to read. --list reads each transcript's recorded working
directory and nothing else; message content is opened solely for the projects named
with --projects. Nothing is sent anywhere.
"""
import argparse, json, os, sys, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"


def project_cwd(jsonl: Path, fallback: str) -> str:
    """The real working directory, read from the first record that carries one.

    The directory name under ~/.claude/projects encodes both "/" and "-" as "-",
    so it cannot be decoded unambiguously. Each transcript records its own cwd.
    """
    try:
        with open(jsonl, "r", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > 40:
                    break
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("cwd"):
                    return d["cwd"]
    except OSError:
        pass
    return fallback


def sessions(since: dt.datetime):
    """Yield (project_dir, jsonl_path, mtime) for sessions active since `since`."""
    if not ROOT.is_dir():
        return
    for proj in sorted(ROOT.iterdir()):
        if not proj.is_dir():
            continue
        for f in proj.glob("*.jsonl"):
            try:
                m = dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc)
            except OSError:
                continue
            if m >= since:
                yield proj, f, m


def cmd_list(since):
    agg = defaultdict(lambda: {"n": 0, "first": None, "last": None})
    for proj, f, m in sessions(since):
        key = project_cwd(f, "?" + proj.name)
        a = agg[key]
        a["n"] += 1
        a["first"] = m if a["first"] is None else min(a["first"], m)
        a["last"] = m if a["last"] is None else max(a["last"], m)
    if not agg:
        print("No sessions found in the window.")
        return
    rows = sorted(agg.items(), key=lambda kv: kv[1]["n"], reverse=True)
    print(f"{'sessions':>8}  {'first':<11} {'last':<11} project")
    for path, a in rows:
        print(f"{a['n']:>8}  {a['first']:%Y-%m-%d}  {a['last']:%Y-%m-%d}  {path}")
    print(f"\n{len(rows)} projects, {sum(a['n'] for _, a in rows)} sessions.")


def user_turns(path):
    """Yield (timestamp, text) for the human's own turns only."""
    try:
        fh = open(path, "r", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "user":
                continue
            msg = d.get("message") or {}
            c = msg.get("content")
            text = ""
            if isinstance(c, str):
                text = c
            elif isinstance(c, list):
                text = " ".join(
                    b.get("text", "") for b in c
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            text = text.strip()
            if text and not text.startswith("<"):
                yield d.get("timestamp", ""), text


def tool_uses(path):
    try:
        fh = open(path, "r", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "assistant":
                continue
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    yield b.get("name", "?")


def cmd_analyze(since, wanted):
    want = {w.rstrip("/") for w in wanted}
    picked = [
        (p, f, m) for p, f, m in sessions(since)
        if any(project_cwd(f, "?" + p.name).rstrip("/").startswith(w) for w in want)
    ]
    if not picked:
        print("No sessions matched those projects.")
        return

    by_day, prompts, tools = Counter(), [], Counter()
    for _p, f, _m in picked:
        for ts, text in user_turns(f):
            if ts:
                by_day[ts[:10]] += 1
            prompts.append((ts, text))
        tools.update(tool_uses(f))

    print(f"SESSIONS: {len(picked)}")
    print(f"PROMPTS: {len(prompts)}")
    print(f"DAYS ACTIVE: {len(by_day)}\n")

    print("ACTIVITY BY DAY")
    for day in sorted(by_day):
        print(f"  {day}  {'#' * min(by_day[day], 50)} {by_day[day]}")

    print("\nTOOL USE")
    for name, n in tools.most_common(12):
        print(f"  {n:>5}  {name}")

    print("\nPROMPTS (chronological, truncated)")
    for ts, text in sorted(prompts, key=lambda x: x[0]):
        one = " ".join(text.split())
        print(f"  [{ts[:16]}] {one[:220]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="ISO date, e.g. 2026-10-12")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--projects", nargs="*", default=[])
    a = ap.parse_args()

    try:
        since = dt.datetime.fromisoformat(a.since)
    except ValueError:
        sys.exit(f"Bad --since: {a.since}")
    if since.tzinfo is None:
        since = since.replace(tzinfo=dt.timezone.utc)

    if a.list:
        cmd_list(since)
    elif a.analyze:
        if not a.projects:
            sys.exit("--analyze needs --projects")
        cmd_analyze(since, a.projects)
    else:
        sys.exit("Pass --list or --analyze")


if __name__ == "__main__":
    main()
