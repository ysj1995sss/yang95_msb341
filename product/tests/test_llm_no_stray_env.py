"""litellm must not load a .env that belongs to another project (decision 030)."""

import os
import subprocess
import sys
from pathlib import Path


def test_importing_the_client_ignores_a_stray_env_file(tmp_path):
    # litellm's load_dotenv() searches upward from litellm's own folder; a .env in the
    # working directory is the simplest stand-in that python-dotenv would also find.
    (tmp_path / ".env").write_text("JC_STRAY_ENV_PROBE=leaked\n", encoding="utf-8")
    product = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k not in ("LITELLM_MODE", "JC_STRAY_ENV_PROBE")}
    env["PYTHONPATH"] = str(product)
    code = ("import os, dotenv; dotenv.find_dotenv = lambda *a, **k: os.path.join(os.getcwd(), '.env');"
            "import resume_tailorer.llm.client;"
            "print(os.environ.get('LITELLM_MODE'), os.environ.get('JC_STRAY_ENV_PROBE'))")
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.split() == ["PRODUCTION", "None"]
