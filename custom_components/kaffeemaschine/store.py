"""Persistente Speicherung für Kaffeemaschinen-Bezüge."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

MAX_ALERT_ENTRIES = 50


class KaffeemaschineSpeicher:
    """Verwaltet die persistente Speicherung der Kaffeemaschinen-Daten."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Speicher initialisieren."""
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}"
        )
        self._daten: dict[str, Any] = {"eintraege": [], "alerts": []}

    async def async_load(self) -> None:
        """Gespeicherte Daten laden."""
        gespeichert = await self._store.async_load()
        if gespeichert is not None:
            self._daten = gespeichert
            # Migration: alerts-Schlüssel für ältere Speicherstände ergänzen
            if "alerts" not in self._daten:
                self._daten["alerts"] = []
        else:
            self._daten = {"eintraege": [], "alerts": []}

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

    async def async_add_alert_raise(self, alert: dict) -> None:
        """Neuen Alert-Raise-Eintrag speichern."""
        alerts: list = self._daten.setdefault("alerts", [])
        # Doppelten RAISE für dieselbe alertId verhindern
        for existing in alerts:
            if existing.get("alertId") == alert.get("alertId") and existing.get("clearTime") is None:
                _LOGGER.debug("Alert %s bereits offen – ignoriere Duplikat.", alert.get("alertId"))
                return
        alerts.append(alert)
        # Auf MAX_ALERT_ENTRIES begrenzen (älteste zuerst entfernen)
        if len(alerts) > MAX_ALERT_ENTRIES:
            self._daten["alerts"] = alerts[-MAX_ALERT_ENTRIES:]
        await self._store.async_save(self._daten)

    async def async_add_alert_clear(self, alert_id: str, clear_time: str, message_id: str | None = None) -> bool:
        """Einen offenen Alert als geschlossen markieren. Gibt True zurück wenn gefunden."""
        alerts: list = self._daten.get("alerts", [])
        # Suche den jüngsten offenen Alert mit dieser alertId
        for alert in reversed(alerts):
            if alert.get("alertId") == alert_id and alert.get("clearTime") is None:
                alert["clearTime"] = clear_time
                if message_id:
                    alert["messageIdClear"] = message_id
                await self._store.async_save(self._daten)
                return True
        _LOGGER.warning("Alert-Clear empfangen, aber kein offener Alert mit ID %s gefunden.", alert_id)
        return False

    async def async_close_all_open_alerts(self, close_time: str) -> int:
        """Alle offenen Alerts schließen (z.B. bei Verbindungsverlust). Gibt Anzahl zurück."""
        alerts: list = self._daten.get("alerts", [])
        count = 0
        for alert in alerts:
            if alert.get("clearTime") is None:
                alert["clearTime"] = close_time
                count += 1
        if count > 0:
            await self._store.async_save(self._daten)
        return count

    def get_alerts(self) -> list[dict]:
        """Alle gespeicherten Alerts zurückgeben (neueste zuerst)."""
        return list(reversed(self._daten.get("alerts", [])))

    def get_open_alerts(self) -> list[dict]:
        """Nur offene Alerts zurückgeben (kein clear_time)."""
        return [a for a in self._daten.get("alerts", []) if a.get("clearTime") is None]

    async def async_clear(self) -> None:
        """Alle gespeicherten Daten löschen."""
        self._daten = {"eintraege": [], "alerts": []}
        await self._store.async_save(self._daten)
