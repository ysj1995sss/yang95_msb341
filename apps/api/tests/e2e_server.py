"""The workspace API for the browser tests (apps/web/e2e). Job boards, the writing model and
the PDF converter are stand-ins, so the tests are fast, offline and repeatable. Never used
in production.

    python tests/e2e_server.py <data-dir> <port>
"""

import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parents[3] / "product")]


BOARD = {"jobs": [
    {"id": 101 + i, "title": title, "absolute_url": f"https://job-boards.greenhouse.io/acme/jobs/{101 + i}",
     "location": {"name": "Remote, US"}, "updated_at": "2026-09-20T12:00:00-00:00",
     "content": ("&lt;p&gt;Requirements: SQL, Tableau and dashboard reporting for business partners. "
                 "3+ years of analytics experience.&lt;/p&gt;")}
    for i, title in enumerate(["Senior Data Analyst", "Data Analyst, Growth", "Account Executive"])
]}


class StubModel:
    """Rewrites the dashboards bullet; keeps everything else."""

    def __init__(self, settings=None):
        pass

    def complete(self, system, user, max_tokens=2000):
        found = re.search(r'\[\s*\{\s*"paragraph_index"', user)
        if not found:
            return "[]"
        bullets, _ = json.JSONDecoder().raw_decode(user[found.start():])
        edits = [{"paragraph_index": b["paragraph_index"], "change": "keep", "new_text": ""} for b in bullets]
        for edit, bullet in zip(edits, bullets):
            if bullet["text"].startswith("Built SQL dashboards"):
                edit.update(change="rewrite",
                            new_text="Built SQL reporting dashboards used by 40 managers across regional sales teams")
        return json.dumps(edits)


def fake_pdf(docx_path: str, pdf_path: str) -> None:
    """A real PDF of the Word file's text, without an office suite."""
    from docx import Document
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(pdf_path, pagesize=letter)
    y = 750
    for paragraph in Document(docx_path).paragraphs:
        pdf.drawString(54, y, paragraph.text[:110])
        y -= 16
    pdf.save()


if __name__ == "__main__":
    data_dir, port = sys.argv[1], int(sys.argv[2])
    # Set before anything imports litellm: litellm loads the first .env it finds above its own
    # install folder (e.g. one in the home folder for another project) without overriding values
    # already set, so these win.
    os.environ.update(JOB_COPILOT_DATA_DIR=data_dir, JOB_COPILOT_PREFETCH="0", LLM_MODEL="stub/model",
                      LLM_API_KEY="stub-key", LLM_FALLBACK_MODELS="none", LEGACY_ROUTES="false",
                      DATABASE_URL=f"sqlite+pysqlite:///{Path(data_dir).as_posix()}/legacy.db")
    os.environ.pop("WORKSPACE_TOKEN_SECRET", None)

    import logging

    import uvicorn

    logging.getLogger("job_copilot").setLevel(logging.WARNING)  # keep the test output readable

    from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
    from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: BOARD if token == "gitlab" else {"jobs": []}), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []), \
         patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}), \
         patch.object(SmartRecruitersScraper, "_make_get_request", lambda self, url, timeout=10: {"content": [], "totalFound": 0}), \
         patch("resume_tailorer.llm.client.LLMClient", StubModel), \
         patch("resume_tailorer.docx_export.pipeline.convert_docx_to_pdf", fake_pdf), \
         patch("app.workspace.tailor_router._load_local_env", lambda: None):
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")
