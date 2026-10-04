"""Jobs: search real postings, triage them, and understand each match (spec 007).

Desktop is three regions: search and goals | result rows | the selected job's
evidence. On narrow screens Streamlit stacks them in that order.

Unchanged rules (decisions 010, 011, 020): real results only, honest source
labels, whole-word title matching, results scoped to the latest search run,
unknown salary/sponsorship/fit shown as unknown. "Prepare application" records
the APPLY triage and hands the job and its fit snapshot to Tailor.
"""

from html import escape

import streamlit as st

from resume_tailorer.job_search.dashboard import SORT_OPTIONS, filter_and_sort_jobs
from resume_tailorer.job_search.job_attributes import (
    EMPLOYMENT_TYPE_OPTIONS,
    EXPERIENCE_LEVEL_OPTIONS,
    INDUSTRY_OPTIONS,
)
from resume_tailorer.job_search.job_quality import evaluate_job_quality
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY, JobService, build_tailor_snapshot
from resume_tailorer.job_search.models import DashboardFilters, JobSource, TriageAction, UserSelection
from resume_tailorer.job_search.ui_helpers import build_search_goals_from_form
from resume_tailorer.profile_import import RECORD_KEY, save_record
from resume_tailorer.session_profile import get_career_profile
from resume_tailorer.ui import chip, progress_steps, render_app_shell, render_page_header, render_progress
from resume_tailorer.ui.auth_gate import OWNER_KEY, job_service_for, require_identity
from resume_tailorer.ui.job_view import build_detail, build_row, job_id_for
from resume_tailorer.ui.onboarding import WORK_MODE_LABELS, apply_goals_to_search_form, form_to_goals, save_goals

st.set_page_config(page_title="Jobs · Job Copilot", page_icon="\U0001F50D", layout="wide")

REMOTE_PREFERENCE_OPTIONS = ["any", "remote", "hybrid", "onsite"]
LIVE_SOURCES = [JobSource.GREENHOUSE, JobSource.LEVER, JobSource.ASHBY]
DEMO_SOURCES = [JobSource.LINKEDIN, JobSource.INDEED, JobSource.HANDSHAKE]
SOURCE_OPTIONS = LIVE_SOURCES + DEMO_SOURCES
SOURCE_LABELS = {
    JobSource.GREENHOUSE: "Greenhouse (live, 36 company boards)",
    JobSource.LEVER: "Lever (live, 8 company boards)",
    JobSource.ASHBY: "Ashby (live, 19 company boards)",
    JobSource.LINKEDIN: "LinkedIn (demo listings, not real jobs)",
    JobSource.INDEED: "Indeed (demo listings, not real jobs)",
    JobSource.HANDSHAKE: "Handshake (demo listings, not real jobs)",
}
_LABEL_TO_SOURCE = {v: k for k, v in SOURCE_LABELS.items()}

ACTION_FILTER_OPTIONS = {"all": "All", "unreviewed": "New", "save": "Saved", "apply": "Preparing", "pass": "Passed"}
SPONSORSHIP_FILTER_OPTIONS = ["any", "YES", "NO", "POSSIBLE", "NOT_STATED", "UNKNOWN"]
QUALITY_FILTER_OPTIONS = ["any", "active", "stale", "expired", "broken", "unknown"]
SELECTED_KEY = "selected_job_id"


def _service() -> JobService:
    return job_service_for(st.session_state[OWNER_KEY])


def _render_search_form() -> dict:
    record = st.session_state.get(RECORD_KEY) or {}
    apply_goals_to_search_form(st.session_state, record)
    searched = st.session_state.get("last_search_goals") is not None
    with st.expander("Search and goals", expanded=not searched):
        job_title = st.text_input("Job title", key="job_title", placeholder="e.g. Product Manager")
        location = st.text_input("Location", key="location", placeholder="City, state or country")
        remote_preference = st.selectbox(
            "Work mode", REMOTE_PREFERENCE_OPTIONS, key="remote_preference", format_func=WORK_MODE_LABELS.get
        )
        experience_level = st.multiselect("Level", EXPERIENCE_LEVEL_OPTIONS, key="experience_level")
        industries = st.multiselect("Industries", INDUSTRY_OPTIONS, key="industries")
        min_salary = st.number_input("Minimum salary (USD)", min_value=0, step=5000, value=0, key="min_salary")
        with st.expander("More filters"):
            max_salary = st.number_input("Maximum salary (0 = no maximum)", min_value=0, step=5000, value=0, key="max_salary")
            employment_type = st.multiselect("Job type", EMPLOYMENT_TYPE_OPTIONS, key="employment_type")
            sponsorship_required = st.checkbox("I need visa sponsorship", key="sponsorship_required")
            relocation_willing = st.checkbox("I'm open to relocating", key="relocation_willing")
            target_companies = st.text_area("Only these companies (comma-separated)", key="target_companies")
            exclude_companies = st.text_area("Skip these companies (comma-separated)", key="exclude_companies")
    return {
        "job_title": job_title, "location": location, "industries": industries,
        "min_salary": min_salary, "max_salary": max_salary, "remote_preference": remote_preference,
        "experience_level": experience_level, "employment_type": employment_type,
        "sponsorship_required": sponsorship_required, "relocation_willing": relocation_willing,
        "target_companies": target_companies, "exclude_companies": exclude_companies,
    }


def _render_sources() -> list:
    with st.expander("Sources"):
        st.caption("Greenhouse, Lever and Ashby list real openings from public company boards. "
                   "Demo sources show sample listings only and are off by default.")
        labels = st.multiselect(
            "Search these sources", [SOURCE_LABELS[s] for s in SOURCE_OPTIONS],
            default=[SOURCE_LABELS[s] for s in LIVE_SOURCES], key="selected_sources",
        )
    return [_LABEL_TO_SOURCE[label] for label in labels]


def _search_summary_text(summary) -> tuple[str, str]:
    status = summary.status.value
    failed = [p for p in summary.providers if p.status.value != "ok"]
    if status == "ok":
        return "verified", f"Found {summary.total_stored} open {'role' if summary.total_stored == 1 else 'roles'}."
    if status == "partial":
        return "review", (f"Found {summary.total_stored} roles, but {len(failed)} "
                          f"{'source' if len(failed) == 1 else 'sources'} didn't respond. Results may be incomplete.")
    return "blocked", "The search couldn't reach any source. Check your connection and try again."


def _run_search(form: dict, sources: list) -> None:
    if not sources:
        st.error("Choose at least one source under Sources.")
        return
    try:
        goals = build_search_goals_from_form(form)
    except ValueError as exc:
        st.error(f"Check your search: {exc}")
        return
    try:
        with st.spinner("Searching 63 company boards. The first search takes about 30 seconds."):
            summary = _service().search_and_store(goals, sources)
    except Exception as exc:
        st.error(f"The search didn't finish: {exc}. Try again in a moment.")
        return
    st.session_state.last_search_run = summary
    st.session_state.last_search_goals = goals
    st.session_state.pop(SELECTED_KEY, None)
    st.session_state["jobs_view"] = "Latest search"


def _render_left(form_record) -> None:
    form = _render_search_form()
    sources = _render_sources()
    if st.button("Search roles", type="primary", use_container_width=True):
        _run_search(form, sources)
        st.rerun()
    record = st.session_state.get(RECORD_KEY)
    if record and form.get("job_title") and st.button("Save as my goals", use_container_width=True,
                                                       help="Next time, Jobs starts with these."):
        save_goals(record, form_to_goals(form))
        save_record(st.session_state, st.session_state[OWNER_KEY], record)
        st.toast("Goals saved to your Career Profile.")
    summary = st.session_state.get("last_search_run")
    if summary is not None:
        tone, text = _search_summary_text(summary)
        st.markdown(f'<div class="jc-status {tone}">{escape(text)}</div>', unsafe_allow_html=True)
        if summary.save_failed:
            st.error(f"{summary.save_failed} roles couldn't be saved: {summary.save_error}")
        with st.expander("Details by source"):
            for p in summary.providers:
                st.markdown(f"- {p.source.value.title()}: {p.status.value}, {p.scraped} found"
                            + (f" ({p.error})" if p.error else ""))
        if any(s in DEMO_SOURCES for s in (st.session_state.last_search_goals and sources or [])):
            st.warning("Demo sources returned sample listings, not real jobs.")


def _result_filters() -> DashboardFilters:
    with st.expander("Filter and sort results"):
        c1, c2 = st.columns(2)
        action = c1.selectbox("Status", list(ACTION_FILTER_OPTIONS), format_func=ACTION_FILTER_OPTIONS.get, key="action_filter")
        quality = c2.selectbox("Posting quality", QUALITY_FILTER_OPTIONS, key="quality_filter")
        sponsorship = c1.selectbox("Sponsorship", SPONSORSHIP_FILTER_OPTIONS, key="sponsorship_filter")
        work_mode = c2.selectbox("Work mode", ["any", "remote", "hybrid", "onsite"], key="work_mode_filter")
        min_fit = c1.number_input("Minimum fit %", 0, 100, 0, 5, key="min_fit_filter")
        min_salary = c2.number_input("Minimum stated salary", min_value=0, value=0, step=5000, key="min_salary_filter")
        sort_by = c1.selectbox("Sort by", list(SORT_OPTIONS), key="sort_by")
        sort_dir = c2.selectbox("Order", ["desc", "asc"], key="sort_dir", format_func={"desc": "High to low", "asc": "Low to high"}.get)
        keyword = st.text_input("Keyword", key="keyword_filter")
    return DashboardFilters(
        action=action, min_fit=float(min_fit) if min_fit else None,
        min_salary=int(min_salary) if min_salary else None,
        sponsorship=None if sponsorship == "any" else sponsorship,
        work_mode=None if work_mode == "any" else work_mode, source=None,
        quality=None if quality == "any" else quality,
        keyword=keyword.strip() or None, sort_by=sort_by, sort_dir=sort_dir,
    )


def _record_action(job, action: str, fit) -> None:
    job_id = job_id_for(job)
    try:
        _service().db.record_user_selection(UserSelection(job_posting_id=job_id, action=action))
    except Exception as exc:
        st.error(f"Couldn't save your choice: {exc}")
        return
    if action == TriageAction.APPLY.value:
        st.session_state[PENDING_TAILOR_JOB_KEY] = build_tailor_snapshot(job, fit)
        st.switch_page("pages/5_Tailor.py")
    st.toast({"save": "Saved for later.", "pass": "Passed. It won't be suggested again."}.get(action, "Saved."))
    st.rerun()


def _load_jobs():
    service = _service()
    view = st.radio("Show", ["Latest search", "Saved jobs"], horizontal=True, key="jobs_view", label_visibility="collapsed")
    if view == "Saved jobs":
        return service.db.get_jobs_by_latest_action("save", limit=100), view
    goals = st.session_state.get("last_search_goals")
    if goals is None:
        return None, view
    last_run = st.session_state.get("last_search_run")
    return service.get_available_jobs(goals, seen_since=last_run.started_at if last_run else None), view


def _render_results_and_detail(results_col, detail_col) -> None:
    with results_col:
        st.markdown("### Matching jobs")
        try:
            jobs, view = _load_jobs()
        except Exception as exc:
            st.error(f"Couldn't load jobs: {exc}. Try searching again.")
            return
        if jobs is None or not jobs:
            if jobs is None:
                st.info("Set your goals on the left and choose **Search roles**. Results stay here while you adjust filters.")
            else:
                st.info("No saved jobs yet. Choose **Save** on a result to keep it here." if view == "Saved jobs" else
                        "No open postings matched. Try fewer or broader words in the job title, or a different work mode.")
            with detail_col:
                st.markdown(
                    '<div class="jc-panel"><h3>Job details</h3><p class="jc-muted">Choose a job to see why it matches, '
                    "what's genuinely missing, and what the posting doesn't say.</p></div>",
                    unsafe_allow_html=True,
                )
            return
        service = _service()
        ids = [job_id_for(j) for j in jobs]
        actions = service.db.get_latest_actions(ids)
        profile = get_career_profile(st.session_state)
        fits = service.fit_results_cached(profile, jobs, st.session_state.setdefault("fit_cache", {})) if profile else {}
        quality = {job_id_for(j): evaluate_job_quality(j) for j in jobs}
        filters = _result_filters()
        shown = filter_and_sort_jobs(
            jobs, filters, fit_scores={k: (r.overall_fit if r else None) for k, r in fits.items()},
            actions=actions, quality_by_id=quality,
        )
        if not profile:
            st.caption("Fit isn't assessed until your Career Profile has a resume.")
        st.caption(f"Showing {len(shown)} of {len(jobs)}.")
        if not shown:
            st.info("No results match these filters. Loosen a filter to see more.")
            return
        selected = st.session_state.get(SELECTED_KEY)
        if selected not in {job_id_for(j) for j in shown}:
            selected = job_id_for(shown[0])
            st.session_state[SELECTED_KEY] = selected
        with st.container(height=640):
            for job in shown:
                job_id = job_id_for(job)
                row = build_row(job, fits.get(job_id), actions.get(job_id), quality.get(job_id))
                with st.container(border=True):
                    marker = "▶ " if job_id == selected else ""
                    st.markdown(
                        f"<strong>{marker}{escape(row.title)}</strong><br>"
                        f'<span class="jc-meta">{escape(row.company)} · {escape(row.location)} · {escape(row.work_mode)}</span><br>'
                        f"{chip(row.fit, row.fit_tone)}{chip(row.salary)}{chip(row.freshness)}"
                        f"{chip(row.source, 'review' if row.is_demo else '')}{chip(row.status)}",
                        unsafe_allow_html=True,
                    )
                    b1, b2, b3 = st.columns(3)
                    if b1.button("View", key=f"view_{job_id}", use_container_width=True,
                                 type="primary" if job_id == selected else "secondary"):
                        st.session_state[SELECTED_KEY] = job_id
                        st.rerun()
                    if b2.button("Save", key=f"{job_id}_save", use_container_width=True):
                        _record_action(job, TriageAction.SAVE.value, fits.get(job_id))
                    if b3.button("Pass", key=f"{job_id}_pass", use_container_width=True):
                        _record_action(job, TriageAction.PASS.value, fits.get(job_id))
        job = next(j for j in shown if job_id_for(j) == selected)
    with detail_col:
        _render_detail(job, fits.get(selected), actions.get(selected), quality.get(selected))


def _evidence_list(title: str, lines, tone: str, empty: str) -> None:
    st.markdown(f"**{escape(title)}**")
    if not lines:
        st.markdown(f'<span class="jc-meta">{escape(empty)}</span>', unsafe_allow_html=True)
        return
    for line in lines[:8]:
        if hasattr(line, "requirement"):
            st.markdown(
                f'<div class="jc-chain" style="grid-template-columns:1fr auto 1.4fr">'
                f"<div><small>Requirement</small>{escape(line.requirement)}</div><div class=\"jc-arrow\">→</div>"
                f"<div><small>Your evidence</small>{escape(line.evidence)}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"{chip('•', tone)} {escape(line)}", unsafe_allow_html=True)


def _render_detail(job, fit, action, quality) -> None:
    record = st.session_state.get(RECORD_KEY) or {}
    detail = build_detail(job, fit, action, record.get("authorization"), quality)
    row = detail.row
    st.markdown(
        f'<div class="jc-panel"><div class="jc-eyebrow">{escape(row.company)}</div>'
        f'<h2 style="margin:.1rem 0 .4rem">{escape(row.title)}</h2>'
        f"{chip(row.fit, row.fit_tone)}{chip(row.quality, row.quality_tone)}{chip(row.status)}"
        f'<p style="margin-top:.5rem">{escape(detail.summary)}</p></div>',
        unsafe_allow_html=True,
    )
    a1, a2, a3 = st.columns([1.6, 1, 1])
    if a1.button("Prepare application", type="primary", key=f"{row.job_id}_apply", use_container_width=True,
                 disabled=row.is_demo, help="Demo listings aren't real jobs." if row.is_demo else
                 "Opens Tailor with this job. Nothing is submitted."):
        _record_action(job, TriageAction.APPLY.value, fit)
    if a2.button("Save", key=f"detail_{row.job_id}_save", use_container_width=True):
        _record_action(job, TriageAction.SAVE.value, fit)
    if a3.button("Pass", key=f"detail_{row.job_id}_pass", use_container_width=True):
        _record_action(job, TriageAction.PASS.value, fit)

    if detail.hard_gates:
        st.markdown("#### Hard requirements to check")
        for gate in detail.hard_gates:
            st.markdown(f'<div class="jc-status blocked">{escape(gate)}</div>', unsafe_allow_html=True)
    st.markdown("#### Why it matches")
    _evidence_list("Strong evidence", detail.strong, "verified", "None found yet.")
    _evidence_list("Partial evidence", detail.partial, "review", "None.")
    st.markdown("#### What's missing")
    _evidence_list("Genuine gaps (never added to your resume)", detail.gaps, "blocked", "No gaps against the stated requirements.")
    _evidence_list("Unknown", detail.unknowns, "", "Nothing unknown.")
    if detail.fit_parts:
        with st.expander("How the fit score is made"):
            for name, value in detail.fit_parts:
                st.markdown(f"- {name}: {value}")
            st.caption("Candidate fit measures your background against the posting. It is separate from how well a resume shows it.")
    st.markdown("#### Details")
    rows = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in detail.facts)
    st.markdown(f'<table class="jc-table">{rows}</table>', unsafe_allow_html=True)
    if detail.url:
        st.link_button("Read the full posting", detail.url)
    if job.alternative_sources:
        st.caption("Also posted on: " + ", ".join(job.alternative_sources))


def main():
    require_identity()
    render_app_shell("Jobs")
    render_page_header(
        "Jobs",
        "Search real openings, see exactly why each one matches, and choose one to prepare. Nothing is submitted from here.",
    )
    apply_goals_to_search_form(st.session_state, st.session_state.get(RECORD_KEY) or {})
    searched = st.session_state.get("last_search_goals") is not None
    selected = bool(st.session_state.get(SELECTED_KEY))
    render_progress(
        progress_steps(("Set goals", "Search", "Review a role", "Prepare application"),
                       (bool(st.session_state.get("job_title")), searched, searched and selected,
                        bool(st.session_state.get(PENDING_TAILOR_JOB_KEY)))),
        "Search and triage",
    )
    left, results, detail = st.columns([0.95, 1.3, 1.55], gap="medium")
    with left:
        _render_left(None)
    _render_results_and_detail(results, detail)


main()
