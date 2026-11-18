"""Dev side: registry rows + each project's metadata.json -> ProjectRecord.

The registry says which projects exist and where their `metadata.json` is; the
fields it doesn't index (`projectCode`, `obsidianNote`) are read from that file
directly. Reading is defensive: a missing or malformed file yields a record with
no code, never an exception.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.sync.fields import FIELDS
from app.sync.models import ProjectRecord

# Vault template enforces 3-8; widened to 3-10 here (see wiki/design.md).
CODE_RE = re.compile(r"^[A-Z0-9]{3,10}$")

DEV_PROJECT_TYPE = "dev"  # everything the registry indexes is a dev project


def read_metadata(path: str | Path | None) -> dict:
    """The metadata.json object at `path`, or {} if absent, unreadable or not an object."""
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _text(value: object) -> str | None:
    """A non-empty stripped string, or None (bools and containers are rejected)."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    return str(value).strip() or None


def _short(path: str | None) -> str | None:
    """Abbreviate the home directory to `~` so the note isn't tied to a username."""
    if not path:
        return None
    home = str(Path.home())
    return "~" + path[len(home):] if path == home or path.startswith(home + "/") else path


def record_from_row(row: dict) -> ProjectRecord:
    meta = read_metadata(row.get("metadataPath"))
    path = _text(row.get("path"))
    record = ProjectRecord(
        name=_text(row.get("projectName")) or (Path(path).name if path else "?"),
        project_type=DEV_PROJECT_TYPE,
        dev_path=_short(path),
        version=_text(row.get("projectVersion")),
        tags=[str(t) for t in row.get("tags") or [] if isinstance(t, (str, int, float))],
    )
    for spec in FIELDS:
        if spec.dev_key is None:
            continue
        # metadata.json is fresher than the registry's last scan; fall back to the row.
        value = _text(meta.get(spec.dev_key)) or _text(row.get(spec.dev_key))
        if value is not None:
            setattr(record, spec.attr, value)

    if record.code is not None:
        code = record.code.upper()
        if CODE_RE.match(code):
            record.code = code
        else:
            record.issues.append(
                f"projectCode {record.code!r} is not 3-10 uppercase letters/digits; ignored"
            )
            record.code = None
    return record


def load_records(rows: list[dict]) -> list[ProjectRecord]:
    return [record_from_row(row) for row in rows]
