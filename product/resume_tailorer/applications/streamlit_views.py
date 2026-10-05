"""Streamlit rendering for the Tracker, and the preview token Apply uses.

What to show is decided in ui/tracker_views.py; this module only renders it.
"""

from __future__ import annotations

from datetime import date
from html import escape

from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus, StatusSource
from resume_tailorer.applications.status_tracker import StatusTracker


def _weekly_panel(rows, owner_id: str) -> None:
    import streamlit as st

    from resume_tailorer.applications.weekly import build_weekly_summary
    from resume_tailorer.profile_import import RECORD_KEY, save_record

    week = build_weekly_summary([(r.status, r.applied) for r in rows], date.today())
    record = st.session_state.get(RECORD_KEY) or {}
    prefs = record.setdefault("preferences", {})
    goal = int(prefs.get("weekly_goal") or 0)
    st.markdown(f"#### Week of {week.week_start:%b %d}")
    st.metric("Applications sent", week.applied, help="Counted from the day you marked each one as applied.")
    if goal:
        st.progress(min(week.applied / goal, 1.0))
        st.caption(f"{week.applied} of {goal}. A goal is a pace, not a test.")
    a, b = st.columns(2)
    a.metric("In interviews", week.interviews)
    b.metric("Saved, not applied", week.saved)
    new_goal = st.number_input("Weekly goal (0 for none)", min_value=0, max_value=100, value=goal, key="weekly_goal_input")
    if new_goal != goal and record.get("profile") is not None:
        prefs["weekly_goal"] = int(new_goal)
        save_record(st.session_state, owner_id, record)
        st.rerun()


_EMAIL_KEY = "tracker_email_text"


def _confirm_email(status_tracker, application_id, status, notes, evidence, done_message) -> None:
    """Runs before the rerun: record the user's confirmed update, then clear the pasted email."""
    import streamlit as st

    status_tracker.update_status(application_id, status, notes=notes, source=StatusSource.EMAIL_INTEGRATION,
                                 confidence="confirmed by you", evidence=evidence)
    st.session_state[_EMAIL_KEY] = ""
    st.session_state["tracker_email_done"] = done_message


def _email_panel(status_tracker, rows) -> None:
    """Spec 005, first slice: a pasted recruiter email proposes a status; only the user applies it."""
    import streamlit as st

    from resume_tailorer.applications.email_status import Candidate, read_email
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    done = st.session_state.pop("tracker_email_done", None)
    if done:
        st.toast(done)
    with st.expander("Update a status from a recruiter email"):
        st.caption("Paste the email, with its From, Date and Subject lines if you have them. "
                   "Job Copilot suggests the application and status; nothing changes until you confirm.")
        text = st.text_area("Recruiter email", key=_EMAIL_KEY, height=150)
        if not text.strip():
            return
        by_id = {r.application_id: r for r in rows}
        reading = read_email(text, [Candidate(r.application_id, r.company, r.role, r.status) for r in rows])
        if reading.status is None:
            st.info("This email doesn't clearly say a status (a rejection, assessment, interview, offer and so on), "
                    "so there's nothing to update.")
            return
        st.markdown(f"Suggested status: **{escape(STATUS_WORDS.get(reading.status, reading.status.value))}**, "
                    f"because it says \u201c{escape(reading.phrase)}\u201d.", unsafe_allow_html=True)
        matched = [m.application_id for m in reading.matches]
        options = matched + [i for i in by_id if i not in matched]
        application_id = st.selectbox(
            "Which application is this about?", options, index=0 if reading.chosen else None,
            format_func=lambda i: f"{by_id[i].role} at {by_id[i].company}",
            placeholder="Choose the application", key="tracker_email_app",
        )
        if not reading.chosen:
            st.caption("The email doesn't clearly point to one tracked application, so choose it yourself.")
        statuses = list(STATUS_WORDS)
        status = st.selectbox("Status to record", statuses, index=statuses.index(reading.status),
                              format_func=lambda v: STATUS_WORDS[v], key="tracker_email_status")
        email_date = st.date_input("Email date", value=reading.email_date or date.today(), key="tracker_email_date")
        if application_id and reading.moves_backwards(by_id[application_id].status):
            st.warning(f"This would move it back from {STATUS_WORDS.get(by_id[application_id].status)}. "
                       "Confirm only if that's right.")
        st.button(
            "Confirm update", type="primary", disabled=application_id is None, key="tracker_email_confirm",
            on_click=_confirm_email,
            args=(status_tracker, application_id, status, f"from a recruiter email dated {email_date:%b %d, %Y}",
                  (reading.subject or reading.phrase)[:200], f"Updated to {STATUS_WORDS.get(status)}."),
        )


def render_application_tracker(service, owner_id: str = "local") -> None:
    """Dense table, saved views and a detail panel built from immutable snapshots."""
    import streamlit as st

    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.ui.shell import chip
    from resume_tailorer.ui.tracker_views import (
        STATUS_WORDS, VIEWS, build_row, default_view, in_view, sort_rows, view_counts,
    )

    status_tracker = StatusTracker(service.applications_db)
    trackers = status_tracker.get_all_applications()
    if not trackers:
        from resume_tailorer.ui.shell import primary_action
        from resume_tailorer.ui.tracker_views import LIFECYCLE

        main, side = st.columns([2, 1], gap="large")
        with main:
            with st.container(border=True):
                st.markdown(
                    '<h2 class="jc-card-title">Nothing tracked yet</h2>'
                    '<p class="jc-meta">When you choose <strong>Track this application</strong> on Apply, it '
                    "appears here with:</p>"
                    '<div class="jc-check"><span>The exact job posting, as it was when you applied</span></div>'
                    '<div class="jc-check"><span>The tailored resume version and any saved answers you used</span></div>'
                    '<div class="jc-check"><span>Every status change, who made it, and when</span></div>'
                    f'<p class="jc-meta" style="margin-top:.75rem">Status: {escape(" → ".join(LIFECYCLE))}</p>',
                    unsafe_allow_html=True,
                )
                primary_action("Find a job", "pages/2_Job_Search.py", "tracker_empty_find")
        with side:
            st.markdown('<div class="jc-aside"><h3>Next actions</h3><p>Give each application a next step and a due '
                        "date. Anything due shows up first on Home and under Needs action here.</p></div>",
                        unsafe_allow_html=True)
        return

    today = date.today()
    submissions = {t.application_id: service.applications_db.get_submission(t.application_id) for t in trackers}
    histories = {t.application_id: status_tracker.get_status_history(t.application_id) for t in trackers}
    rows = [build_row(t, submissions[t.application_id], histories[t.application_id]) for t in trackers]
    counts = view_counts(rows, today)

    main, side = st.columns([2.2, 1], gap="large")
    with side:
        _weekly_panel(rows, owner_id)
    with main:
        _email_panel(status_tracker, rows)
        if "tracker_view" not in st.session_state:
            st.session_state["tracker_view"] = default_view(counts)
        view = st.radio(
            "Saved view", VIEWS, horizontal=True, key="tracker_view",
            format_func=lambda v: f"{v} ({counts[v]})",
        )
        search = st.text_input("Search company or role", key="tracker_search", placeholder="Type to filter")
        shown = [r for r in sort_rows(rows) if in_view(r, view, today)]
        if search.strip():
            needle = search.strip().lower()
            shown = [r for r in shown if needle in r.company.lower() or needle in r.role.lower()]
        if not shown:
            st.info("Nothing in this view." if not search else "No applications match that search.")
            return
        with st.container(key="tracker_table"):
            st.dataframe([r.as_table() for r in shown], use_container_width=True, hide_index=True)
        with st.container(key="tracker_cards"):
            # Phones: readable summaries instead of a wide table (CSS shows one or the other).
            st.markdown("".join(
                f'<div class="jc-row"><strong>{escape(r.role)}</strong><br><span class="jc-meta">'
                f'{escape(r.company)} · {escape(STATUS_WORDS.get(r.status, r.status.value))}'
                f'{" · next: " + escape(r.next_action) if r.next_action else ""}'
                f'{" · due " + r.due.isoformat() if r.due else ""}</span></div>' for r in shown),
                unsafe_allow_html=True)

        labels = {r.application_id: f"{r.role} at {r.company} · {STATUS_WORDS.get(r.status, r.status.value)}" for r in shown}
        application_id = st.selectbox("Open an application", list(labels), format_func=labels.get, key="tracker_selected")
    row = next(r for r in rows if r.application_id == application_id)
    submission = submissions.get(application_id)
    _render_detail(st, service, status_tracker, row, submission, histories[application_id], chip, PENDING_TAILOR_JOB_KEY)


def _render_detail(st, service, status_tracker, row, submission, history, chip, pending_key) -> None:
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    st.markdown("### " + escape(f"{row.role} at {row.company}"))
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        job = (submission.job_snapshot if submission else {}) or {}
        salary = "No salary stated"
        if job.get("salary_min") or job.get("salary_max"):
            salary = f"${(job.get('salary_min') or 0):,} – ${(job.get('salary_max') or 0):,}"
        facts = [
            ("Status", STATUS_WORDS.get(row.status, row.status.value)),
            ("Applied", row.applied.isoformat() if row.applied else "Not yet"),
            ("Candidate fit when you applied", row.fit),
            ("Resume used", row.resume_version),
            ("Mode", row.mode),
            ("Location", job.get("location") or "Not recorded"),
            ("Salary", salary),
            ("Confirmation number", (submission.confirmation_number if submission else "") or "None recorded"),
        ]
        table = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in facts)
        st.markdown(f'<table class="jc-table">{table}</table>', unsafe_allow_html=True)
        st.caption("This is what was true when the application was recorded; later edits don't change it.")
        answers = (submission.custom_answers if submission else {}) or {}
        with st.expander(f"Answers used ({len(answers)})"):
            if answers:
                for question, answer in answers.items():
                    st.markdown(f"- **{escape(question)}** {escape(answer)}")
            else:
                st.caption("No saved answers were used for this application.")
        with st.expander("Status history", expanded=True):
            for event in sorted(history, key=lambda e: e.status_updated, reverse=True):
                who = {"user": "you", "system": "Job Copilot", "email_integration": "you, from an email"}.get(
                    event.source.value, event.source.value.replace("_", " "))
                note = f" · {event.notes}" if event.notes else ""
                st.markdown(
                    f'<div class="jc-meta">{event.status_updated:%b %d, %Y %H:%M} · '
                    f"{escape(STATUS_WORDS.get(event.status, event.status.value))} · set by {escape(who)}{escape(note)}</div>",
                    unsafe_allow_html=True,
                )
        c1, c2 = st.columns(2)
        if row.url:
            c1.link_button("Open employer page", row.url, use_container_width=True)
        if c2.button("Tailor again for this job", use_container_width=True, key="tracker_retailor"):
            st.session_state[pending_key] = {
                "job_id": submission.job_posting_id if submission else "", "title": row.role,
                "company": row.company, "url": row.url, "candidate_fit": (submission.candidate_fit_snapshot or {}) if submission else {},
                "description": (service.db.get_job_posting(submission.job_posting_id).description
                                if submission and service.db.get_job_posting(submission.job_posting_id) else ""),
            }
            st.switch_page("pages/5_Tailor.py")
    with right:
        st.markdown("#### Next action")
        if submission:
            next_action = st.text_input("What's next", value=submission.next_action, key="tracker_next_action",
                                        placeholder="e.g. Email the recruiter")
            due_value = None
            if submission.next_action_due:
                try:
                    due_value = date.fromisoformat(submission.next_action_due[:10])
                except ValueError:
                    due_value = None
            due = st.date_input("Due", value=due_value, key="tracker_due", format="YYYY-MM-DD")
            notes = st.text_area("Notes", value=submission.next_action_notes, key="tracker_next_action_notes", height=80)
            if st.button("Save next action", key="tracker_save_next"):
                service.applications_db.update_next_action(
                    row.application_id, next_action, due.isoformat() if due else None, notes
                )
                st.toast("Next action saved.")
                st.rerun()
        st.markdown("#### Move status")
        order = [s for s in STATUS_WORDS if s is not ApplicationStatus.UNKNOWN]
        selected = st.selectbox("New status", order, index=order.index(row.status) if row.status in order else 0,
                                format_func=STATUS_WORDS.get, key="tracker_status")
        note = st.text_input("Note (optional)", key="tracker_status_note")
        if st.button("Save status", type="primary", key="tracker_save_status", disabled=selected == row.status):
            status_tracker.update_status(row.application_id, selected, note, source=StatusSource.USER)
            st.toast(f"Moved to {STATUS_WORDS[selected]}.")
            st.rerun()


def preview_token(
    job_id: str, resume_pdf_path: str, profile, mode: ApplicationMode, answers: dict | None = None
) -> str:
    """Identifies exactly what a preview approved: the job, the resume file's
    bytes, the profile version, the mode and the approved answers. Any change
    requires a new preview."""
    import hashlib
    import json
    import os

    from resume_tailorer.job_search.job_service import _profile_hash

    resume_id = resume_pdf_path or ""
    if resume_pdf_path and os.path.isfile(resume_pdf_path):
        with open(resume_pdf_path, "rb") as f:
            resume_id = hashlib.sha256(f.read()).hexdigest()
    parts = [job_id or "", resume_id, _profile_hash(profile) if profile else "", mode.value,
             sorted((answers or {}).items())]
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()
