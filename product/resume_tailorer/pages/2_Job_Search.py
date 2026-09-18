"""
Streamlit Job Search page (Sprint 2, Task 7).

Lets the user set job search goals, pick which job sources to scrape,
trigger a search, and browse/triage the resulting jobs in a dashboard.

All business logic (validating form input, building SearchGoals, formatting
job data for display, filtering jobs by triage status) lives in
`resume_tailorer.job_search.ui_helpers`, which contains no Streamlit calls
and is covered by tests in tests/test_job_search_ui_helpers.py. This file
is responsible only for rendering and wiring up Streamlit widgets — it is
not unit tested directly, by design (Streamlit UI requires a browser to
exercise meaningfully).

No auto-apply: the "Apply" button only records a UserSelection; actually
tailoring/submitting a resume for a job happens separately via the
Sprint 1 Resume Tailorer flow.
"""

import streamlit as st

from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobSource, UserSelection
from resume_tailorer.job_search.ui_helpers import (
    build_search_goals_from_form,
    filter_jobs_by_action,
    format_job_for_display,
)

# Session-state key used to look up the user's CareerTruthProfile, if one has
# been built elsewhere in the app (e.g. via the resume tailorer flow). Fit
# scoring is skipped gracefully when no profile is present.
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

ACTION_FILTER_OPTIONS = ["all", "unreviewed", "interested", "saved", "skipped", "applied"]


def _get_job_service() -> JobService:
    """Get (or lazily create) the JobService instance stored in session state."""
    if "job_service" not in st.session_state:
        st.session_state.job_service = JobService(db_path=DB_PATH)
    return st.session_state.job_service


def _render_search_goals_form() -> dict:
    """Render the search goals form and return the raw form input dict."""
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
    """Render job source selection and return the list of selected JobSource enums."""
    st.header("2. Job Sources")
    selected_labels = st.multiselect(
        "Select job sources to search",
        options=[source.value for source in SOURCE_OPTIONS],
        default=[JobSource.LINKEDIN.value],
        key="selected_sources",
    )
    return [JobSource(label) for label in selected_labels]


def _render_search_button(form_data: dict, sources: list) -> None:
    """Render the search button and handle the search-and-store action."""
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
        except Exception as exc:
            st.error(f"Search failed: {exc}")


def _render_job_dashboard() -> None:
    """Render the job dashboard: list stored jobs matching the last search goals."""
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

    # Look up each job's latest selection (if any) so we can filter by status.
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
        if career_profile is not None:
            try:
                result = service.get_job_with_fit_score(job_id, career_profile)
                if result is not None:
                    _, fit_score = result
            except Exception:
                # Fit scoring is best-effort; never block the dashboard on it.
                fit_score = None

        display = format_job_for_display(job, fit_score)

        with st.expander(f"{display['Title']} — {display['Company']} ({display['Location']})"):
            st.write(f"**Salary:** {display['Salary']}")
            st.write(f"**Work mode:** {display['Work Mode']}")
            st.write(f"**Sponsorship available:** {display['Sponsorship']}")
            st.write(f"**Posted:** {display['Posted Date']}")
            st.write(f"**Source:** {display['Source']}")
            st.write(f"**Fit Score:** {display['Fit Score']}")
            if display["URL"]:
                st.write(f"[View posting]({display['URL']})")
            if job.alternative_sources:
                st.caption(
                    "Also posted on: " + ", ".join(job.alternative_sources)
                )

            action_cols = st.columns(4)
            actions = ["interested", "saved", "skipped", "applied"]
            labels = ["Interested", "Save", "Skip", "Apply"]
            for col, action, label in zip(action_cols, actions, labels):
                if col.button(label, key=f"{job_id}_{action}"):
                    selection = UserSelection(job_posting_id=job_id, action=action)
                    if service.db.record_user_selection(selection):
                        st.success(f"Recorded '{action}' for {display['Title']}.")
                    else:
                        st.error("Failed to record selection.")


def main():
    st.title("Job Search")
    st.caption(
        "Set your search goals, choose which sources to scrape, and triage "
        "the results below."
    )
    st.warning(
        "⚠️ Demo Mode: Job listings shown are simulated placeholder data "
        "for testing the search/filter/triage flow. Real scraper integrations "
        "(LinkedIn, Indeed, Handshake, Greenhouse APIs) are a follow-up item — "
        "see decisions/ for tracking. Real job data will never be fabricated "
        "once live scraping is integrated; only actually-scraped fields will "
        "be shown, with 'Unknown'/'Not specified' for anything a real posting "
        "doesn't provide."
    )

    form_data = _render_search_goals_form()
    sources = _render_source_selection()
    _render_search_button(form_data, sources)
    _render_job_dashboard()


if __name__ == "__main__":
    main()
