"""Application Tracker workspace."""

import streamlit as st

from resume_tailorer.applications.streamlit_views import render_application_tracker
from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header


st.set_page_config(page_title="Application Tracker", page_icon="📍", layout="wide")


def _get_job_service() -> JobService:
    if "job_service" not in st.session_state:
        st.session_state.job_service = JobService(
            db_path="job_search.db", applications_db_path="applications.db"
        )
    return st.session_state.job_service


render_app_shell("Application Tracker", build_workflow_state(st.session_state))
render_page_header(
    "Application Tracker",
    "See what was true when you applied, where each application stands, and the next action you chose.",
)
render_application_tracker(_get_job_service())
