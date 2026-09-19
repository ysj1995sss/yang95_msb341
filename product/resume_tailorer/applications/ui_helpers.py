"""Pure formatting functions for the Applications dashboard UI.

No streamlit import here — kept separate so this logic is unit-testable,
matching the pattern in job_search/ui_helpers.py.
"""

from resume_tailorer.applications.models import ApplicationTracker


def format_application_for_display(tracker: ApplicationTracker) -> dict:
    """Format an ApplicationTracker into display-ready strings for a table row."""
    return {
        "Job Posting ID": tracker.job_posting_id,
        "Status": tracker.status.value.replace("_", " ").title(),
        "Last Updated": tracker.status_updated.strftime("%Y-%m-%d %H:%M"),
        "Notes": tracker.notes if tracker.notes else "—",
    }
