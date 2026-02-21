"""Persistente Speicherung für Kaffeemaschinen-Bezüge."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class KaffeemaschineSpeicher:
    """Verwaltet die persistente Speicherung der Kaffeemaschinen-Daten."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Speicher initialisieren."""
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}"
        )
        self._daten: dict[str, Any] = {"eintraege": []}

    async def async_load(self) -> None:
        """Gespeicherte Daten laden."""
        gespeichert = await self._store.async_load()
        if gespeichert is not None:
            self._daten = gespeichert
        else:
            self._daten = {"eintraege": []}

    async def async_add_eintrag(self, eintrag: dict, max_eintraege: int) -> None:
        """Neuen Bezug hinzufügen und Limit einhalten."""
        eintraege: list = self._daten.setdefault("eintraege", [])
        eintraege.append(eintrag)
        if len(eintraege) > max_eintraege:
            self._daten["eintraege"] = eintraege[-max_eintraege:]
        await self._store.async_save(self._daten)

    def get_eintraege(self) -> list[dict]:
        """Alle gespeicherten Bezüge zurückgeben."""
        return list(self._daten.get("eintraege", []))

    async def async_clear(self) -> None:
        """Alle gespeicherten Daten löschen."""
        self._daten = {"eintraege": []}
        await self._store.async_save(self._daten)
