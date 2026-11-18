# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## neo-juno

organising tools for me

Python 3.13 managed with [`uv`](https://docs.astral.sh/uv/). Run from inside this directory:

```bash
uv sync             # create/refresh .venv and install deps
uv run main.py      # scaffold commands (doctor | add-lib | container | setup) + project commands below
uv run pytest       # run tests

uv run main.py projects        # read-only: how ~/dev projects map to Immrama project notes
uv run main.py sync            # dev -> vault sync, DRY RUN (prints planned frontmatter changes)
uv run main.py sync --apply    # actually writes to the vault — only when the user asks
```

`sync`/`projects` take `--vault PATH` (or `$NEO_JUNO_VAULT`); the default is
`~/Vaults/Immrama/Immrama`. Tests use `tmp_path` vaults and a fake registry — never point a test
at the real vault.

## Layout

- `tools/` — plumbing for external tools, one module per tool. `tools/registry.py` wraps the
  `project-registry` CLI (`list --json`); nothing else builds its command lines.
- `app/sync/` — the dev ↔ vault project sync (currently one-way, dev → vault, update-only).
  `fields.py` is the single field-mapping table and `vocab.py` the plain-text ↔ emoji converters;
  `plan.py` is pure (no I/O); `vault.py` is the only module that writes to the vault. Design and
  rules: `project/vault/wiki/design.md`.
- `app/cli.py` — bodies of the `projects`/`sync` commands; `main.py` only dispatches.
- `app/` — project code.
- `libs/` — reusable building blocks (add more with `uv run main.py add-lib <domain>`).
- `project/vault/` — the Obsidian project-management vault (dev-item board + docs/wiki/notes).
- `.bootstrap/` — scaffolder machinery kept out of the project's way (the `main.py` command
  surface dispatches into it). Not application code.

Follow the cascading conventions in `~/dev/CLAUDE.md` and `~/CLAUDE.md`.
