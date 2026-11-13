# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## neo-juno

organising tools for me

Python 3.13 managed with [`uv`](https://docs.astral.sh/uv/). Run from inside this directory:

```bash
uv sync             # create/refresh .venv and install deps
uv run main.py      # ongoing project commands (doctor | add-lib | container | setup)
uv run pytest       # run tests
```

## Layout

- `app/` — project code.
- `libs/` — reusable building blocks (add more with `uv run main.py add-lib <domain>`).
- `project/vault/` — the Obsidian project-management vault (dev-item board + docs/wiki/notes).
- `.bootstrap/` — scaffolder machinery kept out of the project's way (the `main.py` command
  surface dispatches into it). Not application code.

Follow the cascading conventions in `~/dev/CLAUDE.md` and `~/CLAUDE.md`.
