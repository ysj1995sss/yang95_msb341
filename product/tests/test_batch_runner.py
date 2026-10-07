"""Spec 014: the shared batch runner — order, failures, stop, limits, restarts and continuing."""

import json
import threading

import pytest

from resume_tailorer import batch_runner as br


def _items(*ids, empty=()):
    return [br.new_item(i, f"Role {i}", "Acme Retail", "" if i in empty else "A real description.") for i in ids]


def _hooks(fail=(), done=None, limit_after=None, clock=None):
    done = done if done is not None else []
    steps = []

    def tailor_one(job_id):
        if job_id in fail:
            raise RuntimeError("model timed out")
        done.append(job_id)

    def use_limit():
        if limit_after is not None and len(done) + len([f for f in fail if f in steps_jobs]) >= limit_after:
            raise br.LimitReached("You've reached the limit of 2 tailoring runs today.")

    steps_jobs = []

    def on_step(step, job_id):
        steps.append(step)
        steps_jobs.append(job_id)

    hooks = br.Hooks(tailor_one=tailor_one, use_limit=use_limit, on_step=on_step)
    if clock:
        hooks.clock = clock
    return hooks, done, steps


def test_runs_each_job_in_order_and_records_options(tmp_path):
    hooks, done, steps = _hooks()
    br.start(tmp_path, _items("a", "b", "c", empty={"c"}), {"length": "1_page", "api_key": "secret"}, hooks,
             background=False)
    data = br.read_batch(tmp_path)
    assert done == ["a", "b"] and steps == ["Tailoring Role a (1 of 3)", "Tailoring Role b (2 of 3)"]
    assert data["status"] == "done" and [i["status"] for i in data["items"]] == ["done", "done", "skipped"]
    assert data["options"] == {"model": None, "length": "1_page", "conservative": False}  # never the key
    view = br.view(data)
    assert view["summary"] == "2 of 3 tailored · 1 skipped" and view["resumable_count"] == 0
    assert "heartbeat" not in view and "process" not in view


def test_a_failure_does_not_stop_the_rest_and_can_be_continued(tmp_path):
    hooks, done, _ = _hooks(fail={"b"})
    br.start(tmp_path, _items("a", "b", "c"), {}, hooks, background=False)
    data = br.read_batch(tmp_path)
    assert [i["status"] for i in data["items"]] == ["done", "failed", "done"]
    assert br.view(data)["resumable_count"] == 1

    hooks2, done2, _ = _hooks()
    br.continue_batch(tmp_path, hooks2, background=False)
    assert done2 == ["b"]  # only the job that didn't finish
    assert [i["status"] for i in br.read_batch(tmp_path)["items"]] == ["done", "done", "done"]
    with pytest.raises(LookupError):
        br.continue_batch(tmp_path, hooks2, background=False)


def test_the_daily_limit_skips_the_rest_and_they_can_continue_later(tmp_path):
    hooks, done, _ = _hooks(limit_after=1)
    br.start(tmp_path, _items("a", "b", "c"), {}, hooks, background=False)
    items = br.read_batch(tmp_path)["items"]
    assert [i["status"] for i in items] == ["done", "skipped", "skipped"]
    assert "limit of 2 tailoring runs" in items[1]["error"] and items[1]["resumable"]


def test_stop_after_the_current_job(tmp_path):
    release = threading.Event()
    started = threading.Event()
    done = []

    def tailor_one(job_id):
        started.set()
        release.wait(5)
        done.append(job_id)

    hooks = br.Hooks(tailor_one=tailor_one)
    br.start(tmp_path, _items("a", "b"), {}, hooks)
    assert started.wait(5)
    br.cancel(tmp_path)
    release.set()
    for _ in range(200):
        data = br.read_batch(tmp_path)
        if data["items"][0]["status"] == "done":
            break
        threading.Event().wait(0.02)
    assert done == ["a"] and data["status"] == "cancelled"
    assert data["items"][1]["status"] == "skipped" and data["items"][1]["error"] == br.CANCELLED
    assert br.view(data)["resumable_count"] == 1


def test_one_batch_at_a_time(tmp_path):
    release = threading.Event()
    hooks = br.Hooks(tailor_one=lambda job_id: release.wait(5))
    br.start(tmp_path, _items("a"), {}, hooks)
    with pytest.raises(br.BatchBusy):
        br.start(tmp_path, _items("b"), {}, hooks)
    with pytest.raises(br.BatchBusy):
        br.continue_batch(tmp_path, hooks)
    release.set()


def test_a_batch_whose_heartbeat_stopped_is_marked_stopped_and_saved(tmp_path):
    data = {"id": "x1", "status": "running", "heartbeat": 1000.0, "process": "other", "created": 900.0, "note": "",
            "options": {"length": "2_page"},
            "items": [{"job_id": "a", "title": "A", "company": "C", "status": "done", "error": "", "resumable": False},
                      {"job_id": "b", "title": "B", "company": "C", "status": "running", "error": "", "resumable": False},
                      {"job_id": "c", "title": "C", "company": "C", "status": "queued", "error": "", "resumable": False}]}
    br.write_batch(tmp_path, data)
    assert br.read_batch(tmp_path, now=1000.0 + br.STALE_SECONDS - 1)["status"] == "running"  # still alive
    stopped = br.read_batch(tmp_path, now=1000.0 + br.STALE_SECONDS + 1)
    assert stopped["status"] == "stopped" and stopped["note"] == br.STOPPED_NOTE
    assert [i["status"] for i in stopped["items"]] == ["done", "not_started", "not_started"]
    saved = json.loads((tmp_path / "tailor" / "batch.json").read_text(encoding="utf-8"))
    assert saved["status"] == "stopped"  # written back, so it sticks

    hooks, done, _ = _hooks()
    br.continue_batch(tmp_path, hooks, background=False)
    assert done == ["b", "c"]
    assert br.read_batch(tmp_path)["options"]["length"] == "2_page"


def test_a_batch_file_from_before_spec_014(tmp_path):
    legacy = {"id": "old", "status": "running", "boot": "some-other-process", "created": 1.0, "note": "",
              "items": [{"job_id": "a", "title": "A", "company": "C", "status": "done", "error": ""},
                        {"job_id": "b", "title": "B", "company": "C", "status": "queued", "error": ""},
                        {"job_id": "c", "title": "C", "company": "C", "status": "skipped", "error": br.CANCELLED},
                        {"job_id": "d", "title": "D", "company": "C", "status": "skipped",
                         "error": "This posting has no description to tailor against."}]}
    br.write_batch(tmp_path, legacy)
    data = br.read_batch(tmp_path)
    assert data["status"] == "stopped"
    view = br.view(data)
    assert view["resumable_count"] == 2 and view["options"] == br.DEFAULT_OPTIONS
    hooks, done, _ = _hooks()
    br.continue_batch(tmp_path, hooks, background=False)
    assert done == ["b", "c"]


def test_the_heartbeat_keeps_a_long_job_alive(tmp_path, monkeypatch):
    monkeypatch.setattr(br, "HEARTBEAT_SECONDS", 0.02)
    beats = []
    release = threading.Event()

    def tailor_one(job_id):
        for _ in range(100):
            try:
                beats.append(json.loads((tmp_path / "tailor" / "batch.json").read_text(encoding="utf-8"))["heartbeat"])
            except (OSError, ValueError):
                pass
            if len(set(beats)) > 2:
                break
            threading.Event().wait(0.02)
        release.set()

    br.start(tmp_path, _items("a"), {}, br.Hooks(tailor_one=tailor_one))
    assert release.wait(5)
    assert len(set(beats)) > 2  # the ticker moved the heartbeat while the job ran


def test_a_batch_from_an_exited_process_on_this_computer_is_stopped_at_once(tmp_path):
    import os
    import socket
    import subprocess
    import sys
    import time

    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    batch = {"id": "r1", "status": "running", "heartbeat": time.time(), "process": "old", "created": 1.0, "note": "",
             "host": socket.gethostname(), "pid": gone.pid,
             "items": [{"job_id": "a", "title": "A", "company": "C", "status": "running", "error": "", "resumable": False}]}
    br.write_batch(tmp_path, batch)
    assert br.read_batch(tmp_path)["status"] == "stopped"  # heartbeat is fresh, but its process is gone

    alive = dict(batch, id="r2", pid=os.getpid(), status="running")
    br.write_batch(tmp_path, alive)
    assert br.read_batch(tmp_path)["status"] == "running"  # this very process: rely on the heartbeat
    other_host = dict(batch, id="r3", host="another-computer", status="running")
    br.write_batch(tmp_path, other_host)
    assert br.read_batch(tmp_path)["status"] == "running"  # another computer: rely on the heartbeat
    assert br._pid_alive(os.getpid()) and not br._pid_alive(gone.pid)


def test_tailor_again_redoes_one_job_and_keeps_the_batch(tmp_path):
    hooks, done, _ = _hooks()
    br.start(tmp_path, _items("a", "b", "c"), {"length": "2_page"}, hooks, background=False)
    hooks2, done2, _ = _hooks()
    assert br.redo(tmp_path, "b", hooks2, background=False) is not None
    data = br.read_batch(tmp_path)
    assert done2 == ["b"] and [i["job_id"] for i in data["items"]] == ["a", "b", "c"]
    assert all(i["status"] == "done" for i in data["items"]) and data["options"]["length"] == "2_page"
    assert br.redo(tmp_path, "zzz", hooks2, background=False) is None  # not in the batch
