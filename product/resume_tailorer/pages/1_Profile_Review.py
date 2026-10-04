"""Career Profile: the reusable career passport (spec 007).

Verified facts live in one versioned file in the user's own data folder
(profile_store.py), so a resume is imported once and reused by Jobs, Tailor
and Apply. Every fact shows where it came from: from resume, edited by you,
confirmed by you, or missing. Review is by exception: the page leads with
what needs attention and confirms the rest in one step.

Legally significant answers (work authorization, sponsorship) are only ever
what the user chose. Nothing is inferred or drafted.
"""

from datetime import datetime
from html import escape

import streamlit as st

from resume_tailorer.applications.answer_bank import question_key
from resume_tailorer.profile_import import RECORD_KEY, import_resume, load_into_session, save_record, store_for
from resume_tailorer.profile_store import apply_edits, combined_bullets, confirm_remaining, split_bullets
from resume_tailorer.ui import chip, progress_steps, render_app_shell, render_page_header, render_progress
from resume_tailorer.ui.auth_gate import job_service_for, require_identity
from resume_tailorer.ui.goals_wizard import render_goals_wizard
from resume_tailorer.ui.onboarding import (
    YES_NO_LATER,
    answer_to_bool,
    bool_to_answer,
    goals_summary,
)
from resume_tailorer.ui.profile_readiness import build_readiness, provenance_label

st.set_page_config(page_title="Career Profile · Job Copilot", page_icon="\U0001F4C4", layout="wide")


def _prov(record: dict, path: str) -> str:
    label, tone = provenance_label(record, path)
    return chip(label, tone)


def _lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _import_box(owner_id: str, label: str, key: str) -> None:
    upload = st.file_uploader(label, type=["docx", "pdf"], key=key)
    if st.button("Import resume", type="primary", disabled=upload is None, key=f"{key}_go"):
        try:
            with st.spinner("Reading your resume…"):
                import_resume(store_for(owner_id), upload.name, upload.getvalue())
                load_into_session(st.session_state, owner_id, force=True)
        except Exception as exc:
            st.error(f"We couldn't read that file: {exc}. Try the Word version, or a PDF with selectable text.")
            return
        st.toast("Resume imported. Review what needs attention.")
        st.rerun()


def _attention(owner_id: str, record: dict, readiness) -> None:
    if readiness.facts_confirmed and not readiness.attention:
        st.markdown(
            '<div class="jc-status verified"><strong>Your facts are confirmed.</strong> '
            "Only these facts are used when Job Copilot tailors a resume.</div>",
            unsafe_allow_html=True,
        )
        return
    with st.container(border=True):
        if readiness.attention:
            st.markdown(f"### {len(readiness.attention)} {'thing needs' if len(readiness.attention) == 1 else 'things need'} your attention")
            for item in readiness.attention:
                st.markdown(f"- {item}")
            st.caption("Fix these in the sections below. Everything else was read from your resume and only needs a quick look.")
        else:
            st.markdown("### Nothing looks wrong")
            st.caption("Give the facts below a quick look, then confirm them.")
        if not readiness.facts_confirmed:
            if st.button("Confirm the rest", type="primary", key="confirm_rest",
                         help="Marks every fact still 'from resume' as confirmed by you. You can edit any of them later."):
                count = confirm_remaining(record)
                save_record(st.session_state, owner_id, record)
                st.toast(f"Confirmed {count} facts.")
                st.rerun()


def _facts_tab(owner_id: str, record: dict) -> None:
    profile = dict(record.get("profile") or {})
    contact = dict(profile.get("contact_info") or {})
    with st.form("facts_form"):
        st.markdown("### Contact")
        cols = st.columns(2)
        for i, key in enumerate(("name", "email", "phone", "location")):
            with cols[i % 2]:
                st.markdown(_prov(record, f"contact_info.{key}"), unsafe_allow_html=True)
                contact[key] = st.text_input(key.capitalize(), value=contact.get(key, ""), key=f"cp_contact_{key}")

        st.markdown("### Professional summary")
        st.markdown(_prov(record, "summary"), unsafe_allow_html=True)
        summary = st.text_area("Summary", value=profile.get("summary", ""), key="cp_summary", height=90,
                               help="Optional. Used only if your resume has a summary section.")

        st.markdown("### Work history")
        jobs = []
        for i, job in enumerate(profile.get("work_experience") or []):
            label = f"{job.get('title') or 'Role'} · {job.get('employer') or 'Employer'}"
            missing_dates = not (job.get("dates") or "").strip()
            with st.expander(("! " if missing_dates else "") + label, expanded=missing_dates):
                st.markdown(_prov(record, f"work_experience[{i}]"), unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 2, 1.4])
                title = c1.text_input("Title", value=job.get("title", ""), key=f"cp_job_title_{i}")
                employer = c2.text_input("Employer", value=job.get("employer", ""), key=f"cp_job_employer_{i}")
                dates = c3.text_input("Dates", value=job.get("dates", ""), key=f"cp_job_dates_{i}",
                                      placeholder="e.g. Jan 2021 – Present")
                bullets = st.text_area(
                    "Bullet points (one per line)",
                    value="\n".join(combined_bullets(job)),
                    key=f"cp_job_bullets_{i}", height=160,
                )
                responsibilities, accomplishments = split_bullets(job, _lines(bullets))
                jobs.append({**job, "title": title, "employer": employer, "dates": dates,
                             "responsibilities": responsibilities, "accomplishments": accomplishments})

        st.markdown("### Education")
        education = []
        for i, entry in enumerate(profile.get("education") or []):
            st.markdown(_prov(record, f"education[{i}]"), unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([1.3, 1.8, 2.3, 0.9, 0.8])
            degree = c1.text_input("Degree", value=entry.get("degree", ""), key=f"cp_edu_degree_{i}")
            field = c2.text_input("Field", value=entry.get("field", ""), key=f"cp_edu_field_{i}")
            school = c3.text_input("School", value=entry.get("institution", ""), key=f"cp_edu_school_{i}")
            year = c4.text_input("Year", value=str(entry.get("year") or ""), key=f"cp_edu_year_{i}")
            gpa = c5.text_input("GPA", value=entry.get("gpa") or "", key=f"cp_edu_gpa_{i}",
                                placeholder="Optional", help="Leave blank to keep it off your resume facts.")
            education.append({**entry, "degree": degree, "field": field, "institution": school,
                              "year": int(year) if year.strip().isdigit() else 0,
                              "gpa": gpa.strip() or None})
        no_education = st.checkbox("I have no degree to list", value=bool(record.get("no_education")), key="cp_no_edu")

        st.markdown("### Skills and tools")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(_prov(record, "skills"), unsafe_allow_html=True)
            skills = st.text_area("Skills (one per line)", value="\n".join(profile.get("skills") or []), key="cp_skills", height=150)
        with c2:
            st.markdown(_prov(record, "tools"), unsafe_allow_html=True)
            tools = st.text_area("Tools (one per line)", value="\n".join(profile.get("tools") or []), key="cp_tools", height=150)
        st.markdown("### Certifications")
        st.markdown(_prov(record, "certifications"), unsafe_allow_html=True)
        certs = st.text_area("Certifications (one per line)", value="\n".join(profile.get("certifications") or []), key="cp_certs", height=80)

        st.markdown("### Links")
        links = dict(record.get("links") or {})
        lc = st.columns(3)
        links["linkedin"] = lc[0].text_input("LinkedIn", value=links.get("linkedin", ""), key="cp_link_linkedin")
        links["portfolio"] = lc[1].text_input("Portfolio or website", value=links.get("portfolio", ""), key="cp_link_portfolio")
        links["github"] = lc[2].text_input("GitHub", value=links.get("github", ""), key="cp_link_github")

        saved = st.form_submit_button("Save changes", type="primary")

    if saved:
        new_profile = {**profile, "contact_info": contact, "summary": summary.strip(), "work_experience": jobs,
                       "education": education, "skills": _lines(skills), "tools": _lines(tools),
                       "certifications": _lines(certs)}
        changed = apply_edits(record, new_profile)
        record["links"] = links
        record["no_education"] = no_education
        save_record(st.session_state, owner_id, record)
        st.toast(f"Saved. {len(changed)} {'fact' if len(changed) == 1 else 'facts'} marked as edited by you." if changed else "Saved.")
        st.rerun()


def _goals_tab(owner_id: str, record: dict) -> None:
    editing = st.session_state.get("cp_editing_goals") or not (record.get("preferences") or {}).get("job_title")
    if editing:
        if render_goals_wizard(owner_id, "Save goals"):
            st.session_state["cp_editing_goals"] = False
            st.rerun()
        return
    rows = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in goals_summary(record))
    st.markdown(f'<table class="jc-table">{rows}</table>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("Edit goals", key="cp_edit_goals"):
        st.session_state["cp_editing_goals"] = True
        st.rerun()
    c2.page_link("pages/2_Job_Search.py", label="Find jobs with these goals →")


def _authorization_tab(owner_id: str, record: dict) -> None:
    st.caption(
        "Employers ask these on most applications. Only you can answer them. Job Copilot never infers or drafts "
        "work authorization, sponsorship, criminal-history, disability or demographic answers."
    )
    auth = dict(record.get("authorization") or {})
    with st.form("auth_form"):
        authorized = st.radio(
            "Are you legally authorized to work in the country where you're searching?",
            YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(auth.get("authorized_to_work"))), horizontal=True,
        )
        sponsorship = st.radio(
            "Will you now or in the future need an employer to sponsor a work visa?",
            YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(auth.get("sponsorship_required"))), horizontal=True,
        )
        if st.form_submit_button("Save answers", type="primary"):
            auth.update(authorized_to_work=answer_to_bool(authorized), sponsorship_required=answer_to_bool(sponsorship))
            record["authorization"] = auth
            save_record(st.session_state, owner_id, record)
            st.toast("Answers saved.")
            st.rerun()


def _answers_tab(owner_id: str) -> None:
    st.caption(
        "Answers you wrote and approved for application questions. Job Copilot reuses them for the same question "
        "and never writes an answer for you."
    )
    db = job_service_for(owner_id).applications_db
    entries = db.get_answer_entries()
    if not entries:
        st.info("No saved answers yet. When an application asks a question you haven't answered, Apply lets you answer it once.")
    for entry in entries:
        with st.expander(entry["question"]):
            text = st.text_area("Your answer", value=entry["answer"], key=f"cp_ans_{entry['question_key']}")
            c1, c2 = st.columns(2)
            if c1.button("Save answer", key=f"cp_ans_save_{entry['question_key']}"):
                db.save_answer(entry["question_key"], entry["question"], text.strip())
                st.toast("Answer saved.")
                st.rerun()
            if c2.button("Stop reusing this answer", key=f"cp_ans_del_{entry['question_key']}"):
                db.delete_answer(entry["question_key"])
                st.rerun()
    with st.form("new_answer"):
        st.markdown("**Add an answer you want to reuse**")
        question = st.text_input("Question, as employers ask it")
        answer = st.text_area("Your answer", height=80)
        if st.form_submit_button("Save answer") and question.strip() and answer.strip():
            db.save_answer(question_key(question), question.strip(), answer.strip())
            st.toast("Answer saved.")
            st.rerun()


def _side(owner_id: str, record: dict, readiness) -> None:
    st.markdown("### Readiness")
    for section in readiness.sections:
        if section.required:
            mark, tone = ("✓", "verified") if section.ready else ("!", "review")
            state = "Ready" if section.ready else "Needs you"
        else:
            mark, tone = ("✓", "verified") if section.ready else ("–", "")
            state = "Added" if section.ready else "Optional"
        st.markdown(
            f'<div class="jc-row">{chip(mark + " " + state, tone)} {escape(section.name)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("### Resume source")
    meta = record.get("resume")
    if meta:
        uploaded = meta.get("uploaded_at", "")
        try:
            uploaded = datetime.fromisoformat(uploaded).strftime("%b %d, %Y")
        except ValueError:
            pass
        st.markdown(
            f'<div class="jc-meta">{escape(meta["filename"])}<br>Version {meta["version"]} · imported {escape(uploaded)}</div>',
            unsafe_allow_html=True,
        )
        history = record.get("resume_history") or []
        if len(history) > 1:
            st.caption(f"{len(history)} versions kept; earlier versions are never overwritten.")
    with st.expander("Replace with a newer resume"):
        st.caption("Your goals, links and answers are kept. Facts are re-read and need a quick confirmation.")
        _import_box(owner_id, "New resume (Word or PDF)", "cp_replace_upload")


def main():
    identity = require_identity()
    render_app_shell("Career Profile")
    record = st.session_state.get(RECORD_KEY) or {}
    readiness = build_readiness(record)
    render_page_header(
        "Career Profile",
        "Your verified facts, entered once and reused everywhere. Job Copilot only uses what you've confirmed.",
    )
    if st.session_state.get("profile_load_error"):
        st.error("Your saved profile couldn't be read. Import your resume again to rebuild it.")

    if not readiness.has_resume:
        left, right = st.columns([2, 1], gap="large")
        with left:
            st.markdown(
                '<section class="jc-focus"><div class="jc-eyebrow">Start here</div><h2>Import your resume</h2>'
                "<p>Job Copilot reads it once and fills in your profile. You'll only fix what it got wrong.</p></section>",
                unsafe_allow_html=True,
            )
            _import_box(identity.owner_id, "Your resume (Word or PDF)", "cp_first_upload")
            st.caption("Word (.docx) keeps your exact layout in tailored versions.")
        with right:
            st.markdown(
                '<div class="jc-panel"><h3>What a Career Profile holds</h3><p>Contact details, work history, '
                "education, skills, links, job goals, work authorization, and answers you've approved.</p></div>",
                unsafe_allow_html=True,
            )
        return

    required = [s for s in readiness.sections if s.required]
    render_progress(
        progress_steps(tuple(s.name for s in required) + ("Facts confirmed",),
                       tuple(s.ready for s in required) + (readiness.facts_confirmed,)),
        "Profile readiness",
    )
    main_col, side = st.columns([2, 1], gap="large")
    with main_col:
        _attention(identity.owner_id, record, readiness)
        facts, goals, auth, answers = st.tabs(["Facts", "Job goals", "Work authorization", "Saved answers"])
        with facts:
            _facts_tab(identity.owner_id, record)
        with goals:
            _goals_tab(identity.owner_id, record)
        with auth:
            _authorization_tab(identity.owner_id, record)
        with answers:
            _answers_tab(identity.owner_id)
    with side:
        _side(identity.owner_id, record, readiness)


main()
