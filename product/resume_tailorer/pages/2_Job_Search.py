"""
Streamlit Job Search page (Steps 4–9).

Sets search goals, picks sources, scouts jobs, and triages with SAVE/APPLY/PASS.
APPLY hands the job description + fit snapshot to Resume Tailorer (Step 10).
"""

import streamlit as st

from resume_tailorer.ui.auth_gate import OWNER_KEY, job_service_for, require_identity

from resume_tailorer.session_profile import get_career_profile

from resume_tailorer.job_search.dashboard import SORT_OPTIONS, filter_and_sort_jobs
from resume_tailorer.job_search.job_attributes import (
    EMPLOYMENT_TYPE_OPTIONS,
    EXPERIENCE_LEVEL_OPTIONS,
    INDUSTRY_OPTIONS,
    employment_type_for,
    experience_level_for,
    industry_for,
)
from resume_tailorer.job_search.job_quality import evaluate_job_quality
from resume_tailorer.job_search.job_service import (
    PENDING_TAILOR_JOB_KEY,
    JobService,
    build_tailor_snapshot,
)
from resume_tailorer.job_search.models import (
    DashboardFilters,
    JobSource,
    TriageAction,
    UserSelection,
)
from resume_tailorer.job_search.ui_helpers import (
    build_job_card_view,
    build_search_goals_from_form,
    format_job_for_display,
)
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header


st.set_page_config(page_title="Job Search", page_icon="\U0001F50D", layout="wide")


REMOTE_PREFERENCE_OPTIONS = ["any", "remote", "hybrid", "onsite"]
LIVE_SOURCES = [JobSource.GREENHOUSE, JobSource.LEVER, JobSource.ASHBY]
DEMO_SOURCES = [JobSource.LINKEDIN, JobSource.INDEED, JobSource.HANDSHAKE]
SOURCE_OPTIONS = LIVE_SOURCES + DEMO_SOURCES
SOURCE_LABELS = {
    JobSource.GREENHOUSE: "greenhouse — live (36 company boards)",
    JobSource.LEVER: "lever — live (8 company boards)",
    JobSource.ASHBY: "ashby — live (19 company boards)",
    JobSource.LINKEDIN: "linkedin — limited (demo data)",
    JobSource.INDEED: "indeed — limited (demo data)",
    JobSource.HANDSHAKE: "handshake — limited (demo data)",
}
_LABEL_TO_SOURCE = {v: k for k, v in SOURCE_LABELS.items()}

ACTION_FILTER_OPTIONS = ["all", "unreviewed", "save", "apply", "pass"]
SPONSORSHIP_FILTER_OPTIONS = ["any", "YES", "NO", "POSSIBLE", "NOT_STATED", "UNKNOWN"]
QUALITY_FILTER_OPTIONS = ["any", "active", "stale", "expired", "broken", "unknown"]
WORK_MODE_FILTER_OPTIONS = ["any", "remote", "hybrid", "onsite"]
SOURCE_FILTER_OPTIONS = ["any"] + [s.value for s in SOURCE_OPTIONS]


def _get_job_service() -> JobService:
    return job_service_for(st.session_state[OWNER_KEY])


def _render_search_goals_form() -> dict:
    st.subheader("Search criteria")
    st.caption("Only a job title is required. Leave anything else blank for no preference.")

    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input("Job title", key="job_title")
        location = st.text_input("Location", key="location")
        industries = st.multiselect("Industries", INDUSTRY_OPTIONS, key="industries")
        remote_preference = st.selectbox(
            "Remote preference", REMOTE_PREFERENCE_OPTIONS, key="remote_preference"
        )
        experience_level = st.multiselect(
            "Experience level", EXPERIENCE_LEVEL_OPTIONS, key="experience_level"
        )

    with col2:
        min_salary = st.number_input(
            "Minimum salary", min_value=0, step=5000, value=0, key="min_salary"
        )
        max_salary = st.number_input(
            "Maximum salary (0 = no maximum)", min_value=0, step=5000, value=0, key="max_salary"
        )
        employment_type = st.multiselect(
            "Employment type", EMPLOYMENT_TYPE_OPTIONS, key="employment_type"
        )

    sponsorship_required = st.checkbox("Sponsorship required", key="sponsorship_required")
    relocation_willing = st.checkbox("Willing to relocate", key="relocation_willing")

    target_companies = st.text_area(
        "Target companies (comma-separated)", key="target_companies"
    )
    exclude_companies = st.text_area(
        "Exclude companies (comma-separated)", key="exclude_companies"
    )

    return {
        "job_title": job_title,
        "location": location,
        "industries": industries,
        "min_salary": min_salary,
        "max_salary": max_salary,
        "remote_preference": remote_preference,
        "experience_level": experience_level,
        "employment_type": employment_type,
        "sponsorship_required": sponsorship_required,
        "relocation_willing": relocation_willing,
        "target_companies": target_companies,
        "exclude_companies": exclude_companies,
    }


def _render_source_selection() -> list:
    st.subheader("Sources")
    st.caption(
        "Greenhouse, Lever, and Ashby return live listings from public company boards. LinkedIn, Indeed, and "
        "Handshake are demo/limited until a permitted connector is available."
    )
    default_labels = [SOURCE_LABELS[s] for s in LIVE_SOURCES]
    selected_labels = st.multiselect(
        "Select job sources to search",
        options=[SOURCE_LABELS[s] for s in SOURCE_OPTIONS],
        default=default_labels,
        key="selected_sources",
    )
    return [_LABEL_TO_SOURCE[label] for label in selected_labels]


def _render_search_run_summary(summary) -> None:
    status = summary.status.value
    if status == "ok":
        st.success(
            f"Stored {summary.total_stored} job posting(s) "
            f"(scraped {summary.total_scraped}, after dedupe {summary.total_after_dedupe})."
        )
    elif status == "partial":
        st.warning(
            f"Partial search: stored {summary.total_stored} job(s). "
            "One or more sources failed — others still contributed."
        )
    else:
        st.error(
            f"Search failed across selected sources "
            f"(stored {summary.total_stored}). See per-source details below."
        )

    if summary.save_failed:
        st.error(
            f"{summary.save_failed} job(s) could not be saved and are missing from the results: "
            f"{summary.save_error}"
        )

    lines = []
    for provider in summary.providers:
        err = f" — {provider.error}" if provider.error else ""
        lines.append(
            f"- **{provider.source.value}**: {provider.status.value}, "
            f"scraped {provider.scraped}{err}"
        )
    if lines:
        st.markdown("**Search run by source**\n" + "\n".join(lines))


def _render_search_button(form_data: dict, sources: list) -> None:
    searched = st.button("Search roles", type="primary", use_container_width=True)
    if searched:
        if not sources:
            st.error("Please select at least one job source.")
            return

        try:
            goals = build_search_goals_from_form(form_data)
        except ValueError as exc:
            st.error(f"Invalid search goals: {exc}")
            return

        service = _get_job_service()
        try:
            with st.spinner("Searching 63 company boards. The first search can take about 30 seconds; searches in the next 15 minutes are faster."):
                summary = service.search_and_store(goals, sources)
            st.session_state.last_search_run = summary
            st.session_state.last_search_goals = goals
            _render_search_run_summary(summary)

            if summary.total_stored == 0 and summary.status.value == "ok":
                st.info(
                    "No open postings matched this job title. Try fewer or broader words."
                )
            if any(source in DEMO_SOURCES for source in sources):
                st.warning(
                    "LinkedIn, Indeed, and Handshake results are simulated demo "
                    "listings, not real jobs."
                )
        except Exception as exc:
            st.error(f"Search failed: {exc}")

    prior = st.session_state.get("last_search_run")
    if prior is not None and not searched:
        with st.expander("Last search run", expanded=False):
            _render_search_run_summary(prior)


def _render_dashboard_filters() -> DashboardFilters:
    st.subheader("Filters & sort")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        action_filter = st.selectbox(
            "Status", ACTION_FILTER_OPTIONS, key="action_filter"
        )
        sponsorship = st.selectbox(
            "Sponsorship", SPONSORSHIP_FILTER_OPTIONS, key="sponsorship_filter"
        )
    with c2:
        quality = st.selectbox(
            "Quality", QUALITY_FILTER_OPTIONS, key="quality_filter"
        )
        work_mode = st.selectbox(
            "Work mode", WORK_MODE_FILTER_OPTIONS, key="work_mode_filter"
        )
    with c3:
        source = st.selectbox(
            "Source", SOURCE_FILTER_OPTIONS, key="source_filter"
        )
        min_fit = st.number_input(
            "Min fit %", min_value=0, max_value=100, value=0, step=5, key="min_fit_filter"
        )
    with c4:
        min_salary = st.number_input(
            "Min salary", min_value=0, value=0, step=5000, key="min_salary_filter"
        )
        sort_by = st.selectbox("Sort by", list(SORT_OPTIONS), key="sort_by")
        sort_dir = st.selectbox("Sort direction", ["desc", "asc"], key="sort_dir")

    keyword = st.text_input("Keyword (title, company, location, description)", key="keyword_filter")

    return DashboardFilters(
        action=action_filter,
        min_fit=float(min_fit) if min_fit else None,
        min_salary=int(min_salary) if min_salary else None,
        sponsorship=None if sponsorship == "any" else sponsorship,
        work_mode=None if work_mode == "any" else work_mode,
        source=None if source == "any" else source,
        quality=None if quality == "any" else quality,
        keyword=keyword.strip() or None,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def _render_job_dashboard() -> None:
    st.subheader("Role evidence feed")

    goals = st.session_state.get("last_search_goals")
    if goals is None:
        st.info("Run a search above to populate the dashboard.")
        return

    service = _get_job_service()
    try:
        last_run = st.session_state.get("last_search_run")
        jobs = service.get_available_jobs(
            goals, seen_since=last_run.started_at if last_run else None
        )
    except Exception as exc:
        st.error(f"Failed to load jobs: {exc}")
        return

    if not jobs:
        st.info("No jobs found for the current search goals.")
        return

    actions = service.db.get_latest_actions([f"{job.source.value}_{job.source_id}" for job in jobs])

    filters = _render_dashboard_filters()

    career_profile = get_career_profile(st.session_state)
    quality_by_id = {f"{job.source.value}_{job.source_id}": evaluate_job_quality(job) for job in jobs}
    fit_results: dict = (
        service.fit_results_cached(career_profile, jobs, st.session_state.setdefault("fit_cache", {}))
        if career_profile is not None
        else {}
    )
    fit_scores = {job_id: (r.overall_fit if r else None) for job_id, r in fit_results.items()}

    filtered_jobs = filter_and_sort_jobs(
        jobs,
        filters,
        fit_scores=fit_scores,
        actions=actions,
        quality_by_id=quality_by_id,
    )

    st.caption(f"Showing {len(filtered_jobs)} of {len(jobs)} job(s).")

    for job in filtered_jobs:
        job_id = f"{job.source.value}_{job.source_id}"
        fit_score = fit_scores.get(job_id)
        fit_result = fit_results.get(job_id)
        quality = quality_by_id.get(job_id)
        display = format_job_for_display(job, fit_score, fit_result, quality)
        card = build_job_card_view(job, fit_result, quality, actions.get(job_id))

        with st.expander(
            f"{card.title} · {card.company} · {card.location} · Fit {card.fit}"
        ):
            facts = st.columns(4)
            facts[0].metric("Candidate fit", card.fit)
            facts[1].metric("Compensation", card.compensation)
            facts[2].metric("Sponsorship", card.sponsorship)
            facts[3].metric("Posting quality", card.quality)
            st.caption(
                f"{display['Work Mode']} · Posted {display['Posted Date']} · "
                f"Deadline {display['Deadline']} · Source {display['Source']} · {card.action}"
            )
            st.caption(
                f"Industry: {industry_for(job)} · Level: {experience_level_for(job)} · "
                f"Job type: {employment_type_for(job)}"
            )
            if fit_result is not None:
                match_cols = st.columns(3)
                match_cols[0].markdown("**Strong evidence**\n\n" + ("\n".join(f"- {item}" for item in card.strong_matches[:5]) or "Not assessed"))
                match_cols[1].markdown("**Partial evidence**\n\n" + ("\n".join(f"- {item}" for item in card.partial_matches[:5]) or "None identified"))
                match_cols[2].markdown("**True gaps**\n\n" + ("\n".join(f"- {item}" for item in card.true_gaps[:5]) or "None identified"))
            if display["URL"]:
                st.write(f"[View posting]({display['URL']})")
            if job.alternative_sources:
                st.caption("Also posted on: " + ", ".join(job.alternative_sources))

            action_cols = st.columns(3)
            triage_actions = [
                (TriageAction.SAVE.value, "Save"),
                (TriageAction.PASS.value, "Pass"),
                (TriageAction.APPLY.value, "Tailor resume"),
            ]
            for col, (action, label) in zip(action_cols, triage_actions):
                if col.button(label, key=f"{job_id}_{action}"):
                    selection = UserSelection(job_posting_id=job_id, action=action)
                    try:
                        service.db.record_user_selection(selection)
                    except Exception as exc:
                        st.error(f"Could not save your choice: {exc}")
                        continue

                    if action == TriageAction.APPLY.value:
                        apply_fit = fit_result
                        if apply_fit is None and career_profile is not None:
                            try:
                                apply_fit = service.fit_scorer.score_fit_detailed(
                                    career_profile, job
                                )
                            except Exception:
                                apply_fit = None
                        st.session_state[PENDING_TAILOR_JOB_KEY] = build_tailor_snapshot(
                            job, apply_fit
                        )
                        st.success(
                            f"Apply recorded for {display['Title']}. "
                            "Opening Resume Tailorer with this job description…"
                        )
                        try:
                            st.switch_page("app.py")
                        except Exception:
                            st.info(
                                "Open **Resume Tailorer** in the sidebar — "
                                "the job description is prefilled."
                            )
                    else:
                        st.success(f"Recorded '{label}' for {display['Title']}.")


def main():
    require_identity()
    render_app_shell("Job Discovery", build_workflow_state(st.session_state))
    render_page_header(
        "Job Discovery",
        "Search permitted sources, inspect why each role matches, and send one evidence snapshot into tailoring.",
    )
    st.info("Greenhouse, Lever, and Ashby are live. LinkedIn, Indeed, and Handshake are demo sources until permitted connectors are available.")
    with st.sidebar:
        form_data = _render_search_goals_form()
        sources = _render_source_selection()
        _render_search_button(form_data, sources)
    _render_job_dashboard()


if __name__ == "__main__":
    main()
