"""
Streamlit Job Search page (Steps 4–9).

Sets search goals, picks sources, scouts jobs, and triages with SAVE/APPLY/PASS.
APPLY hands the job description + fit snapshot to Resume Tailorer (Step 10).
"""

import streamlit as st

from resume_tailorer.job_search.job_service import (
    PENDING_TAILOR_JOB_KEY,
    JobService,
    build_tailor_snapshot,
)
from resume_tailorer.job_search.models import JobSource, TriageAction, UserSelection
from resume_tailorer.job_search.ui_helpers import (
    build_search_goals_from_form,
    filter_jobs_by_action,
    format_job_for_display,
)

CAREER_PROFILE_SESSION_KEY = "career_profile"

st.set_page_config(page_title="Job Search", page_icon="\U0001F50D", layout="wide")

DB_PATH = "job_search.db"

REMOTE_PREFERENCE_OPTIONS = ["any", "remote", "hybrid", "onsite"]
EXPERIENCE_LEVEL_OPTIONS = ["entry", "mid", "senior", "lead", "executive"]
COMPANY_SIZE_OPTIONS = ["any", "startup", "small", "medium", "large", "enterprise"]
EMPLOYMENT_TYPE_OPTIONS = ["full-time", "part-time", "contract", "internship"]
INDUSTRY_OPTIONS = [
    "Technology",
    "Finance",
    "Healthcare",
    "Retail",
    "Manufacturing",
    "Education",
    "Government",
    "Nonprofit",
    "Media",
    "Consulting",
]
SOURCE_OPTIONS = [JobSource.LINKEDIN, JobSource.INDEED, JobSource.HANDSHAKE, JobSource.GREENHOUSE]
SOURCE_LABELS = {
    JobSource.GREENHOUSE: "greenhouse — available (live ATS boards)",
    JobSource.LINKEDIN: "linkedin — limited (demo data)",
    JobSource.INDEED: "indeed — limited (demo data)",
    JobSource.HANDSHAKE: "handshake — limited (demo data)",
}
_LABEL_TO_SOURCE = {v: k for k, v in SOURCE_LABELS.items()}

ACTION_FILTER_OPTIONS = ["all", "unreviewed", "save", "apply", "pass"]


def _get_job_service() -> JobService:
    if "job_service" not in st.session_state:
        st.session_state.job_service = JobService(db_path=DB_PATH)
    return st.session_state.job_service


def _render_search_goals_form() -> dict:
    st.header("1. Search Goals")

    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input("Job title", key="job_title")
        location = st.text_input("Location", key="location")
        industries = st.multiselect("Industries", INDUSTRY_OPTIONS, key="industries")
        remote_preference = st.selectbox(
            "Remote preference", REMOTE_PREFERENCE_OPTIONS, key="remote_preference"
        )
        experience_level = st.selectbox(
            "Experience level", EXPERIENCE_LEVEL_OPTIONS, key="experience_level"
        )

    with col2:
        min_salary = st.number_input(
            "Minimum salary", min_value=0, step=5000, value=0, key="min_salary"
        )
        max_salary = st.number_input(
            "Maximum salary", min_value=0, step=5000, value=200000, key="max_salary"
        )
        company_size = st.selectbox("Company size", COMPANY_SIZE_OPTIONS, key="company_size")
        employment_type = st.selectbox(
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
        "company_size": company_size,
        "employment_type": employment_type,
        "sponsorship_required": sponsorship_required,
        "relocation_willing": relocation_willing,
        "target_companies": target_companies,
        "exclude_companies": exclude_companies,
    }


def _render_source_selection() -> list:
    st.header("2. Job Sources")
    st.caption(
        "Greenhouse can return live public board listings. LinkedIn, Indeed, and "
        "Handshake are demo/limited until a permitted connector is available."
    )
    default_label = SOURCE_LABELS[JobSource.GREENHOUSE]
    selected_labels = st.multiselect(
        "Select job sources to search",
        options=[SOURCE_LABELS[s] for s in SOURCE_OPTIONS],
        default=[default_label],
        key="selected_sources",
    )
    return [_LABEL_TO_SOURCE[label] for label in selected_labels]


def _render_search_button(form_data: dict, sources: list) -> None:
    st.header("3. Run Search")

    if st.button("Search for jobs", type="primary"):
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
            with st.spinner("Searching for jobs..."):
                count = service.search_and_store(goals, sources)
            st.success(f"Stored {count} job posting(s).")
            st.session_state.last_search_goals = goals

            greenhouse_scraper = (
                service._get_scraper(JobSource.GREENHOUSE)
                if JobSource.GREENHOUSE in sources
                else None
            )
            used_real_data = getattr(greenhouse_scraper, "data_source", None) == "real"

            if used_real_data:
                st.success(
                    "Live Data: Greenhouse results include real, currently-posted "
                    "jobs from public company boards."
                )
            else:
                st.warning(
                    "Demo Mode: listings may be simulated placeholder data. "
                    "LinkedIn/Indeed/Handshake remain limited."
                )
        except Exception as exc:
            st.error(f"Search failed: {exc}")


def _render_job_dashboard() -> None:
    st.header("4. Job Dashboard")

    goals = st.session_state.get("last_search_goals")
    if goals is None:
        st.info("Run a search above to populate the dashboard.")
        return

    service = _get_job_service()
    try:
        jobs = service.get_available_jobs(goals)
    except Exception as exc:
        st.error(f"Failed to load jobs: {exc}")
        return

    if not jobs:
        st.info("No jobs found for the current search goals.")
        return

    jobs_with_selections = []
    for job in jobs:
        job_id = f"{job.source.value}_{job.source_id}"
        selections = service.db.get_user_selections(job_id)
        latest_action = selections[0].action if selections else None
        jobs_with_selections.append((job, latest_action))

    action_filter = st.selectbox("Filter by status", ACTION_FILTER_OPTIONS, key="action_filter")
    filtered_jobs = filter_jobs_by_action(jobs_with_selections, action_filter)

    st.caption(f"Showing {len(filtered_jobs)} of {len(jobs)} job(s).")

    career_profile = st.session_state.get(CAREER_PROFILE_SESSION_KEY)

    for job in filtered_jobs:
        job_id = f"{job.source.value}_{job.source_id}"

        fit_score = None
        fit_result = None
        if career_profile is not None:
            try:
                fit_result = service.fit_scorer.score_fit_detailed(career_profile, job)
                fit_score = fit_result.overall_fit
            except Exception:
                fit_score = None
                fit_result = None

        display = format_job_for_display(job, fit_score, fit_result)

        with st.expander(f"{display['Title']} — {display['Company']} ({display['Location']})"):
            st.write(f"**Salary:** {display['Salary']}")
            st.write(f"**Work mode:** {display['Work Mode']}")
            st.write(f"**Sponsorship:** {display['Sponsorship']}")
            st.write(f"**Posted:** {display['Posted Date']}")
            st.write(f"**Deadline:** {display['Deadline']}")
            st.write(f"**Source:** {display['Source']}")
            st.write(f"**Fit Score:** {display['Fit Score']}")
            if fit_result is not None:
                st.write(
                    f"**Fit breakdown:** eligibility {display.get('Fit Eligibility', 'N/A')}, "
                    f"core {display.get('Fit Core', 'N/A')}, "
                    f"preferred {display.get('Fit Preferred', 'N/A')}, "
                    f"evidence {display.get('Fit Evidence Confidence', 'N/A')}"
                )
                if display.get("Fit Strong") and display["Fit Strong"] != "—":
                    st.caption(f"Strong: {display['Fit Strong']}")
                if display.get("Fit Partial") and display["Fit Partial"] != "—":
                    st.caption(f"Partial: {display['Fit Partial']}")
                if display.get("Fit Gaps") and display["Fit Gaps"] != "—":
                    st.caption(f"Gaps: {display['Fit Gaps']}")
            if display["URL"]:
                st.write(f"[View posting]({display['URL']})")
            if job.alternative_sources:
                st.caption("Also posted on: " + ", ".join(job.alternative_sources))

            action_cols = st.columns(3)
            actions = [
                (TriageAction.SAVE.value, "Save"),
                (TriageAction.PASS.value, "Pass"),
                (TriageAction.APPLY.value, "Apply"),
            ]
            for col, (action, label) in zip(action_cols, actions):
                if col.button(label, key=f"{job_id}_{action}"):
                    selection = UserSelection(job_posting_id=job_id, action=action)
                    if not service.db.record_user_selection(selection):
                        st.error("Failed to record selection.")
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
    st.title("Job Search")
    st.caption(
        "Set your search goals, choose which sources to scrape, and triage "
        "the results below."
    )
    form_data = _render_search_goals_form()
    sources = _render_source_selection()
    _render_search_button(form_data, sources)
    _render_job_dashboard()


if __name__ == "__main__":
    main()
