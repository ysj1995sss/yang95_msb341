"""Run the workspace API on this computer for the web app (apps/web, `npm run dev`).

    python apps/api/scripts/run_local.py [--codex] [--node-dir DIR] [data folder]

Local single-user mode (no sign-in). Data goes to the folder given, default
../job-copilot-local-data next to the repository, never into the repo. Model settings come from
product/.env (LLM_MODEL, LLM_API_KEY). With --codex, tailoring uses the Codex CLI signed in with
your ChatGPT plan instead (LLM_MODEL=codex-cli, decision 031; run `codex login` first). The Codex
CLI runs on Node.js; --node-dir adds a Node.js folder to PATH when it isn't there already.
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
argv = sys.argv[1:]
if "--node-dir" in argv:
    i = argv.index("--node-dir")
    node_dir = argv[i + 1]
    del argv[i:i + 2]
    os.environ["PATH"] = node_dir + os.pathsep + os.environ.get("PATH", "")
args = [a for a in argv if a != "--codex"]
if "--codex" in sys.argv[1:]:
    os.environ["LLM_MODEL"] = "codex-cli"  # set before product/.env is read, so it wins
    os.environ["LLM_FALLBACK_MODELS"] = "none"
    import shutil

    if shutil.which("node") is None:
        print("Warning: Node.js isn't on PATH, so the Codex CLI can't start. Pass --node-dir <folder with node.exe>.")
data = Path(args[0]) if args else REPO.parent / "job-copilot-local-data"
data.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("JOB_COPILOT_DATA_DIR", str(data))
os.environ.setdefault("LEGACY_ROUTES", "false")  # the web app needs only /v2, and no database
os.chdir(REPO / "apps" / "api")
sys.path[:0] = [str(REPO / "apps" / "api"), str(REPO / "product")]

import uvicorn  # noqa: E402

print(f"Job Copilot API on http://127.0.0.1:8000 (data: {data}; model: {os.environ.get('LLM_MODEL', 'from product/.env')})")
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
