"""Batches in the Streamlit app (spec 011): tailor several jobs from Jobs, open any of them in
Tailor, and prepare the reviewed ones from Apply. The work itself is resume_tailorer.batch, shared
with the web app. Here a batch runs in the page (one job after another, with progress shown);
nothing is ever submitted."""

from __future__ import annotations

import streamlit as st

from resume_tailorer.batch import MAX_BATCH, handoff_for_saved_review, prepare_jobs, review_ready, tailor_job

BATCH_KEY = "batch_job_ids"


def render_batch_runner(jobs: list, job_id_for, service, owner_id: str) -> None:
    """Jobs: choose up to 10 jobs from this list and tailor them one after another."""
    from resume_tailorer.llm.client import LLMClient
    from resume_tailorer.llm.settings import resolve_settings
    from resume_tailorer.profile_import import RECORD_KEY, store_for
    from resume_tailorer.session_profile import get_career_profile

    with st.expander("Tailor several jobs at once"):
        labels = {job_id_for(j): f"{j.title} at {j.company}" for j in jobs if (j.description or "").strip()}
        chosen = st.multiselect("Jobs to tailor", list(labels), format_func=labels.get, max_selections=MAX_BATCH,
                                key="batch_pick", help="They're tailored one at a time. You review each one in Tailor.")
        if not st.button(f"Tailor selected ({len(chosen)})", type="primary", disabled=not chosen, key="batch_go"):
            return
        record = st.session_state.get(RECORD_KEY) or {}
        meta = record.get("resume")
        data = store_for(owner_id).resume_bytes(meta) if meta else None
        profile = get_career_profile(st.session_state)
        if not data or profile is None:
            st.error("Import your resume in Career Profile first.")
            return
        try:
            llm = LLMClient(resolve_settings())
        except ValueError as exc:
            st.error(f"The writing model isn't set up: {exc}")
            return
        done = []
        by_id = {job_id_for(j): j for j in jobs}
        with st.status(f"Tailoring {len(chosen)} jobs…", expanded=True) as status:
            for n, job_id in enumerate(chosen, start=1):
                st.write(f"{n} of {len(chosen)}: {labels[job_id]}")
                try:
                    tailor_job(by_id[job_id], artifacts_dir=st.session_state["artifacts_dir"], original_bytes=data,
                               filename=meta["filename"], llm=llm, fit_scorer=service.fit_scorer,
                               career_profile=profile, provenance=record.get("provenance"))
                    done.append(job_id)
                except Exception as exc:  # one job failing never stops the rest
                    st.write(f"Didn't finish: {exc}")
            status.update(label=f"{len(done)} of {len(chosen)} tailored. Review each one in Tailor.", state="complete")
        st.session_state[BATCH_KEY] = done


def render_batch_switcher(service) -> None:
    """Tailor: open any tailored batch job's saved review."""
    from resume_tailorer.active_job import remember, remember_handoff
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.profile_import import RECORD_KEY, save_record
    from resume_tailorer.ui.auth_gate import OWNER_KEY
    from resume_tailorer.review_store import load_review

    ids = st.session_state.get(BATCH_KEY) or []
    if not ids:
        return
    labels = {}
    for job_id in ids:
        job = service.db.get_job_posting(job_id)
        ready, _ = review_ready(load_review(st.session_state["artifacts_dir"], job_id))
        labels[job_id] = f"{job.title} at {job.company}" + (" · reviewed" if ready else "") if job else job_id
    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="bottom")
        choice = left.selectbox("Batch: open a job's review", ids, format_func=labels.get, key="batch_open_pick")
        if right.button("Open review", key="batch_open_go", use_container_width=True):
            record = st.session_state.get(RECORD_KEY) or {}
            remember(record, choice)
            handoff = handoff_for_saved_review(st.session_state, st.session_state["artifacts_dir"], choice)
            ready, _ = review_ready(load_review(st.session_state["artifacts_dir"], choice))
            remember_handoff(record, handoff, ready)
            save_record(st.session_state, st.session_state[OWNER_KEY], record)
            st.session_state.pop(PENDING_TAILOR_JOB_KEY, None)  # rebuilt from the record on the rerun
            st.rerun()


def render_batch_prepare(service) -> None:
    """Apply: track every reviewed, passing batch job as "Ready to apply". Never submits."""
    from resume_tailorer.session_profile import get_career_profile

    ids = st.session_state.get(BATCH_KEY) or []
    if not ids:
        return
    with st.container(border=True):
        st.markdown("**Your batch**")
        st.caption("Prepare every batch job whose review you finished and whose resume passed its checks. Each is "
                   "tracked as ready to apply; you still apply on each employer's own site. Nothing is submitted.")
        if st.button("Prepare reviewed jobs for applying", type="primary", key="batch_prepare"):
            words = {"tracked": "Ready to apply", "already_tracked": "Already tracked", "review_first": "Review first",
                     "not_found": "Not found"}
            for r in prepare_jobs(ids, service=service, profile=get_career_profile(st.session_state),
                                  artifacts_dir=st.session_state["artifacts_dir"]):
                link = f" · [employer's application]({r.url})" if r.status == "tracked" and r.url else ""
                st.markdown(f"- **{r.title}** at {r.company}: {words[r.status]}. {r.message}{link}")
