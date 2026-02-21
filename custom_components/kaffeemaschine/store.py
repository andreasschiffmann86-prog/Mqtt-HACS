"""Persistent storage for Kaffeemaschine timeline entries."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import MAX_ENTRIES, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class KaffeeMaschineStore:
    """Handle persistent storage for the coffee machine timeline."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._entries: list[dict[str, Any]] = []

    async def async_load(self) -> list[dict[str, Any]]:
        """Load stored entries from disk."""
        data = await self._store.async_load()
        if data is None:
            self._entries = []
        else:
            self._entries = data.get("entries", [])
        return self._entries

    async def async_save(self, entries: list[dict[str, Any]]) -> None:
        """Save entries to disk."""
        self._entries = entries
        await self._store.async_save({"entries": entries})

    async def async_add_entry(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        """Add a new drink entry, enforcing the max-entries limit."""
        self._entries.append(entry)
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[-MAX_ENTRIES:]
        await self._store.async_save({"entries": self._entries})
        return self._entries
