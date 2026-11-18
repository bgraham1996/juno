"""Plain-text rendering of a sync plan. Pure: outcomes in, string out."""

from __future__ import annotations

from app.sync.plan import CONFLICT, NO_CODE, NO_NOTE, UNCHANGED, UPDATE, Outcome


def _of(outcomes: list[Outcome], *kinds: str) -> list[Outcome]:
    return sorted((o for o in outcomes if o.kind in kinds), key=lambda o: o.record.name.casefold())


def _label(outcome: Outcome) -> str:
    record = outcome.record
    return f"{record.name}  ({record.dev_path})" if record.dev_path else record.name


def render(outcomes: list[Outcome], *, show_changes: bool = False, applied: bool = False) -> str:
    out: list[str] = []
    linked = _of(outcomes, UPDATE, UNCHANGED)
    conflicts = _of(outcomes, CONFLICT)
    no_note = _of(outcomes, NO_NOTE)
    no_code = _of(outcomes, NO_CODE)
    verb = "updated" if applied else "would update"

    out.append(f"Linked to a vault note ({len(linked)})")
    for o in linked:
        code = o.record.code or o.note.record.code or "no code"
        state = "up to date" if o.kind == UNCHANGED else f"{verb} {len(o.changes)} propert{'y' if len(o.changes) == 1 else 'ies'}"
        out.append(f"  {o.record.name}  [{code}]  ->  {o.note.rel}  ({state})")
        if show_changes:
            for change in o.changes:
                out.append(f"      {change.key}: {change.before or '(unset)'}  ->  {change.after}")
        for warning in o.warnings:
            out.append(f"      note: {warning}")
    if not linked:
        out.append("  (none)")

    if conflicts:
        out.append("")
        out.append(f"Conflicts, nothing written ({len(conflicts)})")
        for o in conflicts:
            out.append(f"  {_label(o)}")
            out.append(f"      {o.reason}")

    out.append("")
    out.append(f"Has a project code but no vault note ({len(no_note)})")
    for o in no_note:
        out.append(f"  {o.record.code}  {_label(o)}")
    if not no_note:
        out.append("  (none)")

    out.append("")
    out.append(f"No project code in metadata.json ({len(no_code)})")
    for o in no_code:
        out.append(f"  {_label(o)}")
        for warning in o.warnings:
            out.append(f"      note: {warning}")
    if not no_code:
        out.append("  (none)")

    updates = sum(1 for o in outcomes if o.kind == UPDATE)
    out.append("")
    out.append(
        f"{len(outcomes)} dev projects: {len(linked)} linked ({updates} {'changed' if applied else 'to change'}), "
        f"{len(conflicts)} conflicts, {len(no_note)} without a note, {len(no_code)} without a code."
    )
    return "\n".join(out)
