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

st.set_page_config(page_title="Review Your Profile", page_icon="\U0001F4C4", layout="wide")

DEFAULT_API_BASE = "http://localhost:8000"


def _verified_badge(path: str, verification: dict) -> str:
    return "🖊️ you added/edited" if verification.get(path) == "user_verified" else "📄 from resume"


def _login_form():
    st.title("Review Your Profile")
    st.caption("Requires the API server running locally (uvicorn app.main:app, from apps/api).")
    with st.form("login_form"):
        api_base = st.text_input("API base URL", value=DEFAULT_API_BASE)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in / Register")
    if submitted:
        try:
            st.session_state["profile_review_session"] = login_or_register(api_base, email, password)
            st.rerun()
        except ApiError as exc:
            st.error(f"Login failed: {exc.detail}")
        except Exception as exc:  # pragma: no cover -- network errors, UI-only path
            st.error(f"Could not reach the API at {api_base}: {exc}")


def _upload_section(session):
    st.header("1. Upload or replace your resume")
    meta = get_resume_meta(session)
    if meta:
        size_display = f"{meta['size_bytes']} bytes" if meta["size_bytes"] is not None else "size unknown"
        st.success(
            f"Current resume: **{meta['filename']}** (version {meta['version']}, "
            f"{size_display}, uploaded {meta['uploaded_at']})"
        )
        versions = get_resume_versions(session)
        if len(versions) > 1:
            with st.expander(f"Upload history ({len(versions)} versions)"):
                for v in versions:
                    label = "current" if v["is_current"] else f"replaced {v['archived_at']}"
                    st.write(f"v{v['version']} -- {v['filename']} ({label})")
    else:
        st.info("No resume uploaded yet.")

    uploaded = st.file_uploader("Upload a PDF or DOCX resume", type=["pdf", "docx"])
    if uploaded is not None and st.button("Parse this resume"):
        try:
            upload_resume(session, uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")
            st.success("Resume parsed. Scroll down to review it.")
            st.rerun()
        except ApiError as exc:
            st.error(f"Upload failed: {exc.detail}")


def _review_section(session):
    st.header("2. Review your Career Truth Profile")
    try:
        profile = get_profile(session)
        verification = get_verification(session)
    except ApiError as exc:
        st.error(f"Could not load profile: {exc.detail}")
        return

    if not profile.get("skills") and not profile.get("work_experience"):
        st.warning("Nothing parsed yet -- upload a resume above first.")
        return

    st.caption("📄 = extracted verbatim from your resume. 🖊️ = you added or edited this.")

    with st.form("profile_form"):
        st.subheader("Contact Info")
        contact = dict(profile.get("contact_info") or {})
        cols = st.columns(2)
        for i, key in enumerate(["name", "email", "phone", "location"]):
            with cols[i % 2]:
                contact[key] = st.text_input(
                    f"{key.capitalize()} ({_verified_badge(f'contact_info.{key}', verification)})",
                    value=contact.get(key, ""),
                    key=f"contact_{key}",
                )

        st.subheader("Skills")
        skills_text = st.text_area(
            "One skill per line", value="\n".join(profile.get("skills") or []), key="skills_text", height=120
        )

        st.subheader("Tools")
        tools_text = st.text_area(
            "One tool per line", value="\n".join(profile.get("tools") or []), key="tools_text", height=100
        )

        st.subheader("Certifications")
        certs_text = st.text_area(
            "One certification per line",
            value="\n".join(profile.get("certifications") or []),
            key="certs_text",
            height=100,
        )

        st.subheader("Education")
        for i, edu in enumerate(profile.get("education") or []):
            badge = _verified_badge(f"education[{i}]", verification)
            st.text(f"{edu.get('degree', '')} in {edu.get('field', '')} -- {edu.get('institution', '')} ({edu.get('year', '')}) [{badge}]")

        st.subheader("Work Experience")
        for i, job in enumerate(profile.get("work_experience") or []):
            job_badge = _verified_badge(f"work_experience[{i}]", verification)
            st.markdown(f"**{job.get('title', '')} at {job.get('employer', '')}** ({job.get('dates', '')}) [{job_badge}]")
            for j, bullet in enumerate(job.get("responsibilities") or []):
                st.text(f"  - {bullet}  [{_verified_badge(f'work_experience[{i}].responsibilities[{j}]', verification)}]")
            for j, bullet in enumerate(job.get("accomplishments") or []):
                st.text(f"  - {bullet}  [{_verified_badge(f'work_experience[{i}].accomplishments[{j}]', verification)}]")
        st.caption("Editing individual bullets/jobs isn't supported in this form yet -- edit Contact Info/Skills/Tools/Certifications above, or re-upload a corrected resume.")

        saved = st.form_submit_button("Save Changes", type="primary")

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
if session is None:
    _login_form()
else:
    if st.sidebar.button("Log out"):
        del st.session_state["profile_review_session"]
        st.rerun()
    _upload_section(session)
    st.divider()
    _review_section(session)
