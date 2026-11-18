"""The single table mapping a project field across both sides.

Every synced field is one row: the `ProjectRecord` attribute, its key in the dev
project's `metadata.json`, its property name in the note's frontmatter, the codec
that translates the value, and how dev -> vault may write it.

Note properties that are not in this table (Status, Priority, review dates, ...)
are never modified by the sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.sync.vocab import CYCLE, PLAIN, PROJECT_TYPE, Codec

# dev -> vault write policies
ALWAYS = "always"  # write whenever dev has a value and the note differs
FILL = "fill"      # write only when the note's value is blank
NEVER = "never"    # read-only in this direction


@dataclass(frozen=True)
class FieldSpec:
    attr: str
    dev_key: str | None    # key in metadata.json; None = not stored there
    vault_key: str | None  # frontmatter property; None = not stored there
    codec: Codec = PLAIN
    to_vault: str = ALWAYS


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("code", "projectCode", "ProjectCode", to_vault=FILL),
    FieldSpec("project_type", None, "ProjectType", PROJECT_TYPE),
    FieldSpec("cycle", "cycle", "Cycle", CYCLE),
    FieldSpec("dev_path", None, "DevPath"),
    FieldSpec("obsidian_note", "obsidianNote", None, to_vault=NEVER),
)

BY_ATTR = {spec.attr: spec for spec in FIELDS}

# The vault's placeholder for "no project code yet" (from its Project Template).
UNASSIGNED = "UNASSIGNED"
