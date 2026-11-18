"""Where neo-juno looks for things. Defaults, with an environment override."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_VAULT = Path("~/Vaults/Immrama/Immrama")
VAULT_ENV = "NEO_JUNO_VAULT"

# Folders inside the vault that hold project notes, relative to the vault root.
PROJECT_FOLDERS = ("Projects",)


def vault_path(override: str | Path | None = None) -> Path:
    """The vault root: explicit override, else $NEO_JUNO_VAULT, else the default."""
    chosen = override or os.environ.get(VAULT_ENV) or DEFAULT_VAULT
    return Path(chosen).expanduser()
