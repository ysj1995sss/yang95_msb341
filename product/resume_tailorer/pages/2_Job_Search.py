"""Jobs: which real role should I prepare an application for? (spec 008)

A stateful job browser. ui/jobs_state.py decides what the page shows from
saved goals, the latest search, the result list, the selection and the view,
never from widget state (Streamlit drops it when the user leaves the page).

Unchanged rules (decisions 010, 011, 020): real results only, honest source
labels, whole-word title matching, results scoped to the latest search run,
unknown salary/sponsorship/fit named as unknown. "Prepare this application"
records the APPLY triage, hands the exact posting and fit snapshot to Tailor,
and remembers the job across sessions.
"""

import re
from html import escape

import streamlit as st

from resume_tailorer.active_job import remember
from resume_tailorer.analyzers.ats_keywords import check_keywords, profile_text
from resume_tailorer.job_search.job_attributes import (
    EMPLOYMENT_TYPE_OPTIONS,
    EXPERIENCE_LEVEL_OPTIONS,
    INDUSTRY_OPTIONS,
)
from resume_tailorer.job_search.job_quality import evaluate_job_quality
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY, JobService, build_tailor_snapshot
from resume_tailorer.job_search.models import JobSource, TriageAction, UserSelection
from resume_tailorer.job_search.ui_helpers import build_search_goals_from_form
from resume_tailorer.profile_import import RECORD_KEY, save_record
from resume_tailorer.session_profile import get_career_profile
from resume_tailorer.ui import chip, render_app_shell, render_page_header
from resume_tailorer.ui.auth_gate import OWNER_KEY, job_service_for, require_identity
from resume_tailorer.ui.job_view import build_detail, build_row, job_id_for
from resume_tailorer.ui.jobs_state import (
    SAVED_VIEW,
    VIEWS,
    JobsInputs,
    JobsState,
    goals_summary_line,
    order_jobs,
    resolve,
    searched_at_text,
)
from resume_tailorer.ui.onboarding import (
    WORK_MODE_LABELS,
    apply_goals_to_search_form,
    form_to_goals,
    save_goals,
    suggested_titles,
)

st.set_page_config(page_title="Jobs · Job Copilot", page_icon="\U0001F50D", layout="wide")

WORK_MODES = ["any", "remote", "hybrid", "onsite"]
LIVE_SOURCES = [JobSource.GREENHOUSE, JobSource.LEVER, JobSource.ASHBY]
DEMO_SOURCES = [JobSource.LINKEDIN, JobSource.INDEED, JobSource.HANDSHAKE]
SOURCE_LABELS = {
    JobSource.GREENHOUSE: "Greenhouse (live, 36 company boards)",
    JobSource.LEVER: "Lever (live, 8 company boards)",
    JobSource.ASHBY: "Ashby (live, 19 company boards)",
    JobSource.LINKEDIN: "LinkedIn (demo listings, not real jobs)",
    JobSource.INDEED: "Indeed (demo listings, not real jobs)",
    JobSource.HANDSHAKE: "Handshake (demo listings, not real jobs)",
}
_LABEL_TO_SOURCE = {v: k for k, v in SOURCE_LABELS.items()}

# Non-widget session keys: they survive leaving the page and coming back.
VIEW_KEY = "jobs_view_choice"
SELECTED_KEY = "selected_job_id"
EDITING_KEY = "jobs_editing"
PENDING_SEARCH_KEY = "jobs_pending_search"
LAST_FORM_KEY = "jobs_last_form"
SEARCHING_HTML = '<div class="jc-status action">Searching 63 company boards…{}</div>'


def _service() -> JobService:
    return job_service_for(st.session_state[OWNER_KEY])


def _record() -> dict:
    return st.session_state.get(RECORD_KEY) or {}


def _saved_goals() -> dict:
    prefs = _record().get("preferences") or {}
    if prefs.get("job_title"):
        return prefs
    return st.session_state.get(LAST_FORM_KEY) or {}


def _seed(widget_key: str, persist_key: str, default) -> None:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state.get(persist_key, default)


# --- search form -------------------------------------------------------------

def _use_suggestion(title: str) -> None:
    st.session_state["job_title"] = title


def _render_form(compact: bool) -> None:
    """The search form. Find matching jobs queues a search that runs at the end of this run."""
    apply_goals_to_search_form(st.session_state, _record())
    # Streamlit forgets widget values while the form is hidden; refill from the last search.
    for key, value in (st.session_state.get(LAST_FORM_KEY) or {}).items():
        if key != "max_salary" and value is not None:
            st.session_state.setdefault(key, value)
    st.session_state.setdefault("selected_sources", [SOURCE_LABELS[s] for s in LIVE_SOURCES])
    suggestions = suggested_titles(_record().get("profile"))
    if suggestions and not compact:
        st.caption("From your work history:")
        cols = st.columns(min(len(suggestions), 4))
        for col, title in zip(cols, suggestions):
            col.button(title, key=f"jobs_suggest_{title}", on_click=_use_suggestion, args=(title,),
                       use_container_width=True)
    c1, c2, c3 = st.columns([1.4, 1.2, 0.9])
    c1.text_input("Target role", key="job_title", placeholder="e.g. Product marketing manager")
    c2.text_input("Location", key="location", placeholder="City, state or country")
    c3.selectbox("Work mode", WORK_MODES, key="remote_preference", format_func=WORK_MODE_LABELS.get)
    with st.expander("More filters"):
        f1, f2 = st.columns(2)
        f1.multiselect("Level", EXPERIENCE_LEVEL_OPTIONS, key="experience_level")
        f2.multiselect("Industry", INDUSTRY_OPTIONS, key="industries")
        f1.number_input("Minimum salary (USD)", min_value=0, step=5000, key="min_salary")
        f2.multiselect("Job type", EMPLOYMENT_TYPE_OPTIONS, key="employment_type")
        f1.checkbox("I need visa sponsorship", key="sponsorship_required")
        f2.checkbox("I'm open to relocating", key="relocation_willing")
        f1.text_input("Only these companies (comma-separated)", key="target_companies")
        f2.text_input("Skip these companies (comma-separated)", key="exclude_companies")
        st.multiselect("Sources", [SOURCE_LABELS[s] for s in LIVE_SOURCES + DEMO_SOURCES], key="selected_sources",
                       help="Greenhouse, Lever and Ashby list real openings. Demo sources show sample listings only.")
    with st.container(horizontal=True):
        if st.button("Find matching jobs", type="primary", key="jobs_find"):
            _queue_search_from_form()
        if compact and st.button("Cancel", key="jobs_cancel_edit"):
            st.session_state[EDITING_KEY] = False
            st.rerun()


def _current_form() -> dict:
    keys = ("job_title", "location", "industries", "min_salary", "remote_preference", "experience_level",
            "employment_type", "sponsorship_required", "relocation_willing", "target_companies", "exclude_companies")
    form = {k: st.session_state.get(k) for k in keys}
    form["max_salary"] = 0
    form["min_salary"] = form.get("min_salary") or 0
    return form


def _queue_search_from_form() -> None:
    form = _current_form()
    if not (form.get("job_title") or "").strip():
        st.error("Add a target role to search, for example “Product marketing manager”.")
        return
    labels = st.session_state.get("selected_sources") or []
    sources = [_LABEL_TO_SOURCE[l] for l in labels if l in _LABEL_TO_SOURCE]
    if not sources:
        st.error("Choose at least one source under More filters.")
        return
    record = _record()
    if record.get("profile"):
        save_goals(record, form_to_goals(form))
        save_record(st.session_state, st.session_state[OWNER_KEY], record)
    # LAST_FORM_KEY changes only when the search finishes, so the header keeps describing
    # the results on screen while a new search runs.
    st.session_state[PENDING_SEARCH_KEY] = {"form": form, "sources": [s.value for s in sources]}
    st.session_state[EDITING_KEY] = False


def _queue_search_again() -> None:
    form = st.session_state.get(LAST_FORM_KEY) or dict(_saved_goals())
    st.session_state[PENDING_SEARCH_KEY] = {"form": dict(form, max_salary=0), "sources": [s.value for s in LIVE_SOURCES]}


def _run_pending_search(status_slot) -> None:
    request = st.session_state.pop(PENDING_SEARCH_KEY, None)
    if not request:
        return
    form = dict(request["form"])
    try:
        goals = build_search_goals_from_form(form)
    except ValueError as exc:
        status_slot.error(f"Check your search: {exc}")
        return
    status_slot.markdown(SEARCHING_HTML.format(""), unsafe_allow_html=True)
    try:
        summary = _service().search_and_store(goals, [JobSource(v) for v in request["sources"]])
    except Exception as exc:
        status_slot.error(f"The search didn't finish: {exc}. Your previous results are still here; try again.")
        return
    st.session_state.last_search_run = summary
    st.session_state.last_search_goals = goals
    st.session_state[LAST_FORM_KEY] = form
    st.session_state.pop(SELECTED_KEY, None)
    st.session_state.pop("w_jobs_selected", None)
    st.session_state[VIEW_KEY] = VIEWS[0]
    st.session_state.pop("w_jobs_view", None)
    st.rerun()


# --- results -----------------------------------------------------------------

def _load_jobs(view: str):
    service = _service()
    if view == SAVED_VIEW:
        return service.db.get_jobs_by_latest_action("save", limit=100)
    goals = st.session_state.get("last_search_goals")
    if goals is None:
        return []
    last_run = st.session_state.get("last_search_run")
    return service.get_available_jobs(goals, seen_since=last_run.started_at if last_run else None)


def _record_action(job, action: str, fit) -> None:
    job_id = job_id_for(job)
    try:
        _service().db.record_user_selection(UserSelection(job_posting_id=job_id, action=action))
    except Exception as exc:
        st.error(f"Couldn't save your choice: {exc}")
        return
    if action == TriageAction.APPLY.value:
        st.session_state[PENDING_TAILOR_JOB_KEY] = build_tailor_snapshot(job, fit)
        record = _record()
        remember(record, job_id)
        save_record(st.session_state, st.session_state[OWNER_KEY], record)
        st.switch_page("pages/5_Tailor.py")
    st.toast({"save": "Saved. Find it under Saved.", "pass": "Passed."}.get(action, "Saved."))
    st.rerun()


def _render_workspace_header(view_state, view_choice: str, count: int) -> None:
    goals = st.session_state.get(LAST_FORM_KEY) or _saved_goals()
    run = st.session_state.get("last_search_run")
    left, right = st.columns([3, 1.3])
    with left:
        st.markdown(f'<div class="jc-search-summary">{escape(goals_summary_line(goals))}</div>', unsafe_allow_html=True)
        if view_choice == SAVED_VIEW:
            meta = [f"{count} saved {'job' if count == 1 else 'jobs'}"]
        else:
            meta = [f"{count} matching {'role' if count == 1 else 'roles'}"] if run is not None else []
            meta.append(searched_at_text(getattr(run, "started_at", None)))
            meta.append(view_state.source_note)
        cls = "jc-warn-line" if view_state.partial_failure else "jc-meta"
        st.markdown(f'<div class="{cls}">{escape(" · ".join(m for m in meta if m))}</div>', unsafe_allow_html=True)
    with right:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Edit search", key="jobs_edit"):
                st.session_state[EDITING_KEY] = True
                st.rerun()
            if st.button("Search again", key="jobs_again",
                         disabled=not (st.session_state.get(LAST_FORM_KEY) or _saved_goals()).get("job_title")):
                _queue_search_again()


def _render_list(jobs, fits, actions, ids) -> None:
    labels, captions = {}, {}
    for job in jobs:
        job_id = job_id_for(job)
        row = build_row(job, fits.get(job_id), actions.get(job_id))
        label = _md_literal(row.title)
        # Identical titles (one role in several cities) must stay distinguishable to the radio,
        # or the highlighted row and the selected job can disagree. Zero-width spaces are invisible.
        while label in labels.values():
            label += "​"
        labels[job_id] = label
        bits = [row.company, row.location]
        if row.work_mode != "Work mode not stated":
            bits.append(row.work_mode)
        if row.salary != "No salary stated":
            bits.append(row.salary)
        bits += [row.fit, row.freshness]
        if row.status in ("Saved", "Passed", "Preparing application"):
            bits.append(row.status)
        if row.is_demo:
            bits.append("Demo listing")
        captions[job_id] = _md_literal(" · ".join(bits))
    current = st.session_state.get(SELECTED_KEY)
    if st.session_state.get("w_jobs_selected") not in ids:
        st.session_state["w_jobs_selected"] = current if current in ids else ids[0]
    with st.container(height=640, key="joblist"):
        chosen = st.radio("Jobs", list(ids), format_func=labels.get, captions=[captions[i] for i in ids],
                          key="w_jobs_selected", label_visibility="collapsed")
    st.session_state[SELECTED_KEY] = chosen


def _md_literal(text: str) -> str:
    """Text shown through Streamlit markdown as-is: no formatting, and "$" never starts maths."""
    return re.sub(r"([\\`*_{}\[\]<>#|$])", r"\\\1", text or "")


def _evidence_rows(lines, mark: str, tone: str) -> str:
    out = []
    for line in lines:
        if hasattr(line, "requirement"):
            body = (f"<strong>{escape(line.requirement)}</strong>"
                    f'<span class="jc-muted"> — {escape(line.evidence)}</span>')
        else:
            body = escape(line)
        out.append(f'<div class="jc-ev"><span class="jc-ev-mark {tone}" aria-hidden="true">{mark}</span>'
                   f"<div>{body}</div></div>")
    return "".join(out)


def _render_detail(job, fit, action, quality) -> None:
    detail = build_detail(job, fit, action, _record().get("authorization"), quality)
    row = detail.row
    with st.container(key="jobdetail"):
        fresh = row.freshness[0].lower() + row.freshness[1:] if row.freshness.startswith("Posted") else row.freshness
        meta = " · ".join(x for x in (row.company, row.location,
                                      "" if row.work_mode == "Work mode not stated" else row.work_mode, fresh) if x)
        st.markdown(
            f'<h2 class="jc-detail-title">{escape(row.title)}</h2>'
            f'<div class="jc-meta">{escape(meta)}</div>'
            f'<div class="jc-chiprow">{chip("Candidate fit " + row.fit.replace("Fit ", ""), row.fit_tone)}'
            f'{chip("Posting " + row.quality.lower(), row.quality_tone)}{chip(row.salary)}'
            f'{chip(row.source, "review" if row.is_demo else "")}'
            f'{chip(row.status) if row.status != "New" else ""}</div>',
            unsafe_allow_html=True,
        )
        with st.container(horizontal=True):
            if st.button("Prepare this application", type="primary", key=f"{row.job_id}_apply",
                         disabled=row.is_demo, help="Demo listings aren't real jobs." if row.is_demo else
                         "Opens Tailor with this job loaded. Nothing is submitted."):
                _record_action(job, TriageAction.APPLY.value, fit)
            if st.button("Save", key=f"detail_{row.job_id}_save"):
                _record_action(job, TriageAction.SAVE.value, fit)
            if st.button("Pass", key=f"detail_{row.job_id}_pass"):
                _record_action(job, TriageAction.PASS.value, fit)

        html = ""
        if detail.hard_gates:
            html += '<h3 class="jc-sec">Check before proceeding</h3>' + "".join(
                f'<div class="jc-status blocked">{escape(g)}</div>' for g in detail.hard_gates)
        html += f'<h3 class="jc-sec">Why this role may fit you</h3><p class="jc-meta">{escape(detail.summary)}</p>'
        if detail.strong:
            html += '<div class="jc-ev-group">Strong matches</div>' + _evidence_rows(detail.strong, "✓", "verified")
        if detail.partial:
            html += '<div class="jc-ev-group">Partial matches</div>' + _evidence_rows(detail.partial, "!", "review")
        if not detail.strong and not detail.partial:
            html += '<p class="jc-meta">No matching evidence found in your verified facts yet.</p>'
        html += '<div class="jc-ev-group">Missing from your background</div>'
        if detail.gaps:
            html += _evidence_rows(detail.gaps, "×", "blocked")
        elif fit is None or fit.overall_fit is None:
            html += '<p class="jc-meta">Not known yet: this needs your Career Profile to compare against.</p>'
        else:
            html += '<p class="jc-meta">Nothing genuinely missing against the stated requirements.</p>'

        if detail.unknowns:
            html += '<div class="jc-ev-group">Important unknowns</div>' + _evidence_rows(detail.unknowns, "–", "")
        st.markdown(html, unsafe_allow_html=True)
        st.caption("Missing items are never added to your resume. Candidate fit measures your background, "
                   "not how well a resume shows it.")

        _render_keywords(job)

        with st.expander("Read full posting"):
            st.markdown(_posting_markdown(job.description))
        if detail.url:
            st.link_button("Open the original posting", detail.url)
        if detail.fit_parts:
            with st.expander("How the fit score is made"):
                for name, value in detail.fit_parts:
                    st.markdown(f"- {name}: {value}")


def _posting_markdown(description: str) -> str:
    """The posting as readable text; markdown symbols in it are shown literally."""
    text = (description or "").strip() or "This posting has no description."
    return "  \n".join(_md_literal(line.strip()) for line in text.splitlines())


def _render_keywords(job) -> None:
    st.markdown('<h3 class="jc-sec">Key requirements and keywords</h3>', unsafe_allow_html=True)
    profile = get_career_profile(st.session_state)
    if profile is None:
        st.caption("Import your resume in Career Profile to see which terms it already covers.")
        return
    check = check_keywords(job.title + " " + (job.description or ""), profile_text(profile))
    html = f'<p class="jc-meta">{escape(check.summary)}</p>'
    if check.missing:
        html += '<div class="jc-ev-group">Not on your resume</div>' + "".join(chip(t, "blocked") for t in check.missing)
    if check.present:
        html += '<div class="jc-ev-group">Already on your resume</div>' + "".join(chip(t, "verified") for t in check.present)
    st.markdown(html, unsafe_allow_html=True)


# --- page states -------------------------------------------------------------

def _render_setup_card() -> None:
    main, side = st.columns([2.2, 1], gap="large")
    with main:
        with st.container(border=True):
            st.markdown('<h2 class="jc-card-title">Find a role worth preparing for</h2>'
                        '<p class="jc-meta">Live openings from 63 company boards on Greenhouse, Lever and Ashby.</p>',
                        unsafe_allow_html=True)
            _render_form(compact=False)
    with side:
        st.markdown(
            '<div class="jc-aside"><h3>What you get</h3>'
            "<p>Each role shows why it may fit you, what is genuinely missing, and what the posting doesn't say.</p>"
            "<p>Nothing is submitted from here. Choosing a role opens Tailor with the posting loaded.</p></div>",
            unsafe_allow_html=True,
        )


def _render_ready_card() -> None:
    goals = _saved_goals()
    main, side = st.columns([2.2, 1], gap="large")
    with main:
        with st.container(border=True):
            st.markdown(f'<div class="jc-eyebrow">Your search</div><div class="jc-search-summary">'
                        f"{escape(goals_summary_line(goals))}</div>"
                        '<p class="jc-meta">Live openings from 63 company boards on Greenhouse, Lever and Ashby.</p>',
                        unsafe_allow_html=True)
            with st.container(horizontal=True):
                if st.button("Find matching jobs", type="primary", key="jobs_find_saved"):
                    st.session_state[LAST_FORM_KEY] = dict(goals)
                    _queue_search_again()
                if st.button("Edit search", key="jobs_edit_saved"):
                    st.session_state[EDITING_KEY] = True
                    st.rerun()
        saved = _service().db.get_jobs_by_latest_action("save", limit=100)
        if saved and st.button(f"View {len(saved)} saved {'job' if len(saved) == 1 else 'jobs'}", key="jobs_open_saved"):
            st.session_state[VIEW_KEY] = SAVED_VIEW
            st.session_state.pop("w_jobs_view", None)
            st.rerun()
    with side:
        st.markdown(
            '<div class="jc-aside"><h3>What you get</h3>'
            "<p>Each role shows why it may fit you, what is genuinely missing, and what the posting doesn't say.</p>"
            "<p>Nothing is submitted from here. Choosing a role opens Tailor with the posting loaded.</p></div>",
            unsafe_allow_html=True,
        )


def _render_results(status_slot, has_goals: bool, searched: bool) -> None:
    service = _service()
    if "w_jobs_view" not in st.session_state:
        st.session_state["w_jobs_view"] = st.session_state.get(VIEW_KEY, VIEWS[0])
    view_choice = st.session_state.get("w_jobs_view") or VIEWS[0]
    try:
        jobs = _load_jobs(view_choice)
    except Exception as exc:
        st.error(f"Couldn't load jobs: {exc}. Search again to refresh them.")
        return
    ids_all = [job_id_for(j) for j in jobs]
    actions = service.db.get_latest_actions(ids_all) if ids_all else {}
    profile = get_career_profile(st.session_state)
    fits = service.fit_results_cached(profile, jobs, st.session_state.setdefault("fit_cache", {})) if profile and jobs else {}
    fit_scores = {k: (r.overall_fit if r else None) for k, r in fits.items()}
    jobs = order_jobs(jobs, view_choice, fit_scores, actions, job_id_for)
    ids = tuple(job_id_for(j) for j in jobs)
    run = st.session_state.get("last_search_run")
    statuses = tuple((p.source.value, p.status.value) for p in getattr(run, "providers", None) or [])
    view = resolve(JobsInputs(has_goals=has_goals, searched=searched,
                              search_requested=PENDING_SEARCH_KEY in st.session_state,
                              result_ids=ids, selected_id=st.session_state.get(SELECTED_KEY),
                              view=view_choice, provider_statuses=() if view_choice == SAVED_VIEW else statuses))
    if view.state is JobsState.SEARCHING:
        status_slot.markdown(SEARCHING_HTML.format(" Your current results stay here until the new ones arrive."),
                             unsafe_allow_html=True)

    _render_workspace_header(view, view_choice, len(ids))
    if not ids:
        chosen_view = st.segmented_control("Show", VIEWS, key="w_jobs_view", label_visibility="collapsed")
        st.session_state[VIEW_KEY] = chosen_view or VIEWS[0]
        with st.container(border=True):
            if view_choice == SAVED_VIEW:
                st.markdown("**No saved jobs yet.** Choose **Save** on a role to keep it here.")
            else:
                st.markdown("**No open postings matched this search.** Try a broader role name, another location, "
                            "or no work-mode preference.")
                if st.button("Edit search", type="primary", key="jobs_edit_empty"):
                    st.session_state[EDITING_KEY] = True
                    st.rerun()
        return

    list_col, detail_col = st.columns([1, 1.45], gap="medium")
    with list_col:
        chosen_view = st.segmented_control("Show", VIEWS, key="w_jobs_view", label_visibility="collapsed")
        st.session_state[VIEW_KEY] = chosen_view or VIEWS[0]
        _render_list(jobs, fits, actions, ids)
    selected = st.session_state.get(SELECTED_KEY)
    job = next((j for j in jobs if job_id_for(j) == selected), jobs[0])
    with detail_col:
        _render_detail(job, fits.get(job_id_for(job)), actions.get(job_id_for(job)), evaluate_job_quality(job))


def main():
    require_identity()
    render_app_shell("Jobs")
    render_page_header("Jobs", "Find a real role worth preparing an application for. Nothing is submitted from here.")
    status_slot = st.empty()

    searched = st.session_state.get("last_search_run") is not None
    has_goals = bool(_saved_goals().get("job_title"))
    editing = bool(st.session_state.get(EDITING_KEY))
    view_choice = st.session_state.get(VIEW_KEY, VIEWS[0])

    if editing:
        with st.container(border=True):
            st.markdown('<div class="jc-eyebrow">Edit search</div>', unsafe_allow_html=True)
            _render_form(compact=True)

    entry = resolve(JobsInputs(has_goals=has_goals, searched=searched,
                               search_requested=PENDING_SEARCH_KEY in st.session_state,
                               result_ids=(), selected_id=None, view=view_choice))
    if searched or view_choice == SAVED_VIEW:
        _render_results(status_slot, has_goals, searched)
    elif entry.state is JobsState.SEARCHING:
        status_slot.markdown(SEARCHING_HTML.format(""), unsafe_allow_html=True)
    elif not editing and entry.state is JobsState.NO_GOALS:
        _render_setup_card()
    elif not editing and entry.state is JobsState.READY_TO_SEARCH:
        _render_ready_card()
    _run_pending_search(status_slot)


main()
