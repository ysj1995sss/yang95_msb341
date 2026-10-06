"""Streamlit rendering of the "About ATS checks" explanation (spec 010)."""

from __future__ import annotations

import streamlit as st

from resume_tailorer.ui import ats_explainer


def render_ats_explainer() -> None:
    with st.expander(ats_explainer.TITLE):
        for paragraph in ats_explainer.PARAGRAPHS:
            st.write(paragraph)
