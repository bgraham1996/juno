"""Command bodies for the project commands in `main.py` (`projects`, `sync`).

Deliberately plain: gather, plan, print. Each returns a process exit code.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import config
from app.sync import dev, vault
from app.sync.plan import UPDATE, Outcome, build_plan
from app.sync.report import render
from tools import registry


def _plan(vault_override: str | None) -> tuple[Path, list[Outcome]] | None:
    root = config.vault_path(vault_override)
    if not root.is_dir():
        print(f"Vault not found: {root}", file=sys.stderr)
        return None
    try:
        rows = registry.list_projects()
    except registry.RegistryError as exc:
        print(exc, file=sys.stderr)
        return None
    notes = vault.load_notes(root, config.PROJECT_FOLDERS)
    return root, build_plan(dev.load_records(rows), notes)


def projects(vault_override: str | None = None) -> int:
    """Report how dev projects line up with vault project notes. Read-only."""
    planned = _plan(vault_override)
    if planned is None:
        return 1
    root, outcomes = planned
    print(f"Vault: {root}\n")
    print(render(outcomes))
    return 0


def sync(vault_override: str | None = None, apply: bool = False) -> int:
    """Push dev project fields into matching vault notes. Dry run unless `apply`."""
    planned = _plan(vault_override)
    if planned is None:
        return 1
    root, outcomes = planned
    print(f"Vault: {root}")
    print("Mode:  apply\n" if apply else "Mode:  dry run (nothing is written; pass --apply to write)\n")

    failed = 0
    if apply:
        for outcome in outcomes:
            if outcome.kind != UPDATE:
                continue
            try:
                vault.apply_update(outcome.note.path, {c.key: c.after for c in outcome.changes})
            except (OSError, ValueError) as exc:
                failed += 1
                print(f"FAILED {outcome.note.rel}: {exc}", file=sys.stderr)

    print(render(outcomes, show_changes=True, applied=apply))
    if failed:
        print(f"\n{failed} note(s) could not be written; see errors above.", file=sys.stderr)
    return 1 if failed else 0
