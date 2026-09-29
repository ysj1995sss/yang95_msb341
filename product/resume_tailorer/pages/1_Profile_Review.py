"""
Streamlit Career Truth Profile review page.

Unlike the rest of this Streamlit app (which runs the resume_tailorer
engine in-process, no login required), this page talks to the apps/api
FastAPI backend over HTTP -- that's where per-user auth, the persisted
Profile, and the resume-verified/user-verified distinction actually live
(see resume_tailorer.profile_review.api_client's docstring). Requires the
API server running locally (uvicorn app.main:app, from apps/api).

Flow: log in (or register on first use) -> upload a resume, or load the
one already on file -> review Contact Info / Education / Work Experience
/ Skills / Tools / Certifications, each item labeled "from resume" or
"you added/edited" -> edit any field -> Save Changes writes back via
PUT /profile, which is what actually creates the user_verified tags.

All business logic (HTTP calls) lives in api_client.py, which has no
Streamlit import and is unit tested directly; this file is UI wiring only,
per this app's established convention (see pages/2_Job_Search.py).
"""

import streamlit as st

from resume_tailorer.profile_review.api_client import (
    ApiError,
    get_profile,
    get_resume_meta,
    get_resume_versions,
    get_verification,
    login_or_register,
    put_profile,
    upload_resume,
)
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header
from resume_tailorer.ui.fact_vault import build_fact_vault_summary

st.set_page_config(page_title="Review Your Profile", page_icon="\U0001F4C4", layout="wide")

DEFAULT_API_BASE = "http://localhost:8000"


def _verified_badge(path: str, verification: dict) -> str:
    return "🖊️ you added/edited" if verification.get(path) == "user_verified" else "📄 from resume"


def _login_form():
    render_page_header(
        "Fact Vault",
        "Build the verified career record Job Copilot can safely reuse. Sign in to load your private profile.",
    )
    st.info("The profile service must be running locally before you sign in.")
    with st.form("login_form"):
        api_base = st.text_input("API base URL", value=DEFAULT_API_BASE)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Continue to Fact Vault", type="primary")
    if submitted:
        try:
            st.session_state["profile_review_session"] = login_or_register(api_base, email, password)
            st.rerun()
        except ApiError as exc:
            st.error(f"Login failed: {exc.detail}")
        except Exception as exc:  # pragma: no cover -- network errors, UI-only path
            st.error(f"Could not reach the API at {api_base}: {exc}")


def _upload_section(session):
    st.subheader("Resume source")
    meta = get_resume_meta(session)
    if meta:
        size_display = f"{meta['size_bytes']} bytes" if meta["size_bytes"] is not None else "size unknown"
        st.markdown(
            f'<div class="jc-status verified"><strong>Current source</strong><br>'
            f"{meta['filename']} · version {meta['version']} · {size_display}<br>"
            f"Uploaded {meta['uploaded_at']}</div>",
            unsafe_allow_html=True,
        )
        versions = get_resume_versions(session)
        if len(versions) > 1:
            with st.expander(f"Upload history ({len(versions)} versions)"):
                for v in versions:
                    label = "current" if v["is_current"] else f"replaced {v['archived_at']}"
                    st.write(f"v{v['version']} -- {v['filename']} ({label})")
    else:
        st.info("No resume source yet. Upload a PDF or DOCX to extract reusable facts.")

    uploaded = st.file_uploader("Upload a PDF or DOCX resume", type=["pdf", "docx"])
    if uploaded is not None and st.button("Build Fact Vault", type="primary"):
        try:
            upload_resume(session, uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")
            st.success("Fact Vault built. Review the evidence below.")
            st.rerun()
        except ApiError as exc:
            st.error(f"Upload failed: {exc.detail}")


def _review_section(session):
    st.subheader("Verified career evidence")
    try:
        profile = get_profile(session)
        verification = get_verification(session)
    except ApiError as exc:
        st.error(f"Could not load profile: {exc.detail}")
        return

    if not profile.get("skills") and not profile.get("work_experience"):
        st.warning("Your Fact Vault is empty. Upload a resume above to begin.")
        return

    st.session_state["profile_data"] = profile
    summary = build_fact_vault_summary(profile, verification)
    metrics = st.columns(4)
    metrics[0].metric("Reusable facts", summary.resume_fact_count)
    metrics[1].metric("Skills", summary.skill_count)
    metrics[2].metric("Evidence bullets", summary.bullet_count)
    metrics[3].metric("Your edits", summary.user_edit_count)
    st.caption("📄 Extracted from your resume · 🖊️ Added or edited by you")
    tone = "review" if summary.unresolved_count else "verified"
    st.markdown(
        f'<div class="jc-status {tone}">{summary.next_action}</div>',
        unsafe_allow_html=True,
    )

    with st.form("profile_form"):
        st.markdown("### Contact information")
        contact = dict(profile.get("contact_info") or {})
        cols = st.columns(2)
        for i, key in enumerate(["name", "email", "phone", "location"]):
            with cols[i % 2]:
                contact[key] = st.text_input(
                    f"{key.capitalize()} ({_verified_badge(f'contact_info.{key}', verification)})",
                    value=contact.get(key, ""),
                    key=f"contact_{key}",
                )

        st.markdown("### Skills and qualifications")
        skills_text = st.text_area(
            "One skill per line", value="\n".join(profile.get("skills") or []), key="skills_text", height=120
        )

        st.markdown("#### Tools")
        tools_text = st.text_area(
            "One tool per line", value="\n".join(profile.get("tools") or []), key="tools_text", height=100
        )

        st.markdown("#### Certifications")
        certs_text = st.text_area(
            "One certification per line",
            value="\n".join(profile.get("certifications") or []),
            key="certs_text",
            height=100,
        )

        with st.expander("Education evidence", expanded=True):
            for i, edu in enumerate(profile.get("education") or []):
                badge = _verified_badge(f"education[{i}]", verification)
                st.write(f"**{edu.get('degree', '')} in {edu.get('field', '')}** · {edu.get('institution', '')} · {edu.get('year', '')} · {badge}")

        st.markdown("### Work evidence")
        for i, job in enumerate(profile.get("work_experience") or []):
            title = f"{job.get('title', 'Role')} · {job.get('employer', 'Employer')}"
            with st.expander(title, expanded=i == 0):
                job_badge = _verified_badge(f"work_experience[{i}]", verification)
                st.caption(f"{job.get('dates', '')} · {job_badge}")
                for group in ("responsibilities", "accomplishments"):
                    for j, bullet in enumerate(job.get(group) or []):
                        st.markdown(f"- {bullet}  \n  *{_verified_badge(f'work_experience[{i}].{group}[{j}]', verification)}*")
        st.caption("Editing individual bullets/jobs isn't supported in this form yet -- edit Contact Info/Skills/Tools/Certifications above, or re-upload a corrected resume.")

        saved = st.form_submit_button("Save verified facts", type="primary")

    if saved:
        updated = dict(profile)
        updated["contact_info"] = contact
        updated["skills"] = [s.strip() for s in skills_text.splitlines() if s.strip()]
        updated["tools"] = [t.strip() for t in tools_text.splitlines() if t.strip()]
        updated["certifications"] = [c.strip() for c in certs_text.splitlines() if c.strip()]
        try:
            put_profile(session, updated)
            st.success("Saved. Newly added/changed fields are now marked as your own edits.")
            st.rerun()
        except ApiError as exc:
            st.error(f"Save failed: {exc.detail}")


session = st.session_state.get("profile_review_session")
render_app_shell("Fact Vault", build_workflow_state(st.session_state))
if session is None:
    _login_form()
else:
    if st.sidebar.button("Log out"):
        del st.session_state["profile_review_session"]
        st.rerun()
    render_page_header(
        "Fact Vault",
        "Review the facts Job Copilot may use. Resume evidence and your own edits stay visibly distinct.",
    )
    source, evidence = st.columns([1, 2], gap="large")
    with source:
        _upload_section(session)
    with evidence:
        _review_section(session)
