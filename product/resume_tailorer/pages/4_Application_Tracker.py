"""Tracker: every application, what was true when you applied, and what's next (spec 007)."""

import streamlit as st

from resume_tailorer.applications.streamlit_views import render_application_tracker
from resume_tailorer.ui import render_app_shell, render_page_header
from resume_tailorer.ui.auth_gate import job_service_for, require_identity

st.set_page_config(page_title="Tracker · Job Copilot", page_icon="📍", layout="wide")

identity = require_identity()
render_app_shell("Tracker")
render_page_header(
    "Tracker",
    "Where each application stands, the exact resume and answers you used, and the next thing to do.",
)
try:
    render_application_tracker(job_service_for(identity.owner_id), identity.owner_id)
except Exception as exc:
    st.error(f"Your applications couldn't be loaded: {exc}. Reload the page to try again.")
