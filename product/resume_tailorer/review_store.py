"""The Tailor review (proposed changes, your decisions, the built resume), kept per job
so leaving mid-review loses nothing (decision 027). No Streamlit import.

Stored as readable JSON with explicit type tags, not pickle: a review file can be
inspected, moved or synced, and loading one can only rebuild this app's own
dataclasses and enums (classes under `resume_tailorer`), never run code. A file
that doesn't load (damaged, or from an incompatible version) is ignored.
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import hashlib
import importlib
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

FORMAT = 2  # 1 was pickle (never loaded any more)
_PACKAGE = "resume_tailorer."


def _path(folder: str, job_id: str) -> Path:
    name = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:20]
    return Path(folder) / "reviews" / f"{name}.json"


def _type_name(cls: type) -> str:
    return f"{cls.__module__}:{cls.__qualname__}"


def _type_from(name: str, kind: str) -> type:
    module_name, _, qualname = str(name).partition(":")
    if not module_name.startswith(_PACKAGE):
        raise ValueError(f"Refusing to load a type from outside the app: {name}")
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    if kind == "dataclass" and not (isinstance(obj, type) and dataclasses.is_dataclass(obj)):
        raise ValueError(f"Not a dataclass: {name}")
    if kind == "enum" and not (isinstance(obj, type) and issubclass(obj, enum.Enum)):
        raise ValueError(f"Not an enum: {name}")
    return obj


def encode(value: Any) -> Any:
    """A JSON-safe form of `value`, tagged so `decode` can rebuild the exact types."""
    if value is None or isinstance(value, (bool, int, float, str)) and not isinstance(value, enum.Enum):
        return value
    if isinstance(value, enum.Enum):
        return {"$enum": _type_name(type(value)), "value": encode(value.value)}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"$dataclass": _type_name(type(value)),
                "fields": {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}}
    if isinstance(value, (bytes, bytearray)):
        return {"$bytes": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, dict):
        return {"$dict": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, tuple):
        return {"$tuple": [encode(v) for v in value]}
    if isinstance(value, (set, frozenset)):
        return {"$set": [encode(v) for v in sorted(value, key=repr)]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    raise TypeError(f"Can't store a {type(value).__name__} in a review")


def decode(value: Any) -> Any:
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if "$enum" in value:
        return _type_from(value["$enum"], "enum")(decode(value["value"]))
    if "$dataclass" in value:
        cls = _type_from(value["$dataclass"], "dataclass")
        stored = {k: decode(v) for k, v in value["fields"].items()}
        fields = {f.name: f for f in dataclasses.fields(cls)}
        obj = cls(**{k: v for k, v in stored.items() if k in fields and fields[k].init})
        for k, v in stored.items():
            if k in fields and not fields[k].init:
                object.__setattr__(obj, k, v)
        return obj
    if "$bytes" in value:
        return base64.b64decode(value["$bytes"])
    if "$datetime" in value:
        return datetime.fromisoformat(value["$datetime"])
    if "$date" in value:
        return date.fromisoformat(value["$date"])
    if "$dict" in value:
        return {_hashable(decode(k)): decode(v) for k, v in value["$dict"]}
    if "$tuple" in value:
        return tuple(decode(v) for v in value["$tuple"])
    if "$set" in value:
        return {_hashable(decode(v)) for v in value["$set"]}
    raise ValueError(f"Unknown entry in a review file: {sorted(value)[:3]}")


def _hashable(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def signature(state: dict) -> tuple:
    """What changes when the user decides something; saving is skipped when it hasn't."""
    return (
        tuple(sorted((state.get("dispositions") or {}).items())),
        tuple(sorted(state.get("decided") or ())),
        tuple(sorted((state.get("manual_texts") or {}).items())),
        state.get("version"),
        state.get("reviewed"),
        state.get("dirty"),
    )


def save_review(folder: Optional[str], job_id: Optional[str], state: dict) -> bool:
    if not folder or not job_id or not state:
        return False
    try:
        text = json.dumps({"format": FORMAT, "job_id": job_id, "state": encode(state)})
    except (TypeError, ValueError):
        return False
    path = _path(folder, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def load_review(folder: Optional[str], job_id: Optional[str]) -> Optional[dict[str, Any]]:
    if not folder or not job_id:
        return None
    _remove_old_pickle(folder, job_id)
    path = _path(folder, job_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("format") != FORMAT or payload.get("job_id") != job_id:
            return None
        state = decode(payload.get("state"))
    except Exception:
        return None
    return state if isinstance(state, dict) and "changes" in state else None


def discard_review(folder: Optional[str], job_id: Optional[str]) -> None:
    if folder and job_id:
        _remove_old_pickle(folder, job_id)
        try:
            _path(folder, job_id).unlink()
        except OSError:
            pass


def _remove_old_pickle(folder: str, job_id: str) -> None:
    """Format 1 files were pickle. They are never loaded, only removed."""
    try:
        _path(folder, job_id).with_suffix(".review").unlink()
    except OSError:
        pass
