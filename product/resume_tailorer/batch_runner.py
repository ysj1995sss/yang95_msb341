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

from resume_tailorer.utils.files import read_text_retrying

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
    tailor_one: Callable[[str], object]  # legacy harmless hooks; real apps use tailor_claim
    use_limit: Callable[[], None] = lambda: None  # raises LimitReached
    on_step: Callable[[str, Optional[str]], None] = lambda step, job_id: None
    on_finish: Callable[[], None] = lambda: None
    clock: Callable[[], float] = field(default=time.time)
    tailor_claim: Optional[Callable[[ExecutionClaim], object]] = None
    publish_result: Callable[[str, object], None] = lambda job_id, result: None
    on_claim_step: Optional[Callable[[ExecutionClaim, str], None]] = None
    on_claim_finish: Optional[Callable[[ExecutionClaim], None]] = None


@dataclass(frozen=True)
class ExecutionClaim:
    user_dir: Path
    batch_id: str
    execution: str
    job_id: Optional[str] = None


def owns_running_item(data, batch_id, execution, job_id) -> bool:
    return bool(data and data.get('id') == batch_id and data.get('execution') == execution
                and _is_active(data) and any(i['job_id'] == job_id and i['status'] == 'running' for i in data['items']))


def when_current(claim: ExecutionClaim, action: Callable[[], None]) -> bool:
    with _file_lock(claim.user_dir):
        data = _read_batch_locked(claim.user_dir)
        if not data or data.get('id') != claim.batch_id or data.get('execution') != claim.execution:
            return False
        if claim.job_id is not None and not owns_running_item(data, claim.batch_id, claim.execution, claim.job_id):
            return False
        action()
        return True


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
    # OS locks release on process exit. Never steal/unlink a live publisher's lock on age,
    # and never race two crash-recovery unlinkers against a newly acquired lock.
    fd = os.open(lock, os.O_CREAT | os.O_RDWR)
    if os.fstat(fd).st_size == 0:
        os.write(fd, b'0')
    def acquire():
        os.lseek(fd, 0, os.SEEK_SET)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    acquired = False
    try:
        while not acquired:
            try:
                acquire()
                acquired = True
            except OSError:
                if time.monotonic() > deadline:
                    raise BatchBusy("Another batch change is in progress. Try again in a moment.")
                time.sleep(0.05)
        with _LOCK:
            yield
    finally:
        if acquired:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


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


def _is_active(data: dict) -> bool:
    """A stopped batch still owns its current job until that job returns."""
    return data.get("status") == "running" or (
        data.get("status") == "cancelled" and any(i.get("status") == "running" for i in data["items"]))


def _is_stale(data: dict, now: float) -> bool:
    if not _is_active(data):
        return False
    # Run by another process on this computer that has exited (a restart): stopped right away.
    pid = data.get("pid")
    if data.get("host") == socket.gethostname() and isinstance(pid, int) and pid != os.getpid()             and not _pid_alive(pid):
        return True
    beat = data.get("heartbeat")
    if beat is None:  # written before spec 014: only the process id says who runs it
        return data.get("boot") != PROCESS_ID
    return now - float(beat) > STALE_SECONDS


def _read_batch_file(user_dir: Path) -> Optional[dict]:
    try:
        data = json.loads(read_text_retrying(_path(user_dir)))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    return data


def _read_batch_locked(user_dir: Path, now: Optional[float] = None) -> Optional[dict]:
    """Read/recover while the caller owns the cross-process change lock."""
    data = _read_batch_file(user_dir)
    if data is None:
        return None
    if _is_stale(data, time.time() if now is None else now):
        data["status"] = "stopped"
        data["note"] = STOPPED_NOTE
        for item in data["items"]:
            if item.get("status") in ("queued", "running"):
                item["status"] = "not_started"
                item["resumable"] = True
        write_batch(user_dir, data)
    return data


def read_batch(user_dir: Path, now: Optional[float] = None) -> Optional[dict]:
    """The person's last batch; recover disappeared workers under the same lock as a new claim."""
    data = _read_batch_file(user_dir)
    if data and _is_stale(data, time.time() if now is None else now):
        with _file_lock(user_dir):
            return _read_batch_locked(user_dir, now)  # another process may have continued it while we waited
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
    shown = {k: v for k, v in data.items() if k not in ("boot", "heartbeat", "process", "host", "pid", "execution")}
    if data.get("status") == "cancelled" and _is_active(data):
        shown["status"] = "running"  # both apps keep polling and hide Continue until the current job returns
        shown["note"] = "Stopping after the current job finishes."
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
    current = _read_batch_locked(user_dir, now)
    if current and _is_active(current):
        raise BatchBusy("A batch is already running. Wait for it to finish or stop it.")
    data.update(status="running", process=PROCESS_ID, boot=PROCESS_ID, heartbeat=now,
                host=socket.gethostname(), pid=os.getpid(), execution=uuid.uuid4().hex)
    write_batch(user_dir, data)


def start(user_dir: Path, items: list[dict], options: dict, hooks: Hooks, *, background: bool = True) -> dict:
    """Start a new batch (replacing the last one). Raises BatchBusy if one is running."""
    now = hooks.clock()
    data = {"id": uuid.uuid4().hex[:8], "created": now, "items": items, "note": "",
            "options": {**DEFAULT_OPTIONS, **{k: options.get(k) for k in DEFAULT_OPTIONS if k in options}}}
    with _file_lock(user_dir):
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], data["execution"], hooks, background)
    return data


def continue_batch(user_dir: Path, hooks: Hooks, *, background: bool = True) -> dict:
    """Re-queue the jobs that didn't finish and run them with the batch's own options."""
    now = hooks.clock()
    with _file_lock(user_dir):
        data = _read_batch_locked(user_dir, now)
        if not data:
            raise LookupError("There's no batch to continue.")
        if _is_active(data):
            raise BatchBusy("This batch is still running.")
        again = [i for i in data["items"] if is_resumable(i)]
        if not again:
            raise LookupError("Every job in this batch already finished.")
        for item in again:
            item.update(status="queued", error="", resumable=False)
        data["note"] = ""
        data.setdefault("options", dict(DEFAULT_OPTIONS))
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], data["execution"], hooks, background)
    return data


def redo(user_dir: Path, job_id: str, hooks: Hooks, *, background: bool = True) -> Optional[dict]:
    """Tailor one job of the batch again (its profile changed), keeping the rest of the batch as
    it is. None when the job isn't in the batch (the caller starts a one-job batch instead)."""
    now = hooks.clock()
    with _file_lock(user_dir):
        data = _read_batch_locked(user_dir, now)
        if not data or not any(i["job_id"] == job_id for i in data["items"]):
            return None
        if _is_active(data):
            raise BatchBusy("This batch is still running.")
        for item in data["items"]:
            if item["job_id"] == job_id:
                item.update(status="queued", error="", resumable=False)
        data["note"] = ""
        data.setdefault("options", dict(DEFAULT_OPTIONS))
        _claim(user_dir, data, now)
    _launch(user_dir, data["id"], data["execution"], hooks, background)
    return data


def cancel(user_dir: Path) -> Optional[dict]:
    """Stop after the job that's running now; jobs not started can be continued later."""
    with _file_lock(user_dir):
        data = _read_batch_locked(user_dir)
        if data and data.get("status") == "running":
            data["status"] = "cancelled"
            for item in data["items"]:
                if item["status"] == "queued":
                    item.update(status="skipped", error=CANCELLED, resumable=True)
            write_batch(user_dir, data)
    return data


def _launch(user_dir: Path, batch_id: str, execution: str, hooks: Hooks, background: bool) -> None:
    if background:
        threading.Thread(target=run, args=(user_dir, batch_id, hooks, execution),
                         name=f"batch-{batch_id}", daemon=True).start()
    else:
        run(user_dir, batch_id, hooks, execution)


def _update(user_dir: Path, batch_id: str, execution: str, change: Callable[[dict], None]) -> Optional[dict]:
    with _file_lock(user_dir, wait=30.0):
        data = _read_batch_locked(user_dir)
        if not data or data.get("id") != batch_id or data.get("execution") != execution:
            return None
        change(data)
        write_batch(user_dir, data)
        return data


def run(user_dir: Path, batch_id: str, hooks: Hooks, execution: str) -> None:
    """Tailor each queued job in order. One job failing never stops the rest."""
    stop = threading.Event()

    def beat() -> None:
        while not stop.wait(HEARTBEAT_SECONDS):
            _update(user_dir, batch_id, execution,
                    lambda d: d.update(heartbeat=hooks.clock()) if _is_active(d) else None)

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

            if _update(user_dir, batch_id, execution, pick) is None or not picked:
                return
            item = picked["item"]
            claim = ExecutionClaim(Path(user_dir), batch_id, execution, item['job_id'])
            step = f"Tailoring {item['title']} ({picked['index'] + 1} of {picked['total']})"
            hooks.on_step(step, item['job_id'])
            if hooks.on_claim_step:
                hooks.on_claim_step(claim, step)  # outside batch lock; API acquires its lock first
            outcome = {"status": "done", "error": "", "resumable": False}
            result = None
            try:
                result = hooks.tailor_claim(claim) if hooks.tailor_claim else hooks.tailor_one(item["job_id"])
            except Exception as exc:  # one job failing never stops the rest
                logger.exception("Batch job %s failed", item["job_id"])
                outcome = {"status": "failed", "error": f"Tailoring didn't finish: {exc}", "resumable": True}
            with _file_lock(user_dir, wait=30.0):
                data = _read_batch_locked(user_dir)
                if not owns_running_item(data, batch_id, execution, item['job_id']):
                    return
                if outcome['status'] == 'done':
                    try:
                        hooks.publish_result(item['job_id'], result)
                    except Exception as exc:
                        outcome = dict(status='failed', error=f'The review could not be saved: {exc}', resumable=True)
                data['items'][picked['index']].update(outcome)
                write_batch(user_dir, data)
    finally:
        stop.set()
        own = _update(user_dir, batch_id, execution,
                      lambda d: d.update(status="done") if d.get("status") == "running" else None)
        try:
            if own is not None:
                hooks.on_finish()
                if hooks.on_claim_finish:
                    hooks.on_claim_finish(ExecutionClaim(Path(user_dir), batch_id, execution))
        except Exception:  # progress reporting never breaks a batch
            logger.exception("Batch finish hook failed")
