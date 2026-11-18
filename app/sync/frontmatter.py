"""Line-based reading and surgical updating of a note's YAML frontmatter.

Deliberately not a YAML round-trip: `update` rewrites only the lines for the keys
it is given and leaves every other byte of the note alone, so hand formatting,
unmanaged properties and the body survive untouched.

Only top-level `Key: value` scalars are understood. A key whose value spans
several lines (a block list, say) is reported by `block_keys` and refused by
`update`.
"""

from __future__ import annotations

import re

_KEY_RE = re.compile(r"^([A-Za-z_][\w \-]*?)\s*:(?:[ \t]+(.*))?$")
_NEEDS_QUOTES_START = tuple("~[]{}*&!|>'\"%@`#,?-:")


class FrontmatterError(ValueError):
    pass


def _bounds(lines: list[str]) -> tuple[int, int] | None:
    """(first, end) line indexes of the frontmatter body, or None if there is none."""
    if not lines or lines[0].lstrip("﻿").rstrip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return 1, i
    return None


def _entries(lines: list[str], first: int, end: int) -> list[tuple[str, int, int, str]]:
    """Top-level keys as (key, start_line, stop_line, inline_value); stop is exclusive."""
    found: list[tuple[str, int, int, str]] = []
    i = first
    while i < end:
        line = lines[i].rstrip("\r\n")
        match = None if line[:1] in (" ", "\t", "#", "-") else _KEY_RE.match(line)
        if not match:
            i += 1
            continue
        stop = i + 1
        while stop < end:
            nxt = lines[stop].rstrip("\r\n")
            if nxt.strip() and nxt[:1] not in (" ", "\t", "-"):
                break
            stop += 1
        # trailing blank lines belong to no key
        while stop > i + 1 and not lines[stop - 1].strip():
            stop -= 1
        found.append((match.group(1), i, stop, (match.group(2) or "").strip()))
        i = stop
    return found


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if value[0] == '"' else inner.replace("''", "'")
    return value


def _format(value: str) -> str:
    risky = (
        not value
        or value != value.strip()
        or value.startswith(_NEEDS_QUOTES_START)
        or ": " in value
        or " #" in value
        or value.endswith(":")
    )
    if not risky:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read(text: str) -> dict[str, str]:
    """Top-level scalar properties. Multi-line values come back as ''."""
    lines = text.splitlines(keepends=True)
    bounds = _bounds(lines)
    if bounds is None:
        return {}
    return {
        key: "" if stop - start > 1 else _unquote(value)
        for key, start, stop, value in _entries(lines, *bounds)
    }


def block_keys(text: str) -> set[str]:
    """Keys whose value spans more than one line (lists, nested maps, block text)."""
    lines = text.splitlines(keepends=True)
    bounds = _bounds(lines)
    if bounds is None:
        return set()
    return {key for key, start, stop, _ in _entries(lines, *bounds) if stop - start > 1}


def update(text: str, changes: dict[str, str]) -> str:
    """Return `text` with each key in `changes` set, touching only those lines.

    Existing keys are replaced in place; new keys are appended just before the
    closing `---`. Raises if the note has no frontmatter or a key is multi-line.
    """
    if not changes:
        return text
    lines = text.splitlines(keepends=True)
    bounds = _bounds(lines)
    if bounds is None:
        raise FrontmatterError("note has no frontmatter block")
    first, end = bounds
    newline = "\r\n" if lines[end].endswith("\r\n") else "\n"
    existing = {key: (start, stop) for key, start, stop, _ in _entries(lines, first, end)}

    appended: list[str] = []
    for key, value in changes.items():
        rendered = f"{key}: {_format(value)}{newline}"
        if key in existing:
            start, stop = existing[key]
            if stop - start > 1:
                raise FrontmatterError(f"{key} is a multi-line value; not overwriting it")
            lines[start] = rendered
        else:
            appended.append(rendered)
    return "".join(lines[:end] + appended + lines[end:])
