"""Batches in the Streamlit app (specs 011 and 014): tailor several jobs from Jobs in the
background, follow their progress, continue a batch that stopped, tailor an out-of-date job
again, open any of them in Tailor, and prepare the reviewed ones from Apply.

The work is resume_tailorer.batch_runner, shared with the web app, and the batch lives in the
person's `tailor/batch.json`, so it survives leaving the page, a new session and the other app.
Nothing is ever submitted."""

from __future__ import annotations

import streamlit as st

from resume_tailorer.batch import MAX_BATCH, handoff_for_saved_review, item_freshness, prepare_jobs, review_ready

BATCH_KEY = "batch_job_ids"  # spec 011's session list; read only as a fallback for older sessions
_ITEM_WORDS = {"queued": "Waiting", "running": "Tailoring now", "done": "Tailored", "failed": "Failed",
               "skipped": "Skipped", "not_started": "Not started"}


def _owner() -> str:
    from resume_tailorer.ui.auth_gate import OWNER_KEY

    return st.session_state[OWNER_KEY]


def _artifacts() -> str:
    from resume_tailorer.identity import artifacts_dir

    return st.session_state.get("artifacts_dir") or artifacts_dir(_owner())


def _user_dir():
    from resume_tailorer.identity import user_dir

    return user_dir(_owner())


def _hooks(options: dict):
    """Tailor one job in the background thread: no st.session_state there, so the person's
    record, profile and stored job are read fresh from their folder for each job."""
    from resume_tailorer.batch import tailor_job
    from resume_tailorer.batch_runner import Hooks
    from resume_tailorer.identity import applications_db_path, artifacts_dir, job_db_path
    from resume_tailorer.job_search.job_service import JobService
    from resume_tailorer.llm.client import LLMClient
    from resume_tailorer.llm.settings import resolve_settings
    from resume_tailorer.profile_import import RECORD_KEY, load_into_session, store_for
    from resume_tailorer.session_profile import get_career_profile

    owner = _owner()
    settings = resolve_settings(model=options.get("model"))  # raises ValueError when no model is set up

    def tailor_one(job_id: str) -> None:
        session: dict = {}
        load_into_session(session, owner, force=True)
        record = session.get(RECORD_KEY) or {}
        meta = record.get("resume")
        data = store_for(owner).resume_bytes(meta) if meta else None
        profile = get_career_profile(session)
        if not data or profile is None:
            raise LookupError("Import your resume in Career Profile first.")
        service = JobService(db_path=job_db_path(owner), applications_db_path=applications_db_path(owner))
        try:
            job = service.db.get_job_posting(job_id)
            if job is None:
                raise LookupError("That job is no longer stored.")
            tailor_job(job, artifacts_dir=artifacts_dir(owner), original_bytes=data, filename=meta["filename"],
                       llm=LLMClient(settings), fit_scorer=service.fit_scorer, career_profile=profile,
                       provenance=record.get("provenance"), target_length=options.get("length") or "preserve",
                       conservative=bool(options.get("conservative")))
        finally:
            service.close()

    return Hooks(tailor_one=tailor_one)


def _run(action) -> None:
    """Start, continue or redo a batch; show why not when it can't."""
    from resume_tailorer.batch_runner import BatchBusy

    try:
        action()
    except ValueError as exc:
        st.error(f"The writing model isn't set up: {exc}")
    except (BatchBusy, LookupError) as exc:
        st.error(str(exc))


def render_batch_runner(jobs: list, job_id_for, service, owner_id: str) -> None:
    """Jobs: choose up to 10 jobs and tailor them in the background; the progress follows below."""
    from resume_tailorer import batch_runner

    with st.expander("Tailor several jobs at once"):
        labels = {job_id_for(j): f"{j.title} at {j.company}" for j in jobs if (j.description or "").strip()}
        chosen = st.multiselect("Jobs to tailor", list(labels), format_func=labels.get, max_selections=MAX_BATCH,
                                key="batch_pick", help="They're tailored one at a time in the background. You can "
                                                       "keep using the app; review each one in Tailor.")
        if st.button(f"Tailor selected ({len(chosen)})", type="primary", disabled=not chosen, key="batch_go"):
            by_id = {job_id_for(j): j for j in jobs}
            items = [batch_runner.new_item(i, by_id[i].title, by_id[i].company, by_id[i].description or "")
                     for i in chosen]
            options = dict(batch_runner.DEFAULT_OPTIONS)
            _run(lambda: batch_runner.start(_user_dir(), items, options, _hooks(options)))
        render_batch_progress()


@st.fragment(run_every=2)
def _progress_fragment() -> None:
    _render_batch(in_fragment=True)


def render_batch_progress() -> None:
    """The person's batch, refreshing itself every 2 seconds while it runs (only this part reruns)."""
    from resume_tailorer.batch_runner import read_batch

    data = read_batch(_user_dir())
    if data and data.get("status") == "running":
        _progress_fragment()
    else:
        _render_batch(in_fragment=False)


def _render_batch(in_fragment: bool) -> None:
    from resume_tailorer import batch_runner
    from resume_tailorer.session_profile import get_career_profile

    shown = batch_runner.view(batch_runner.read_batch(_user_dir()))
    if not shown:
        return
    if in_fragment and shown["status"] != "running":
        st.rerun()  # finished: redraw the page once, so the fragment stops refreshing
    profile = get_career_profile(st.session_state)
    with st.container(border=True):
        st.markdown(f"**Batch** · {shown['summary']}")
        if shown.get("note"):
            st.warning(shown["note"])
        for item in shown["items"]:
            fresh = item_freshness(_artifacts(), item, profile)
            line = f"- **{item['title']}** at {item['company']}: {_ITEM_WORDS.get(item['status'], item['status'])}"
            if item.get("error"):
                line += f". {item['error']}"
            st.markdown(line)
            if fresh["stale"]:
                left, right = st.columns([4, 1])
                left.caption(fresh["stale_message"])
                if shown["status"] != "running" and right.button("Tailor again", key=f"batch_again_{item['job_id']}"):
                    options = shown["options"]
                    again = [{"job_id": item["job_id"], "title": item["title"], "company": item["company"],
                              "status": "queued", "error": "", "resumable": False}]
                    _run(lambda: batch_runner.start(_user_dir(), again, options, _hooks(options)))
                    st.rerun()
        if shown["status"] == "running":
            if st.button("Stop after the current job", key="batch_stop"):
                batch_runner.cancel(_user_dir())
                st.rerun()
        elif shown["resumable_count"]:
            if st.button(f"Continue batch ({shown['resumable_count']} left)", type="primary", key="batch_continue"):
                _run(lambda: batch_runner.continue_batch(_user_dir(), _hooks(shown["options"])))
                st.rerun()


def _batch_job_ids() -> list[str]:
    """Tailored jobs in the person's batch (from batch.json), else spec 011's session list."""
    from resume_tailorer.batch_runner import read_batch

    data = read_batch(_user_dir())
    if data:
        return [i["job_id"] for i in data["items"] if i["status"] == "done"]
    return list(st.session_state.get(BATCH_KEY) or [])


def render_batch_switcher(service) -> None:
    """Tailor: the batch's progress, and open any tailored batch job's saved review."""
    from resume_tailorer.active_job import remember, remember_handoff
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.profile_import import RECORD_KEY, save_record
    from resume_tailorer.review_store import load_review

    render_batch_progress()
    ids = _batch_job_ids()
    if not ids:
        return
    labels = {}
    for job_id in ids:
        job = service.db.get_job_posting(job_id)
        ready, _ = review_ready(load_review(_artifacts(), job_id))
        labels[job_id] = f"{job.title} at {job.company}" + (" · reviewed" if ready else "") if job else job_id
    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="bottom")
        choice = left.selectbox("Batch: open a job's review", ids, format_func=labels.get, key="batch_open_pick")
        if right.button("Open review", key="batch_open_go", use_container_width=True):
            record = st.session_state.get(RECORD_KEY) or {}
            remember(record, choice)
            handoff = handoff_for_saved_review(st.session_state, _artifacts(), choice)
            ready, _ = review_ready(load_review(_artifacts(), choice))
            remember_handoff(record, handoff, ready)
            save_record(st.session_state, _owner(), record)
            st.session_state.pop(PENDING_TAILOR_JOB_KEY, None)  # rebuilt from the record on the rerun
            st.rerun()


def render_batch_prepare(service) -> None:
    """Apply: track every reviewed, passing, up-to-date batch job as "Ready to apply". Never submits."""
    from resume_tailorer.session_profile import get_career_profile

    ids = _batch_job_ids()
    if not ids:
        return
    with st.container(border=True):
        st.markdown("**Your batch**")
        st.caption("Prepare every batch job whose review you finished and whose resume passed its checks. Each is "
                   "tracked as ready to apply; you still apply on each employer's own site. Nothing is submitted.")
        if st.button("Prepare reviewed jobs for applying", type="primary", key="batch_prepare"):
            words = {"tracked": "Ready to apply", "already_tracked": "Already tracked", "review_first": "Review first",
                     "tailor_again": "Tailor again first", "not_found": "Not found"}
            for r in prepare_jobs(ids, service=service, profile=get_career_profile(st.session_state),
                                  artifacts_dir=_artifacts()):
                link = f" · [employer's application]({r.url})" if r.status == "tracked" and r.url else ""
                st.markdown(f"- **{r.title}** at {r.company}: {words[r.status]}. {r.message}{link}")
