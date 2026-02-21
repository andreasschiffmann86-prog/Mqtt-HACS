"""Timeline management for Kaffeemaschine integration."""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .store import KaffeeMaschineStore

_LOGGER = logging.getLogger(__name__)


class KaffeeMaschineTimeline:
    """Manage coffee machine drink timeline."""

    def __init__(self) -> None:
        """Initialize the timeline."""
        self._store: KaffeeMaschineStore | None = None
        self._entries: list[dict[str, Any]] = []

    async def async_setup(self, hass: HomeAssistant) -> None:
        """Set up the timeline and load persisted data."""
        self._store = KaffeeMaschineStore(hass)
        self._entries = await self._store.async_load()

    async def add_entry(
        self,
        getraenk: str,
        menge_ml: int | None,
        temperatur: int | None,
        staerke: str | None,
        zeitstempel: str,
    ) -> None:
        """Add a new drink entry to the timeline."""
        entry: dict[str, Any] = {
            "getraenk": getraenk,
            "menge_ml": menge_ml,
            "temperatur": temperatur,
            "staerke": staerke,
            "zeitstempel": zeitstempel,
        }
        if self._store is not None:
            self._entries = await self._store.async_add_entry(entry)
        else:
            self._entries.append(entry)

    def get_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the last *limit* entries (most recent last)."""
        return self._entries[-limit:]

    def get_today_count(self) -> int:
        """Return the number of drink entries for today."""
        today = datetime.now().date().isoformat()
        return sum(
            1
            for e in self._entries
            if str(e.get("zeitstempel", "")).startswith(today)
        )

    def get_total_count(self) -> int:
        """Return the total number of drink entries."""
        return len(self._entries)

    def get_count_by_type(self) -> dict[str, int]:
        """Return a dict mapping drink name to count."""
        counter: Counter[str] = Counter(
            e.get("getraenk", "Unbekannt") for e in self._entries
        )
        return dict(counter)

    def get_last_drink(self) -> dict[str, Any] | None:
        """Return the most recent drink entry, or None if empty."""
        if not self._entries:
            return None
        return self._entries[-1]

    def get_favorite_drink(self) -> str | None:
        """Return the most frequently consumed drink type."""
        if not self._entries:
            return None
        counter: Counter[str] = Counter(
            e.get("getraenk", "Unbekannt") for e in self._entries
        )
        return counter.most_common(1)[0][0]
