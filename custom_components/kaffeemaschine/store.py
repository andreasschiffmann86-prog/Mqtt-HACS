"""Persistente Datenspeicherung fuer die Kaffeemaschine Timeline."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import MAX_ENTRIES, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class KaffeeMaschineStore:
    """Verwaltet die persistente Speicherung der Timeline."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._entries: list[dict[str, Any]] = []

    async def async_load(self) -> list[dict[str, Any]]:
        data = await self._store.async_load()
        if data is None:
            self._entries = []
        else:
            self._entries = data.get("entries", [])
        _LOGGER.debug("Geladene Timeline-Eintraege: %d", len(self._entries))
        return self._entries

    async def async_add_entry(self, entry: dict[str, Any]) -> None:
        self._entries.append(entry)
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[-MAX_ENTRIES:]
        await self._store.async_save({"entries": self._entries})

    def get_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._entries[-limit:]))

    def get_today_count(self) -> int:
        today = datetime.now().date().isoformat()
        return sum(1 for e in self._entries if e.get("zeitstempel", "").startswith(today))

    def get_total_count(self) -> int:
        return len(self._entries)

    def get_count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._entries:
            name = entry.get("getraenk", "Unbekannt")
            counts[name] = counts.get(name, 0) + 1
        return counts

    def get_last_drink(self) -> dict[str, Any] | None:
        if not self._entries:
            return None
        return self._entries[-1]

    def get_favorite_drink(self) -> str:
        counts = self.get_count_by_type()
        if not counts:
            return "Kein Bezug"
        return max(counts, key=lambda k: counts[k])
