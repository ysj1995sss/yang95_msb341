"""Streamlit rendering of the "About ATS checks" explanation (spec 010)."""

from __future__ import annotations

import streamlit as st

from resume_tailorer.ui import ats_explainer


def render_ats_explainer() -> None:
    with st.expander(ats_explainer.TITLE):
        for paragraph in ats_explainer.PARAGRAPHS:
            st.write(paragraph)


_STATE_WORDS = {"ok": "✓ Passed", "warn": "⚠ Warning", "fail": "✗ Failed", "not_checked": "– Not checked for this version"}


def render_requirement_review(view: dict) -> None:
    """The requirement review (spec 010), from ui.requirement_review_view.review_view."""
    st.markdown("### Requirement review")
    st.caption(f"{view['summary']}. Each line shows the posting's words and the exact fact behind the status. "
               "Only requirements with direct or transferable evidence are made clearer; the rest are never added.")
    if view.get("note"):
        st.caption(view["note"])
    for group in view["groups"]:
        st.markdown(f"**{group['label']}**")
        for row in group["rows"]:
            shown = {True: " · shown in this resume", False: " · not shown yet"}.get(row["shown_in_resume"], "")
            gate = " · hard requirement" if row["hard_gate"] and row["status"] == "none" else ""
            with st.expander(f"{row['label']}{gate}: {row['text']}{shown}"):
                st.write(row["reason"])
                if row.get("terms"):
                    st.write(" · ".join(f"{t['term']}: {t['label']}" for t in row["terms"]))
                for evidence in row["evidence"]:
                    confirmed = "confirmed by you" if evidence["confirmed"] else "not confirmed yet"
                    st.markdown(f"> {evidence['text']}\n\n{evidence['source']} · {confirmed}")


def render_readability(view: dict) -> None:
    problems = any(item["state"] in ("warn", "fail") for item in view["items"])
    with st.expander("Readability check", expanded=problems):
        st.caption(view["note"])
        for item in view["items"]:
            line = f"{_STATE_WORDS[item['state']]}: {item['label']}"
            st.write(line + (f" — {item['message']}" if item["message"] else ""))


def render_keyword_report(view: dict) -> None:
    """Spec 011: the terms this version added and the ones still left out, and why."""
    st.markdown("### Keywords")
    st.caption(view["note"])
    added = ", ".join(item["term"] for item in view["added"]) or "None"
    st.markdown(f"**Added in this version:** {added}")
    if view["already"]:
        st.markdown(f"**Already in your resume:** {', '.join(view['already'])}")
    if view["left_out"]:
        st.markdown("**Still left out:**")
        for group in view["left_out"]:
            st.markdown(f"- {group['label']}: {', '.join(group['terms'])}")
