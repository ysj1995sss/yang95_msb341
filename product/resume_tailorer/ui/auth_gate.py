"""Streamlit wiring for resume_tailorer.identity: sign-in gate and per-user services."""

from __future__ import annotations

from resume_tailorer.identity import (
    Identity,
    applications_db_path,
    job_db_path,
    resolve_identity,
)

OWNER_KEY = "owner_id"


def _auth_config() -> dict:
    import streamlit as st

    try:
        return dict(st.secrets.get("auth") or {})
    except Exception:
        return {}


def require_identity() -> Identity:
    """Stop the page with a sign-in screen until the visitor is identified."""
    import streamlit as st

    from resume_tailorer.code_freshness import code_changed_on_disk, drop_stale_modules

    if code_changed_on_disk():
        # A new version was deployed. Objects in this session belong to the old code, and
        # everything that matters (profile, chosen job, tailored resume, review) is on disk.
        drop_stale_modules()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    auth = _auth_config()
    user_info = dict(st.user) if auth else {}
    identity = resolve_identity(bool(auth), user_info)
    if identity is None:
        st.title("Job Copilot")
        st.write("Sign in to keep your resumes, jobs and applications private to you.")
        provider = "google" if "google" in auth else None
        st.button("Sign in with Google", type="primary", on_click=st.login, args=(provider,) if provider else ())
        st.stop()

    if st.session_state.get(OWNER_KEY) not in (None, identity.owner_id):
        # A different account in the same browser session: drop the previous one's state.
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    st.session_state[OWNER_KEY] = identity.owner_id

    st.session_state["identity_view"] = {"signed_in": identity.signed_in, "name": identity.display_name}
    try:
        from resume_tailorer.profile_import import load_into_session

        load_into_session(st.session_state, identity.owner_id)
        st.session_state.pop("profile_load_error", None)
    except Exception as exc:  # a damaged profile file must not lock the user out
        st.session_state["profile_load_error"] = str(exc)
    try:
        from resume_tailorer.active_job import restore_handoff, restore_pending_job
        from resume_tailorer.session_profile import get_career_profile

        service = job_service_for(identity.owner_id)
        restore_pending_job(st.session_state, st.session_state.get("profile_record"), service.db,
                            service.fit_scorer, get_career_profile(st.session_state))
        restore_handoff(st.session_state, st.session_state.get("profile_record"))
        service.warm_up()  # live job boards download while the user reads; searches then hit the cache
    except Exception:  # the chosen job is a convenience; never block a page on it
        pass
    return identity


def job_service_for(owner_id: str):
    """This owner's JobService, reused across reruns of the same session."""
    import streamlit as st

    from resume_tailorer.job_search.job_service import JobService

    service = st.session_state.get("job_service")
    # Rebuild when the class was reloaded (Streamlit's dev server re-imports
    # edited modules): a service from the old module would compare enums from
    # two different classes and quietly take the wrong branch (decision 021).
    if (
        service is None
        or type(service) is not JobService
        or st.session_state.get("job_service_owner") != owner_id
    ):
        service = JobService(
            db_path=job_db_path(owner_id),
            applications_db_path=applications_db_path(owner_id),
        )
        st.session_state["job_service"] = service
        st.session_state["job_service_owner"] = owner_id
    return service
