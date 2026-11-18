"""The neutral project shape both sides are converted into."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectRecord:
    """One project, described in plain-text (dev-side) vocabulary.

    A dev directory and a vault note are both read into this shape, so the planner
    compares like with like. `None` means "this side doesn't say".
    """

    name: str
    code: str | None = None
    project_type: str | None = None
    cycle: str | None = None
    dev_path: str | None = None
    obsidian_note: str | None = None
    version: str | None = None
    tags: list[str] = field(default_factory=list)
    # Problems found while reading this record (e.g. a malformed project code).
    issues: list[str] = field(default_factory=list)
