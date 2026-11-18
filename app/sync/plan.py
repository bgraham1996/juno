"""Work out what a sync would do. Pure: no file or process access.

`build_plan` pairs each dev project with a vault note and lists the frontmatter
changes needed, producing exactly one `Outcome` per dev project.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.sync.fields import ALWAYS, FIELDS, FILL, UNASSIGNED
from app.sync.models import ProjectRecord
from app.sync.vault import VaultNote

UPDATE = "update"        # linked; the note needs changes
UNCHANGED = "unchanged"  # linked; the note is already up to date
NO_NOTE = "no-note"      # has a project code, but no note carries it
NO_CODE = "no-code"      # nothing to link by
CONFLICT = "conflict"    # ambiguous or contradictory; never written


@dataclass
class FieldChange:
    key: str
    before: str
    after: str


@dataclass
class Outcome:
    record: ProjectRecord
    kind: str
    note: VaultNote | None = None
    changes: list[FieldChange] = field(default_factory=list)
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


def _note_ref(raw: str) -> str:
    """Normalise an `obsidianNote` value: strip [[ ]], an alias, a heading and `.md`."""
    ref = raw.strip()
    if ref.startswith("[[") and ref.endswith("]]"):
        ref = ref[2:-2]
    ref = ref.split("|", 1)[0].split("#", 1)[0].strip()
    return ref[:-3] if ref.casefold().endswith(".md") else ref


def _resolve(record: ProjectRecord, notes: list[VaultNote]) -> tuple[VaultNote | None, str, str]:
    """(note, kind, reason) — kind is '' when a note was found."""
    if record.obsidian_note:
        ref = _note_ref(record.obsidian_note).casefold()
        key = (lambda n: n.rel.casefold()) if "/" in ref else (lambda n: n.name.casefold())
        hits = [n for n in notes if key(n) == ref]
        if not hits:
            return None, CONFLICT, f"obsidianNote {record.obsidian_note!r} is not a project note in the vault"
        if len(hits) > 1:
            return None, CONFLICT, f"obsidianNote {record.obsidian_note!r} matches {len(hits)} notes"
        note = hits[0]
        if record.code and note.record.code and note.record.code != record.code:
            return None, CONFLICT, (
                f"obsidianNote points at {note.name!r}, whose ProjectCode is "
                f"{note.record.code}, not {record.code}"
            )
        return note, "", ""

    if not record.code:
        return None, NO_CODE, ""
    hits = [n for n in notes if n.record.code == record.code]
    if not hits:
        return None, NO_NOTE, ""
    if len(hits) > 1:
        names = ", ".join(repr(n.name) for n in hits)
        return None, CONFLICT, f"{len(hits)} notes share ProjectCode {record.code}: {names}"
    return hits[0], "", ""


def _diff(record: ProjectRecord, note: VaultNote) -> tuple[list[FieldChange], list[str], str]:
    """(changes, warnings, blocking_reason)"""
    changes: list[FieldChange] = []
    warnings: list[str] = []
    for spec in FIELDS:
        if spec.vault_key is None or spec.to_vault not in (ALWAYS, FILL):
            continue
        value = getattr(record, spec.attr)
        if value is None:
            continue  # dev doesn't say: never clear the note's value
        if not spec.codec.knows(value):
            warnings.append(f"{spec.attr} {value!r} has no emoji mapping; written as plain text")
        after = spec.codec.to_vault(value)
        before = note.properties.get(spec.vault_key, "")
        if spec.vault_key in note.block_keys:
            return [], warnings, f"{spec.vault_key} is a multi-line value in the note"
        if spec.to_vault == FILL and before.strip() and before.strip().upper() != UNASSIGNED:
            continue
        if before != after:
            changes.append(FieldChange(spec.vault_key, before, after))
    return changes, warnings, ""


def build_plan(records: list[ProjectRecord], notes: list[VaultNote]) -> list[Outcome]:
    outcomes: list[Outcome] = []
    claimed: dict[str, list[Outcome]] = defaultdict(list)

    for record in records:
        note, kind, reason = _resolve(record, notes)
        outcome = Outcome(record=record, kind=kind, note=note, reason=reason,
                          warnings=list(record.issues))
        outcomes.append(outcome)
        if note is not None:
            claimed[note.rel].append(outcome)

    for claimants in claimed.values():
        if len(claimants) > 1:
            for outcome in claimants:
                others = ", ".join(o.record.name for o in claimants if o is not outcome)
                outcome.kind = CONFLICT
                outcome.reason = f"note {outcome.note.name!r} is also claimed by: {others}"
            continue
        outcome = claimants[0]
        changes, warnings, blocked = _diff(outcome.record, outcome.note)
        outcome.warnings += warnings
        if blocked:
            outcome.kind, outcome.reason = CONFLICT, blocked
        else:
            outcome.changes = changes
            outcome.kind = UPDATE if changes else UNCHANGED
    return outcomes
