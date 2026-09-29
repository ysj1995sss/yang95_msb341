from resume_tailorer.ui.fact_vault import build_fact_vault_summary


PROFILE = {
    "skills": ["Python", "SQL"],
    "tools": ["Git"],
    "certifications": ["Cloud fundamentals"],
    "education": [{"degree": "BS"}],
    "work_experience": [
        {
            "responsibilities": ["Built reliable services"],
            "accomplishments": ["Reduced latency by 20%"],
        }
    ],
}


def test_summary_counts_verified_facts_and_user_edits():
    summary = build_fact_vault_summary(PROFILE, {"skills[0]": "user_verified"})
    assert summary.skill_count == len(PROFILE["skills"])
    assert summary.user_edit_count == 1
    assert summary.has_profile is True


def test_summary_counts_resume_bullets_and_unresolved_items():
    summary = build_fact_vault_summary(PROFILE, {"skills[0]": "user_verified"})
    assert summary.bullet_count == 2
    assert summary.resume_fact_count == 7
    assert summary.unresolved_count == 0


def test_empty_profile_has_a_clear_empty_state():
    summary = build_fact_vault_summary({}, {})
    assert summary.has_profile is False
    assert summary.next_action == "Upload a resume to build your Fact Vault."
