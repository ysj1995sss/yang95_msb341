"""The batch runner both apps use (spec 014): tailor several jobs one at a time in a background
thread, with the state kept in `users/<owner>/tailor/batch.json` so it survives restarts and is
shared by the web app and the Streamlit app. Nothing is ever submitted (decision 016).

- A running batch records its process (computer and process id) and writes a heartbeat every
  30 s. It was stopped (a restart or a crash) when that process has exited on this computer, or
  when its heartbeat is older than 3 minutes (another computer). It's then marked "stopped" in
  the file, and the jobs it didn't finish can be continued with the same options.
- One batch at a time per person, across processes: starting or continuing checks the file
  under a short lock file.
- App-specific pieces come in as hooks: how to tailor one job, the daily limit, and progress.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional

MAX_BATCH = 10
PROCESS_ID = uuid.uuid4().hex  # this process; the API's run status uses the same id
HEARTBEAT_SECONDS = 30
STALE_SECONDS = 180
CANCELLED = "Cancelled before it started."
STOPPED_NOTE = "This batch stopped before it finished (the app restarted). Continue it to tailor the rest."
DEFAULT_OPTIONS = {"model": None, "length": "preserve", "conservative": False}

logger = logging.getLogger("job_copilot.batch")
_LOCK = threading.RLock()


class LimitReached(Exception):
    """The daily tailoring limit stopped the batch; the message says when it resets."""


class BatchBusy(Exception):
    """A batch is already running for this person."""


@dataclass
class Hooks:
    tailor_one: Callable[[str], None]  # tailor and save one job's review; raises on failure
    use_limit: Callable[[], None] = lambda: None  # raises LimitReached
    on_step: Callable[[str, Optional[str]], None] = lambda step, job_id: None
    on_finish: Callable[[], None] = lambda: None
    clock: Callable[[], float] = field(default=time.time)


# --- the state file -------------------------------------------------------------------------

def _path(user_dir: Path) -> Path:
    path = Path(user_dir) / "tailor" / "batch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _file_lock(user_dir: Path, wait: float = 5.0) -> Iterator[None]:
    """A short cross-process lock around read-check-write of the batch file."""
    lock = _path(user_dir).with_suffix(".lock")
    deadline = time.monotonic() + wait
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 30:  # left behind by a crash
                    lock.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise BatchBusy("Another batch change is in progress. Try again in a moment.")
            time.sleep(0.05)
    try:
        with _LOCK:
            yield
    finally:
        lock.unlink(missing_ok=True)


def write_batch(user_dir: Path, data: dict) -> None:
    path = _path(user_dir)
    tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: someone is reading the file this instant
            if attempt == 19:
                raise
            time.sleep(0.01)


def _pid_alive(pid: int) -> bool:
    """Is a process with this id running on this computer? (Never signals or stops it.)"""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # signal 0 only checks; on POSIX it never stops anything
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _is_stale(data: dict, now: float) -> bool:
    if data.get("status") != "running":
        return False
    # Run by another process on this computer that has exited (a restart): stopped right away.
    pid = data.get("pid")
    if data.get("host") == socket.gethostname() and isinstance(pid, int) and pid != os.getpid()             and not _pid_alive(pid):
        return True
    beat = data.get("heartbeat")
    if beat is None:  # written before spec 014: only the process id says who runs it
        return data.get("boot") != PROCESS_ID
    return now - float(beat) > STALE_SECONDS


def read_batch(user_dir: Path, now: Optional[float] = None) -> Optional[dict]:
    """The person's last batch; a running batch whose heartbeat stopped is marked stopped (and saved)."""
    try:
        data = json.loads(_path(user_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    if _is_stale(data, time.time() if now is None else now):
        data["status"] = "stopped"
        data["note"] = STOPPED_NOTE
        for item in data["items"]:
            if item.get("status") in ("queued", "running"):
                item["status"] = "not_started"
                item["resumable"] = True
        with _LOCK:
            write_batch(user_dir, data)
    return data


def is_resumable(item: dict) -> bool:
    if "resumable" in item:
        return bool(item["resumable"]) and item.get("status") in ("not_started", "failed", "skipped")
    # Items written before spec 014.
    return item.get("status") in ("not_started", "failed") or (
        item.get("status") == "skipped" and item.get("error") == CANCELLED)


def view(data: Optional[dict]) -> Optional[dict]:
    """The batch as shown: a summary line and how many jobs can be continued."""
    if not data:
        return None
    shown = {k: v for k, v in data.items() if k not in ("boot", "heartbeat", "process", "host", "pid")}
    items = shown["items"]
    counts = {s: sum(1 for i in items if i["status"] == s) for s in ("done", "failed", "skipped")}
    shown["summary"] = (f"{counts['done']} of {len(items)} tailored"
                        + (f" · {counts['failed']} failed" if counts["failed"] else "")
                        + (f" · {counts['skipped']} skipped" if counts["skipped"] else ""))
    shown["resumable_count"] = 0 if shown.get("status") == "running" else sum(1 for i in items if is_resumable(i))
    shown.setdefault("options", dict(DEFAULT_OPTIONS))
    return shown


def new_item(job_id: str, title: str, company: str, description: str) -> dict:
    usable = bool((description or "").strip())
    return {"job_id": job_id, "title": title, "company": company, "status": "queued" if usable else "skipped",
            "error": "" if usable else "This posting has no description to tailor against.", "resumable": False}


# --- running --------------------------------------------------------------------------------

def _claim(user_dir: Path, data: dict, now: float) -> None:
    current = read_batch(user_dir, now)
    if current and current.get("status") == "running":
        raise BatchBusy("A batch is already running. Wait for it to finish or stop it.")
    data.update(status="running", process=PROCESS_ID, boot=PROCESS_ID, heartbeat=now,
                host=socket.gethostname(), pid=os.getpid())
    write_batch(user_dir, data)


def start(user_dir: Path, items: list[dict], options: dict, hooks: Hooks, *, background: bool = True) -> dict:
    """Start a new batch (replacing the last one). Raises BatchBusy if one is running."""
    now = hooks.clock()
    data = {"id": uuid.uuid4().hex[:8], "created": now, "items": items, "note": "",
            "options": {**DEFAULT_OPTIONS, **{k: options.get(k) for k in DEFAULT_OPTIONS if k in options}}}
    with _file_lock(user_dir):
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], hooks, background)
    return data


def continue_batch(user_dir: Path, hooks: Hooks, *, background: bool = True) -> dict:
    """Re-queue the jobs that didn't finish and run them with the batch's own options."""
    now = hooks.clock()
    with _file_lock(user_dir):
        data = read_batch(user_dir, now)
        if not data:
            raise LookupError("There's no batch to continue.")
        if data.get("status") == "running":
            raise BatchBusy("This batch is still running.")
        again = [i for i in data["items"] if is_resumable(i)]
        if not again:
            raise LookupError("Every job in this batch already finished.")
        for item in again:
            item.update(status="queued", error="", resumable=False)
        data["note"] = ""
        data.setdefault("options", dict(DEFAULT_OPTIONS))
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], hooks, background)
    return data


def redo(user_dir: Path, job_id: str, hooks: Hooks, *, background: bool = True) -> Optional[dict]:
    """Tailor one job of the batch again (its profile changed), keeping the rest of the batch as
    it is. None when the job isn't in the batch (the caller starts a one-job batch instead)."""
    now = hooks.clock()
    with _file_lock(user_dir):
        data = read_batch(user_dir, now)
        if not data or not any(i["job_id"] == job_id for i in data["items"]):
            return None
        if data.get("status") == "running":
            raise BatchBusy("This batch is still running.")
        for item in data["items"]:
            if item["job_id"] == job_id:
                item.update(status="queued", error="", resumable=False)
        data["note"] = ""
        data.setdefault("options", dict(DEFAULT_OPTIONS))
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], hooks, background)
    return data


def cancel(user_dir: Path) -> Optional[dict]:
    """Stop after the job that's running now; jobs not started can be continued later."""
    with _file_lock(user_dir):
        data = read_batch(user_dir)
        if data and data.get("status") == "running":
            data["status"] = "cancelled"
            for item in data["items"]:
                if item["status"] == "queued":
                    item.update(status="skipped", error=CANCELLED, resumable=True)
            write_batch(user_dir, data)
    return data


def _launch(user_dir: Path, batch_id: str, hooks: Hooks, background: bool) -> None:
    if background:
        threading.Thread(target=run, args=(user_dir, batch_id, hooks),
                         name=f"batch-{batch_id}", daemon=True).start()
    else:
        run(user_dir, batch_id, hooks)


def _update(user_dir: Path, batch_id: str, change: Callable[[dict], None]) -> Optional[dict]:
    with _file_lock(user_dir, wait=30.0):
        data = read_batch(user_dir)
        if not data or data.get("id") != batch_id:
            return None
        change(data)
        write_batch(user_dir, data)
        return data


def run(user_dir: Path, batch_id: str, hooks: Hooks) -> None:
    """Tailor each queued job in order. One job failing never stops the rest."""
    stop = threading.Event()

    def beat() -> None:
        while not stop.wait(HEARTBEAT_SECONDS):
            _update(user_dir, batch_id, lambda d: d.update(heartbeat=hooks.clock()) if d.get("status") == "running" else None)

    threading.Thread(target=beat, name=f"batch-beat-{batch_id}", daemon=True).start()
    try:
        while True:
            picked: dict = {}

            def pick(data: dict) -> None:
                if data.get("status") != "running":
                    return
                total = len(data["items"])
                for n, item in enumerate(data["items"]):
                    if item["status"] == "queued":
                        try:
                            hooks.use_limit()
                        except LimitReached as exc:
                            for later in data["items"][n:]:
                                if later["status"] == "queued":
                                    later.update(status="skipped", error=str(exc), resumable=True)
                            return
                        item["status"] = "running"
                        data["heartbeat"] = hooks.clock()
                        picked.update(item=dict(item), index=n, total=total)
                        return

            if _update(user_dir, batch_id, pick) is None or not picked:
                return
            item = picked["item"]
            hooks.on_step(f"Tailoring {item['title']} ({picked['index'] + 1} of {picked['total']})", item["job_id"])
            outcome = {"status": "done", "error": "", "resumable": False}
            try:
                hooks.tailor_one(item["job_id"])
            except Exception as exc:  # one job failing never stops the rest
                logger.exception("Batch job %s failed", item["job_id"])
                outcome = {"status": "failed", "error": f"Tailoring didn't finish: {exc}", "resumable": True}
            _update(user_dir, batch_id, lambda d, n=picked["index"]: d["items"][n].update(outcome))
    finally:
        stop.set()
        _update(user_dir, batch_id, lambda d: d.update(status="done") if d.get("status") == "running" else None)
        try:
            hooks.on_finish()
        except Exception:  # progress reporting never breaks a batch
            logger.exception("Batch finish hook failed")
