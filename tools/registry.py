"""Plumbing for the `project-registry` CLI (see ~/dev/project-registry).

Shells out to the installed command and parses its JSON, which is the interface
that project documents as the most stable. Read-only: this never runs `scan`, so
the data is as fresh as the registry's last scan.

Each row is a dict with: id, path, projectName, projectVersion, branchName,
branchVersion, cycle, dirType, tags, notes, metadataPath, configPath, gitPath.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable

COMMAND = "project-registry"


class RegistryError(RuntimeError):
    """The registry could not be queried (not installed, not scanned, bad output)."""


def list_projects(runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> list[dict]:
    """Return every live project the registry knows about.

    `runner` is `subprocess.run` by default and exists so tests can substitute a fake.
    """
    try:
        done = runner([COMMAND, "list", "--json"], capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RegistryError(
            f"`{COMMAND}` is not on PATH. Install it with "
            "`uv tool install ~/dev/project-registry`."
        ) from exc

    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip()
        raise RegistryError(
            f"`{COMMAND} list` failed (exit {done.returncode}). "
            f"Has `{COMMAND} scan` been run?" + (f"\n{detail}" if detail else "")
        )

    try:
        rows = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"`{COMMAND} list --json` did not return JSON: {exc}") from exc
    if not isinstance(rows, list):
        raise RegistryError(f"`{COMMAND} list --json` returned {type(rows).__name__}, expected a list.")
    return [row for row in rows if isinstance(row, dict)]
