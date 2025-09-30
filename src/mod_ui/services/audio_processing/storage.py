"""Simple disk-backed storage for pedalboards.

This module stores pedalboards as JSON files under a data directory. It uses
atomic writes (temp file + rename) and provides list/load/delete helpers.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_DATA_DIR = os.getenv(
    "AUDIO_PROCESSING_DATA_DIR", os.path.join(os.getcwd(), "data", "audio_processing")
)


def _ensure_dir(dirpath: str) -> Path:
    p = Path(dirpath)
    p.mkdir(parents=True, exist_ok=True)
    (p / "pedalboards").mkdir(parents=True, exist_ok=True)
    return p


def save_pedalboard(
    pedalboard: Dict, pb_id: Optional[str] = None, data_dir: Optional[str] = None
) -> Tuple[str, str]:
    """Save a pedalboard dict to disk. Returns (id, path)."""
    dirpath = data_dir or DEFAULT_DATA_DIR
    base = _ensure_dir(dirpath) / "pedalboards"

    if pb_id is None:
        pb_id = uuid.uuid4().hex

    path = base / f"{pb_id}.json"
    tmp = base / f".{pb_id}.json.tmp"

    # Add saved metadata and schema version
    payload = dict(pedalboard)
    payload.setdefault("metadata", {})
    payload["metadata"]["saved_at"] = datetime.now().isoformat()
    # Add schema version to allow future migrations
    payload.setdefault("_schema_version", 1)

    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    # Atomic replace
    os.replace(str(tmp), str(path))

    return pb_id, str(path)


def list_pedalboards(data_dir: Optional[str] = None) -> List[Dict]:
    dirpath = data_dir or DEFAULT_DATA_DIR
    base = Path(dirpath) / "pedalboards"
    if not base.exists():
        return []

    out = []
    for p in sorted(base.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            out.append(
                {
                    "id": p.stem,
                    "path": str(p),
                    "metadata": payload.get("metadata", {}),
                    "name": payload.get("name"),
                }
            )
        except (json.JSONDecodeError, OSError):
            # best-effort: skip unreadable or invalid files
            continue

    return out


def load_pedalboard(pb_id: str, data_dir: Optional[str] = None) -> Optional[Dict]:
    dirpath = data_dir or DEFAULT_DATA_DIR
    path = Path(dirpath) / "pedalboards" / f"{pb_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    # Migrate if necessary (simple passthrough for schema v1)
    schema = payload.get("_schema_version", 1)
    if schema == 1:
        return payload
    # Future migrations would go here
    return payload


def export_pedalboard(
    pb_id: str, out_path: str, data_dir: Optional[str] = None
) -> bool:
    """Export a saved pedalboard to an external path (overwrites)."""
    payload = load_pedalboard(pb_id, data_dir=data_dir)
    if payload is None:
        return False
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return True


def import_pedalboard(
    file_path: str, data_dir: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    """Import a pedalboard JSON file into storage. Returns (id,path) or None on failure."""
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None

    # Generate id
    pb_id = uuid.uuid4().hex
    dirpath = data_dir or DEFAULT_DATA_DIR
    base = _ensure_dir(dirpath) / "pedalboards"
    path = base / f"{pb_id}.json"
    tmp = base / f".{pb_id}.json.tmp"

    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(path))
    return pb_id, str(path)


def delete_pedalboard(pb_id: str, data_dir: Optional[str] = None) -> bool:
    dirpath = data_dir or DEFAULT_DATA_DIR
    path = Path(dirpath) / "pedalboards" / f"{pb_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
