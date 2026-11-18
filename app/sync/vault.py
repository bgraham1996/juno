"""Vault side: find project notes, read them as ProjectRecords, write updates.

A project note is a Markdown file under one of the configured project folders
whose `FileType` property says "project" and whose `ProjectType` is not a log.
This module is the only place that writes to the vault.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.sync import frontmatter
from app.sync.fields import FIELDS, UNASSIGNED
from app.sync.models import ProjectRecord


@dataclass
class VaultNote:
    path: Path
    rel: str                      # path inside the vault, without the .md suffix
    properties: dict[str, str]    # top-level frontmatter scalars, as written
    block_keys: set[str] = field(default_factory=set)
    record: ProjectRecord = None  # type: ignore[assignment]

    @property
    def name(self) -> str:
        return self.path.stem


def _is_project(properties: dict[str, str]) -> bool:
    if "project" not in properties.get("FileType", "").casefold():
        return False
    return "log" not in properties.get("ProjectType", "").casefold()


def _record(name: str, properties: dict[str, str]) -> ProjectRecord:
    record = ProjectRecord(name=name)
    for spec in FIELDS:
        if spec.vault_key is None:
            continue
        shown = properties.get(spec.vault_key, "").strip()
        if shown:
            setattr(record, spec.attr, spec.codec.to_dev(shown))
    if record.code is not None:
        record.code = record.code.upper()
        if record.code == UNASSIGNED:
            record.code = None
    return record


def load_notes(vault: Path, folders: tuple[str, ...]) -> list[VaultNote]:
    """Every project note under `folders`, sorted by path."""
    notes: list[VaultNote] = []
    for folder in folders:
        root = vault / folder
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            properties = frontmatter.read(text)
            if not _is_project(properties):
                continue
            notes.append(
                VaultNote(
                    path=path,
                    rel=path.relative_to(vault).with_suffix("").as_posix(),
                    properties=properties,
                    block_keys=frontmatter.block_keys(text),
                    record=_record(path.stem, properties),
                )
            )
    return notes


def apply_update(path: Path, changes: dict[str, str]) -> None:
    """Set `changes` in the note's frontmatter, replacing the file atomically.

    Re-reads the note at write time, so an edit made since planning is preserved.
    """
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    updated = frontmatter.update(text, changes)
    if updated == text:
        return
    temp = path.with_name(f".{path.name}.neo-juno.tmp")  # dotfile: Obsidian ignores it
    try:
        with open(temp, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
