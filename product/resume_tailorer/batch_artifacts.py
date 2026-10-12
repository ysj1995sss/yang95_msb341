"""Private computation and short, execution-fenced canonical publication."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from resume_tailorer.review_store import save_review


@dataclass
class StagedReview:
    state: dict
    staging_dir: Path
    artifacts_dir: Path


def _absolute(path: Path) -> Path:
    path = Path(path).absolute()
    # Windows scratch/profile folders can exceed MAX_PATH after private staging is nested.
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        raw = str(path)
        return Path('\\\\?\\UNC\\' + raw[2:] if raw.startswith('\\\\') else '\\\\?\\' + raw)
    return path


def _contained_stage(folder: Path, stage: Path) -> Path:
    folder = _absolute(folder)
    root = folder / '.batch-staging'
    stage = _absolute(stage)
    if not stage.is_relative_to(root) or stage == root:
        raise ValueError('Invalid batch workspace.')
    for path in (stage, *stage.parents):
        if path == folder:
            break
        if path.is_symlink() or path.is_junction():
            raise ValueError('Batch workspace links are not allowed.')
    if not stage.resolve().is_relative_to(root.resolve()):
        raise ValueError('Batch workspace escapes its private folder.')
    return stage


def new_stage(artifacts_dir, execution, job_id) -> Path:
    if not re.fullmatch(r'[a-f0-9]{32}', execution):
        raise ValueError('Invalid batch execution.')
    folder = Path(artifacts_dir)
    stage = _contained_stage(folder, folder / '.batch-staging' / execution /
                             hashlib.sha256(job_id.encode()).hexdigest() / uuid.uuid4().hex)
    stage.mkdir(parents=True, exist_ok=False)
    mark_stage(stage, active=True)
    return stage


def mark_stage(stage: Path, *, active: bool) -> None:
    (stage / 'worker.json').write_text(json.dumps(dict(pid=os.getpid(), host=socket.gethostname(),
                                                     active=active, updated=time.time())), encoding='utf-8')


def publish_staged_review(job_id: str, result: StagedReview | None) -> None:
    if result is None:
        return
    _contained_stage(result.artifacts_dir, result.staging_dir)
    state = result.state
    # Immutable content first; only the atomic review replacement makes it current.
    pdf = state.get('pdf_bytes')
    if pdf and state['report'].validation.status.value != 'FAIL':
        folder = _absolute(result.artifacts_dir)
        folder.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(pdf).hexdigest()[:16] + '.pdf'
        target = folder / name
        if target.is_symlink() or target.is_junction():
            raise ValueError('Artifact links are not allowed.')
        if target.exists():
            if target.read_bytes() != pdf:
                raise RuntimeError('An existing artifact has different contents.')
        else:
            fd, tmp = tempfile.mkstemp(dir=folder, suffix='.tmp')
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(pdf)
                os.replace(tmp, target)
            finally:
                Path(tmp).unlink(missing_ok=True)
    if not save_review(str(result.artifacts_dir), job_id, state):
        raise RuntimeError('The review could not be saved. Your previous review is unchanged; continue to try again.')


def cleanup_staging(artifacts_dir: Path, *, now: float, retention_seconds: float) -> None:
    from resume_tailorer.batch_runner import _pid_alive, _read_batch_file

    root = _absolute(artifacts_dir) / '.batch-staging'
    if not root.exists() or root.is_symlink() or root.is_junction():
        return
    current = _read_batch_file(Path(artifacts_dir).parent) or {}
    for execution in root.iterdir():
        if execution.name == current.get('execution'):
            continue
        if execution.is_symlink() or execution.is_junction() or not execution.is_dir() or not re.fullmatch(r'[a-f0-9]{32}', execution.name):
            continue
        for job in execution.iterdir():
            if job.is_symlink() or job.is_junction() or not job.is_dir() or not re.fullmatch(r'[a-f0-9]{64}', job.name):
                continue
            for attempt in job.iterdir():
                try:
                    stage = _contained_stage(Path(artifacts_dir), attempt)
                    if not re.fullmatch(r'[a-f0-9]{32}', stage.name):
                        continue
                    meta = json.loads((stage / 'worker.json').read_text(encoding='utf-8'))
                    if now - float(meta['updated']) <= retention_seconds:
                        continue
                    if meta.get('active') and (meta.get('host') != socket.gethostname() or _pid_alive(int(meta['pid']))):
                        continue
                    # Never follow an unexpected nested link, even inside an otherwise owned stage.
                    if any(p.is_symlink() or p.is_junction() for p in stage.rglob('*')):
                        continue
                    shutil.rmtree(stage)
                except (OSError, ValueError, KeyError, TypeError):
                    continue
