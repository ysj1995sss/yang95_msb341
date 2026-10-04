"""Career Profile: the reusable career passport (specs 007 and 008).

Verified facts live in one versioned file in the user's own data folder
(profile_store.py), so a resume is imported once and reused by Jobs, Tailor
and Apply. The page is a section summary; one section opens in an editor at a
time. Review is by exception: anything that looks wrong is listed first, and
the rest is confirmed in one step. Provenance is summarised once per section;
fields the user edited are marked.

Legally significant answers (work authorization, sponsorship) are only ever
what the user chose. Nothing is inferred or drafted.
"""

from datetime import datetime
from html import escape

import streamlit as st

from resume_tailorer.applications.answer_bank import question_key
from resume_tailorer.profile_import import RECORD_KEY, import_resume, load_into_session, save_record, store_for
from resume_tailorer.profile_store import EDITED, apply_edits, combined_bullets, confirm_remaining, split_bullets
from resume_tailorer.ui import chip, render_app_shell, render_page_header
from resume_tailorer.ui.auth_gate import job_service_for, require_identity
from resume_tailorer.ui.goals_wizard import render_goals_wizard
from resume_tailorer.ui.onboarding import YES_NO_LATER, answer_to_bool, bool_to_answer, goals_summary
from resume_tailorer.ui.profile_readiness import (
    build_readiness,
    first_section_needing_review,
    provenance_summary,
    section_rows,
)

st.set_page_config(page_title="Career Profile · Job Copilot", page_icon="\U0001F4C4", layout="wide")

OPEN_KEY = "cp_open_section"


def _lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _edited(record: dict, path: str) -> bool:
    return (record.get("provenance") or {}).get(path) == EDITED


def _label(text: str, record: dict, path: str) -> str:
    return text + (" · edited by you" if _edited(record, path) else "")


def _save_profile(owner_id: str, record: dict, new_profile: dict, **extra) -> None:
    changed = apply_edits(record, new_profile)
    record.update(extra)
    save_record(st.session_state, owner_id, record)
    st.toast(f"Saved. {len(changed)} {'fact' if len(changed) == 1 else 'facts'} marked as edited by you."
             if changed else "Saved.")
    st.rerun()


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
        st.session_state.pop(OPEN_KEY, None)
        st.toast("Resume imported. Review what needs attention.")
        st.rerun()


# --- section editors ------------------------------------------------------------

def _edit_contact(owner_id, record, profile):
    contact = dict(profile.get("contact_info") or {})
    with st.form("cp_contact"):
        cols = st.columns(2)
        for i, key in enumerate(("name", "email", "phone", "location")):
            contact[key] = cols[i % 2].text_input(_label(key.capitalize(), record, f"contact_info.{key}"),
                                                  value=contact.get(key, ""))
        if st.form_submit_button("Save contact", type="primary"):
            _save_profile(owner_id, record, {**profile, "contact_info": contact})


def _edit_summary(owner_id, record, profile):
    with st.form("cp_summary"):
        text = st.text_area(_label("Summary", record, "summary"), value=profile.get("summary", ""), height=130,
                            help="Optional. Used only if your resume has a summary section.")
        if st.form_submit_button("Save summary", type="primary"):
            _save_profile(owner_id, record, {**profile, "summary": text.strip()})


def _edit_work(owner_id, record, profile):
    jobs = profile.get("work_experience") or []
    if not jobs:
        st.info("No roles were found in your resume. Re-import a Word version, or check its layout.")
        return
    labels = [f"{j.get('title') or 'Role'} · {j.get('employer') or 'Employer'}" for j in jobs]
    index = st.selectbox("Role", range(len(jobs)), format_func=lambda i: labels[i], key="cp_work_pick")
    job = jobs[index]
    with st.form(f"cp_work_{index}"):
        c1, c2, c3 = st.columns([2, 2, 1.4])
        path = f"work_experience[{index}]"
        title = c1.text_input(_label("Title", record, path), value=job.get("title", ""))
        employer = c2.text_input("Employer", value=job.get("employer", ""))
        dates = c3.text_input("Dates", value=job.get("dates", ""), placeholder="e.g. Jan 2021 – Present")
        bullets = st.text_area("Bullet points (one per line)", value="\n".join(combined_bullets(job)), height=200)
        if st.form_submit_button("Save role", type="primary"):
            responsibilities, accomplishments = split_bullets(job, _lines(bullets))
            updated = list(jobs)
            updated[index] = {**job, "title": title, "employer": employer, "dates": dates,
                              "responsibilities": responsibilities, "accomplishments": accomplishments}
            _save_profile(owner_id, record, {**profile, "work_experience": updated})


def _edit_education(owner_id, record, profile):
    entries = profile.get("education") or []
    with st.form("cp_education"):
        updated = []
        for i, entry in enumerate(entries):
            st.markdown(f"**{escape(entry.get('institution') or 'Education')}**"
                        + (" · edited by you" if _edited(record, f"education[{i}]") else ""))
            c1, c2, c3, c4, c5 = st.columns([1.3, 1.8, 2.3, 0.9, 0.8])
            degree = c1.text_input("Degree", value=entry.get("degree", ""), key=f"cp_edu_degree_{i}")
            field = c2.text_input("Field", value=entry.get("field", ""), key=f"cp_edu_field_{i}")
            school = c3.text_input("School", value=entry.get("institution", ""), key=f"cp_edu_school_{i}")
            year = c4.text_input("Year", value=str(entry.get("year") or ""), key=f"cp_edu_year_{i}")
            gpa = c5.text_input("GPA", value=entry.get("gpa") or "", key=f"cp_edu_gpa_{i}", placeholder="Optional")
            updated.append({**entry, "degree": degree, "field": field, "institution": school,
                            "year": int(year) if year.strip().isdigit() else 0, "gpa": gpa.strip() or None})
        no_education = st.checkbox("I have no degree to list", value=bool(record.get("no_education")))
        if st.form_submit_button("Save education", type="primary"):
            _save_profile(owner_id, record, {**profile, "education": updated}, no_education=no_education)


def _edit_skills(owner_id, record, profile):
    with st.form("cp_skills"):
        c1, c2 = st.columns(2)
        skills = c1.text_area(_label("Skills (one per line)", record, "skills"),
                              value="\n".join(profile.get("skills") or []), height=220)
        tools = c2.text_area(_label("Tools (one per line)", record, "tools"),
                             value="\n".join(profile.get("tools") or []), height=220)
        if st.form_submit_button("Save skills and tools", type="primary"):
            _save_profile(owner_id, record, {**profile, "skills": list(dict.fromkeys(_lines(skills))),
                                             "tools": list(dict.fromkeys(_lines(tools)))})


def _edit_certifications(owner_id, record, profile):
    with st.form("cp_certs"):
        certs = st.text_area(_label("Certifications (one per line)", record, "certifications"),
                             value="\n".join(profile.get("certifications") or []), height=140)
        if st.form_submit_button("Save certifications", type="primary"):
            _save_profile(owner_id, record, {**profile, "certifications": _lines(certs)})


def _edit_links(owner_id, record, profile):
    links = dict(record.get("links") or {})
    with st.form("cp_links"):
        links["linkedin"] = st.text_input("LinkedIn", value=links.get("linkedin", ""))
        links["portfolio"] = st.text_input("Portfolio or website", value=links.get("portfolio", ""))
        links["github"] = st.text_input("GitHub", value=links.get("github", ""))
        if st.form_submit_button("Save links", type="primary"):
            record["links"] = links
            save_record(st.session_state, owner_id, record)
            st.toast("Links saved.")
            st.rerun()


def _edit_goals(owner_id, record, profile):
    if st.session_state.get("cp_editing_goals") or not (record.get("preferences") or {}).get("job_title"):
        if render_goals_wizard(owner_id, "Save goals"):
            st.session_state["cp_editing_goals"] = False
            st.rerun()
        return
    rows = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in goals_summary(record))
    st.markdown(f'<table class="jc-table">{rows}</table>', unsafe_allow_html=True)
    if st.button("Edit goals", key="cp_edit_goals"):
        st.session_state["cp_editing_goals"] = True
        st.rerun()


def _edit_authorization(owner_id, record, profile):
    st.caption("Employers ask these on most applications. Only you can answer them. Job Copilot never infers or "
               "drafts work authorization, sponsorship, criminal-history, disability or demographic answers.")
    auth = dict(record.get("authorization") or {})
    with st.form("cp_auth"):
        authorized = st.radio("Are you legally authorized to work in the country where you're searching?",
                              YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(auth.get("authorized_to_work"))),
                              horizontal=True)
        sponsorship = st.radio("Will you now or in the future need an employer to sponsor a work visa?",
                               YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(auth.get("sponsorship_required"))),
                               horizontal=True)
        if st.form_submit_button("Save answers", type="primary"):
            auth.update(authorized_to_work=answer_to_bool(authorized), sponsorship_required=answer_to_bool(sponsorship))
            record["authorization"] = auth
            save_record(st.session_state, owner_id, record)
            st.toast("Answers saved.")
            st.rerun()


def _edit_answers(owner_id, record, profile):
    st.caption("Answers you wrote and approved for application questions. Job Copilot reuses them for the same "
               "question and never writes an answer for you.")
    db = job_service_for(owner_id).applications_db
    for entry in db.get_answer_entries():
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
    with st.form("cp_new_answer"):
        question = st.text_input("Question, as employers ask it")
        answer = st.text_area("Your answer", height=80)
        if st.form_submit_button("Add answer") and question.strip() and answer.strip():
            db.save_answer(question_key(question), question.strip(), answer.strip())
            st.toast("Answer saved.")
            st.rerun()


EDITORS = {
    "contact": _edit_contact, "summary": _edit_summary, "work": _edit_work, "education": _edit_education,
    "skills": _edit_skills, "certifications": _edit_certifications, "links": _edit_links,
    "goals": _edit_goals, "authorization": _edit_authorization, "answers": _edit_answers,
}


# --- page ---------------------------------------------------------------------

def _attention(owner_id: str, record: dict, readiness, rows) -> None:
    items = [issue for r in rows for issue in r.issues]
    if readiness.facts_confirmed and not items:
        st.markdown('<div class="jc-status verified"><strong>Your facts are confirmed.</strong> '
                    "Only these facts are used when Job Copilot tailors a resume.</div>", unsafe_allow_html=True)
        return
    with st.container(border=True):
        if items:
            st.markdown(f"**Needs your attention · {len(items)} {'item' if len(items) == 1 else 'items'} to review**")
            st.markdown("\n".join(f"- {escape(i)}" for i in items[:6]) + ("\n- …" if len(items) > 6 else ""))
        else:
            st.markdown("**Nothing looks wrong.** Give your sections a quick look, then confirm them.")
        if not readiness.facts_confirmed and st.button(
                "Confirm the rest", type="primary", key="confirm_rest",
                help="Marks every fact still 'from resume' as confirmed by you. You can edit any of them later."):
            count = confirm_remaining(record)
            save_record(st.session_state, owner_id, record)
            st.toast(f"Confirmed {count} facts.")
            st.rerun()


def _summary_list(rows, open_key) -> None:
    with st.container(border=True, key="cp_summary_list"):
        for r in rows:
            c1, c2, c3 = st.columns([2.2, 1.2, 0.9], vertical_alignment="center")
            current = " ▸" if r.key == open_key else ""
            c1.markdown(f"**{escape(r.name)}**{current}<br><span class='jc-meta'>{escape(r.detail)}</span>",
                        unsafe_allow_html=True)
            c2.markdown(chip(r.status, r.tone), unsafe_allow_html=True)
            if c3.button(r.action, key=f"cp_open_{r.key}", use_container_width=True,
                         type="primary" if r.key == open_key else "secondary"):
                st.session_state[OPEN_KEY] = r.key
                st.rerun()


def _resume_source(owner_id: str, record: dict) -> None:
    meta = record.get("resume") or {}
    uploaded = meta.get("uploaded_at", "")
    try:
        uploaded = datetime.fromisoformat(uploaded).strftime("%b %d, %Y")
    except ValueError:
        pass
    versions = len(record.get("resume_history") or [])
    with st.expander(f"Resume source · {meta.get('filename', 'none')} · version {meta.get('version', '–')}"):
        st.caption(f"Imported {uploaded}. {versions} {'version' if versions == 1 else 'versions'} kept; "
                   "earlier versions are never overwritten. Your goals, links and answers are kept when you "
                   "replace it; facts are re-read and need a quick confirmation.")
        _import_box(owner_id, "Replace with a newer resume (Word or PDF)", "cp_replace_upload")


def main():
    identity = require_identity()
    render_app_shell("Career Profile")
    owner_id = identity.owner_id
    record = st.session_state.get(RECORD_KEY) or {}
    readiness = build_readiness(record)
    render_page_header("Career Profile",
                       "Your verified facts, entered once and reused everywhere. Only what you've confirmed is used.")
    if st.session_state.get("profile_load_error"):
        st.error("Your saved profile couldn't be read. Import your resume again to rebuild it.")

    if not readiness.has_resume:
        main_col, side = st.columns([2, 1], gap="large")
        with main_col:
            with st.container(border=True):
                st.markdown('<h2 class="jc-card-title">Import your resume</h2>'
                            '<p class="jc-meta">Job Copilot reads it once and fills in your profile. '
                            "You'll only fix what it got wrong.</p>", unsafe_allow_html=True)
                _import_box(owner_id, "Your resume (Word or PDF)", "cp_first_upload")
                st.caption("Word (.docx) keeps your exact layout in tailored versions.")
        with side:
            st.markdown('<div class="jc-aside"><h3>What a Career Profile holds</h3><p>Contact details, work history, '
                        "education, skills, links, job goals, work authorization, and answers you've approved.</p></div>",
                        unsafe_allow_html=True)
        return

    answers = len(job_service_for(owner_id).applications_db.get_answers())
    rows = section_rows(record, answers)
    if OPEN_KEY not in st.session_state:
        st.session_state[OPEN_KEY] = first_section_needing_review(rows)
    open_key = st.session_state.get(OPEN_KEY)

    _attention(owner_id, record, readiness, rows)
    left, right = st.columns([1, 1.3], gap="large")
    with left:
        _summary_list(rows, open_key)
        _resume_source(owner_id, record)
    with right:
        if not open_key:
            st.markdown('<div class="jc-aside"><h3>Choose a section</h3><p>Pick Edit, Review or Add on the left. '
                        "One section opens here at a time.</p><p>Everything listed under Needs your attention "
                        "is worth a look before you tailor a resume.</p></div>", unsafe_allow_html=True)
            return
        row = next(r for r in rows if r.key == open_key)
        with st.container(border=True, key="cp_editor"):
            head, close = st.columns([4, 1])
            head.markdown(f'<h2 class="jc-card-title">{escape(row.name)}</h2>'
                          f'<p class="jc-meta">{escape(provenance_summary(record, open_key) or row.detail)}</p>',
                          unsafe_allow_html=True)
            if close.button("Close", key="cp_close"):
                st.session_state[OPEN_KEY] = None
                st.rerun()
            for issue in row.issues:
                st.markdown(f'<div class="jc-status review">{escape(issue)}</div>', unsafe_allow_html=True)
            EDITORS[open_key](owner_id, record, record.get("profile") or {})


main()
