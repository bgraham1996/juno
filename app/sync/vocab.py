"""Converters between plain-text dev values and the emoji labels the vault shows.

Dev files keep plain words (`"cycle": "active"`); notes show `Cycle: 🟢 Active`.
Each `Codec` works in both directions. To change or extend a vocabulary, edit the
dict below — nothing else needs to know.
"""

from __future__ import annotations

_VARIATION_SELECTOR = "️"  # emoji are sometimes stored with it, sometimes without


def _fold(shown: str) -> str:
    return shown.replace(_VARIATION_SELECTOR, "").strip().casefold()


class Codec:
    """A two-way plain <-> vault mapping. Unknown values pass through unchanged."""

    def __init__(self, pairs: dict[str, str] | None = None) -> None:
        pairs = pairs or {}
        self._to_vault = {plain.casefold(): shown for plain, shown in pairs.items()}
        self._to_dev = {_fold(shown): plain for plain, shown in pairs.items()}

    def to_vault(self, plain: str | None) -> str | None:
        if plain is None:
            return None
        return self._to_vault.get(plain.strip().casefold(), plain.strip())

    def to_dev(self, shown: str | None) -> str | None:
        if shown is None:
            return None
        return self._to_dev.get(_fold(shown), shown.strip())

    def knows(self, plain: str) -> bool:
        """True if `plain` is part of this vocabulary (always true for a pass-through codec)."""
        return not self._to_vault or plain.strip().casefold() in self._to_vault


PLAIN = Codec()  # no conversion

# The vault's existing `ProjectType` values.
PROJECT_TYPE = Codec(
    {
        "dev": "🔹 Dev",
        "organiser": "🌐 Organiser",
        "log": "🗃️ Log",
    }
)

# Dev `cycle` -> the note's `Cycle` property. Starter set.
CYCLE = Codec(
    {
        "idea": "💡 Idea",
        "active": "🟢 Active",
        "paused": "⏸️ Paused",
        "template": "🧩 Template",
        "archived": "📦 Archived",
    }
)
