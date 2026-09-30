"""Application Tracker workspace."""

import streamlit as st

from resume_tailorer.applications.streamlit_views import render_application_tracker
from resume_tailorer.ui.auth_gate import job_service_for, require_identity
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header


st.set_page_config(page_title="Application Tracker", page_icon="📍", layout="wide")


identity = require_identity()
render_app_shell("Application Tracker", build_workflow_state(st.session_state))
render_page_header(
    "Application Tracker",
    "See what was true when you applied, where each application stands, and the next action you chose.",
)
render_application_tracker(job_service_for(identity.owner_id))
