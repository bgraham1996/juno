---
type: wiki
subtype: design
tags: [design, architecture]
---

# Design

*Engineering-facing design notes for neo-juno: architecture, decisions, process.*

## Project-management vault

Dev items are notes carrying `FileType: 🚥 Dev Item` frontmatter (create with the `dev-item`
template in `vault_infra/templates/`); the [[Dev Items]] Obsidian **Bases** board queries them
into Board / Backlog / By Bucket / By Cycle views.

## Dev project ↔ vault note sync

*Decided 2026-11-13. Code: `app/sync/`, `tools/registry.py`, `app/cli.py`.*

Links dev projects in `~/dev` to project notes in the Immrama vault
(`~/Vaults/Immrama/Immrama/Projects`).

### Decisions

- **The project code is the join key.** `projectCode` in a project's `metadata.json` matches
  `ProjectCode` in a note's frontmatter (3–8 uppercase letters/digits, the vault template's rule).
- **`obsidianNote` is an explicit, redundant link.** Optional in `metadata.json`; names the note
  (plain name, `[[wikilink]]`, or vault-relative path) and takes precedence over the code. It
  exists for the day several versions of one project need to point at different notes.
- **`project-registry` is discovery only.** `tools/registry.py` shells out to
  `project-registry list --json`. The registry does not index `projectCode`/`obsidianNote`, so
  `app/sync/dev.py` reads each project's `metadata.json` (via the registry's `metadataPath`)
  itself. If the registry later indexes them, only `dev.py` changes.
- **One-way for now: dev → vault, update-only.** The sync never creates notes; projects without a
  note are listed in the report.
- **`Status` is note maturity, not project state, and is never written.** Dev `cycle` goes to its
  own `Cycle` property.
- **Dev files stay plain text; the vault shows emoji.** `app/sync/vocab.py` holds two-way codecs.
  A value with no mapping is written as plain text and flagged, never dropped.
- **`ProjectType` separates dev projects from the rest** (an itinerary is a project note but not a
  dev project). Everything from the registry is written as `🔹 Dev`.
- **Dry run by default**; `--apply` writes.

### Field table (`app/sync/fields.py`)

| `metadata.json` | note property | dev → vault |
|---|---|---|
| `projectCode` | `ProjectCode` | fills only a blank / `UNASSIGNED` value |
| (constant `dev`) | `ProjectType` | written |
| `cycle` | `Cycle` | written when dev has a value |
| (registry `path`, `~`-shortened) | `DevPath` | written |
| `obsidianNote` | (the note itself) | not written |

A missing dev value never clears a note value. Properties outside this table and the note body
are never modified: `frontmatter.update` rewrites only the lines for the keys it is given.

### Outcomes (`app/sync/plan.py`)

One per dev project: `update`, `unchanged`, `no-note`, `no-code`, `conflict`. Conflicts are never
written: `obsidianNote` naming a missing or ambiguous note, or a note with a different code; two
notes sharing a code; two dev projects resolving to the same note; a managed property that is a
multi-line value in the note.

### Path to two-way

Both sides are already read into the same `ProjectRecord` in plain vocabulary, and the codecs and
field table work in both directions. Vault → dev needs: a `metadata.json` writer in `dev.py`, a
per-field direction/conflict policy in `fields.py`, and a direction flag on the command.

### Open

- Several dev directories for one project (`juno`, `juno-neo`, `neo-juno` → JUNO001) currently
  conflict if more than one claims the code. Needs a rule (primary version, or a list of paths).
- Tags are read on the dev side but not synced (the vault uses `ProjectTags`).
- The cycle vocabulary in `vocab.py` is a starter set.
