import pytest

from resume_tailorer.artifacts.filenames import safe_artifact_filename


def test_safe_filename_is_deterministic_and_sanitized():
    assert safe_artifact_filename("ACME / Labs", "Strategy: Lead", 2, "pdf") == (
        "ACME_Labs_Strategy_Lead_Tailored_Resume_v2.pdf"
    )


def test_safe_filename_uses_honest_fallbacks():
    assert safe_artifact_filename("", "", 1, ".docx") == (
        "Target_Job_Tailored_Resume_v1.docx"
    )


@pytest.mark.parametrize("version", [0, -1])
def test_safe_filename_rejects_non_positive_versions(version):
    with pytest.raises(ValueError, match="positive"):
        safe_artifact_filename("ACME", "Analyst", version, "pdf")


def test_safe_filename_rejects_unsafe_extension():
    with pytest.raises(ValueError, match="extension"):
        safe_artifact_filename("ACME", "Analyst", 1, "../../exe")
