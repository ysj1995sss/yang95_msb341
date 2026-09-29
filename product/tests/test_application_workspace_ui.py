from resume_tailorer.applications.models import ATSCapability, ApplicationMode
from resume_tailorer.applications.streamlit_views import build_launchpad_state


UNPROVEN = ATSCapability(
    platform="greenhouse",
    manual_supported=True,
    assist_supported=True,
    final_submission=False,
    notes="Real submission is not verified.",
)


def test_unproven_platform_recommends_manual_and_disables_submit():
    state = build_launchpad_state(mode=ApplicationMode.ASSIST, capability=UNPROVEN)
    assert state.recommended_mode is ApplicationMode.MANUAL
    assert state.real_submit_enabled is False
    assert state.primary_action == "Open application"


def test_manual_mode_never_claims_automated_submission():
    state = build_launchpad_state(mode=ApplicationMode.MANUAL, capability=UNPROVEN)
    assert state.real_submit_enabled is False
    assert state.primary_action == "Open application"
    assert "reliable" in state.disclosure.lower()
    assert state.tracker_action == "Stage in tracker"
    assert state.success_message == "Application staged as Ready to apply."
