"""Run the workspace API on this computer for the web app (apps/web, `npm run dev`).

    python apps/api/scripts/run_local.py [data folder]

Local single-user mode (no sign-in). Data goes to the folder given, default
../job-copilot-local-data next to the repository, never into the repo. Model settings come from
product/.env (LLM_MODEL, LLM_API_KEY).
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
data = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO.parent / "job-copilot-local-data"
data.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("JOB_COPILOT_DATA_DIR", str(data))
os.environ.setdefault("LEGACY_ROUTES", "false")  # the web app needs only /v2, and no database
os.chdir(REPO / "apps" / "api")
sys.path[:0] = [str(REPO / "apps" / "api"), str(REPO / "product")]

import uvicorn  # noqa: E402

print(f"Job Copilot API on http://127.0.0.1:8000 (data: {data})")
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
