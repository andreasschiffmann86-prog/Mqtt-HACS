"""Sensoren für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SENSOR_ALERT_TIMELINE,
    SENSOR_BEZUEGE_GESAMT,
    SENSOR_BEZUEGE_HEUTE,
    SENSOR_LIEBLINGSGETRAENK,
    SENSOR_LETZTES_GETRAENK,
    SENSOR_TIMELINE,
    SENSOR_GERAETE_INFO,
    SENSOR_LETZTER_BEZUG_STATUS,
    SIGNAL_ALERT_UPDATE,
    SIGNAL_UPDATE,
)
from .store import KaffeemaschineSpeicher
from .timeline import (
    get_bezuege_heute,
    get_lieblingsgetraenk,
    get_letztes_getraenk,
    get_timeline,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren für diesen Konfigurationseintrag einrichten."""
    daten = hass.data[DOMAIN][entry.entry_id]
    speicher: KaffeemaschineSpeicher = daten["speicher"]

    sensoren = [
        LetztesGetraenkSensor(hass, entry.entry_id, speicher),
        BezuegeHeuteSensor(hass, entry.entry_id, speicher),
        BezuegeGesamtSensor(hass, entry.entry_id, speicher),
        LieblingsgetraenkSensor(hass, entry.entry_id, speicher),
        TimelineSensor(hass, entry.entry_id, speicher),
        GeraeteInfoSensor(hass, entry.entry_id, speicher),
        LetzterBezugStatusSensor(hass, entry.entry_id, speicher),
        AlertTimelineSensor(hass, entry.entry_id, speicher),
    ]
    async_add_entities(sensoren)


class KaffeemaschineSensorBase(SensorEntity):
    """Basisklasse für alle Kaffeemaschinen-Sensoren."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        speicher: KaffeemaschineSpeicher,
        sensor_key: str,
    ) -> None:
        """Sensor initialisieren."""
        self.hass = hass
        self._entry_id = entry_id
        self._speicher = speicher
        self._sensor_key = sensor_key
        self._attr_unique_id = f"{entry_id}_{sensor_key}"

    async def async_added_to_hass(self) -> None:
        """Auf Dispatcher-Signale hören."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE}_{self._entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Sensor-Status aktualisieren."""
        self.async_write_ha_state()


class LetztesGetraenkSensor(KaffeemaschineSensorBase):
    """Sensor für das zuletzt bezogene Getränk."""

    _attr_icon = "mdi:coffee"
    _attr_translation_key = SENSOR_LETZTES_GETRAENK

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_LETZTES_GETRAENK)

    @property
    def native_value(self) -> str | None:
        """Letztes Getränk zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes:
            return letztes.get("getraenk")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attribute des letzten Bezugs zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes:
            return {
                "menge_ml": letztes.get("menge_ml"),
                "temperatur": letztes.get("temperatur"),
                "kaffee_menge_gramm": letztes.get("kaffee_menge_gramm"),
                "zeitstempel": letztes.get("zeitstempel"),
                "canceled": letztes.get("canceled"),
                "cup_size": letztes.get("cup_size"),
                "cycle_time": letztes.get("cycle_time"),
                "extraction_time": letztes.get("extraction_time"),
                "is_double": letztes.get("is_double"),
                "strokes": letztes.get("strokes"),
                "beverage_id": letztes.get("beverage_id"),
                "ingredients": letztes.get("ingredients"),
                "device_model": letztes.get("device_model"),
                "device_serial": letztes.get("device_serial"),
                "store_id": letztes.get("store_id"),
            }
        return {}


class BezuegeHeuteSensor(KaffeemaschineSensorBase):
    """Sensor für die Anzahl der Bezüge heute."""

    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "Bezüge"
    _attr_translation_key = SENSOR_BEZUEGE_HEUTE

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_BEZUEGE_HEUTE)

    @property
    def native_value(self) -> int:
        """Anzahl der Bezüge heute zurückgeben."""
        return get_bezuege_heute(self._speicher.get_eintraege())


class BezuegeGesamtSensor(KaffeemaschineSensorBase):
    """Sensor für die Gesamtanzahl der Bezüge."""

    _attr_icon = "mdi:coffee-maker"
    _attr_native_unit_of_measurement = "Bezüge"
    _attr_translation_key = SENSOR_BEZUEGE_GESAMT

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_BEZUEGE_GESAMT)

    @property
    def native_value(self) -> int:
        """Gesamtanzahl der Bezüge zurückgeben."""
        return len(self._speicher.get_eintraege())


class LieblingsgetraenkSensor(KaffeemaschineSensorBase):
    """Sensor für das Lieblingsgetränk."""

    _attr_icon = "mdi:star"
    _attr_translation_key = SENSOR_LIEBLINGSGETRAENK

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_LIEBLINGSGETRAENK)

    @property
    def native_value(self) -> str | None:
        """Lieblingsgetränk zurückgeben."""
        return get_lieblingsgetraenk(self._speicher.get_eintraege())


class TimelineSensor(KaffeemaschineSensorBase):
    """Sensor für die Timeline der letzten Bezüge."""

    _attr_icon = "mdi:timeline"
    _attr_translation_key = SENSOR_TIMELINE

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_TIMELINE)

    @property
    def native_value(self) -> int:
        """Gesamtanzahl der Einträge in der Timeline."""
        return len(self._speicher.get_eintraege())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Timeline als Attribut zurückgeben."""
        return {
            "timeline": get_timeline(self._speicher.get_eintraege(), anzahl=20),
        }


class GeraeteInfoSensor(KaffeemaschineSensorBase):
    """Sensor für Geräte-Informationen der Kaffeemaschine."""

    _attr_icon = "mdi:information-outline"
    _attr_translation_key = SENSOR_GERAETE_INFO

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_GERAETE_INFO)

    @property
    def native_value(self) -> str | None:
        """Maschinenmodell zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes and letztes.get("device_model"):
            return letztes.get("device_model")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Geräte-Details als Attribute zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes:
            return {
                "manufacturer": letztes.get("device_manufacturer"),
                "model": letztes.get("device_model"),
                "serial_number": letztes.get("device_serial"),
                "software_version": letztes.get("device_sw_version"),
                "store_id": letztes.get("store_id"),
            }
        return {}


class LetzterBezugStatusSensor(KaffeemaschineSensorBase):
    """Sensor für den Status des letzten Bezugs (erfolgreich/abgebrochen)."""

    _attr_icon = "mdi:check-circle-outline"
    _attr_translation_key = SENSOR_LETZTER_BEZUG_STATUS

    def __init__(
        self, hass: HomeAssistant, entry_id: str, speicher: KaffeemaschineSpeicher
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(hass, entry_id, speicher, SENSOR_LETZTER_BEZUG_STATUS)

    @property
    def native_value(self) -> str | None:
        """Status des letzten Bezugs zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes:
            canceled = letztes.get("canceled")
            if canceled is True:
                return "Abgebrochen"
            elif canceled is False:
                return "Erfolgreich"
            return "Unbekannt"
        return None

    @property
    def icon(self) -> str:
        """Icon basierend auf Status."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes and letztes.get("canceled") is True:
            return "mdi:cancel"
        return "mdi:check-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Bezug-Details als Attribute zurückgeben."""
        letztes = get_letztes_getraenk(self._speicher.get_eintraege())
        if letztes:
            return {
                "beverage_id": letztes.get("beverage_id"),
                "cup_size": letztes.get("cup_size"),
                "cycle_time": letztes.get("cycle_time"),
                "extraction_time": letztes.get("extraction_time"),
                "is_double": letztes.get("is_double"),
                "strokes": letztes.get("strokes"),
                "ingredients": letztes.get("ingredients"),
                "canceled": letztes.get("canceled"),
            }
        return {}


class AlertTimelineSensor(SensorEntity):
    """Sensor für die Alert-Timeline der Kaffeemaschine."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:alert-circle"
    _attr_translation_key = SENSOR_ALERT_TIMELINE

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        speicher: KaffeemaschineSpeicher,
    ) -> None:
        """Sensor initialisieren."""
        self.hass = hass
        self._entry_id = entry_id
        self._speicher = speicher
        self._attr_unique_id = f"{entry_id}_{SENSOR_ALERT_TIMELINE}"

    async def async_added_to_hass(self) -> None:
        """Auf Alert-Dispatcher-Signale hören."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ALERT_UPDATE}_{self._entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Sensor-Zustand aktualisieren."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Anzahl der aktuell offenen Alerts zurückgeben."""
        return len(self._speicher.get_open_alerts())

    @property
    def icon(self) -> str:
        """Icon: rot bei offenen Alerts, grün sonst."""
        if self._speicher.get_open_alerts():
            return "mdi:alert-circle"
        return "mdi:check-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Alert-Timeline als Attribut zurückgeben (neueste zuerst)."""
        now = datetime.now(tz=timezone.utc)
        alle_alerts = self._speicher.get_alerts()
        offene_alerts = self._speicher.get_open_alerts()

        def _bereichere_alert(alert: dict) -> dict:
            enriched = dict(alert)
            if alert.get("clearTime") is None:
                # Dauer berechnen
                try:
                    raise_dt = datetime.fromisoformat(alert["raiseTime"])
                    if raise_dt.tzinfo is None:
                        raise_dt = raise_dt.replace(tzinfo=timezone.utc)
                    delta = now - raise_dt
                    total_sec = int(delta.total_seconds())
                    stunden = total_sec // 3600
                    minuten = (total_sec % 3600) // 60
                    sekunden = total_sec % 60
                    if stunden > 0:
                        enriched["duration"] = f"{stunden}h {minuten}m"
                    elif minuten > 0:
                        enriched["duration"] = f"{minuten}m {sekunden}s"
                    else:
                        enriched["duration"] = f"{sekunden}s"
                    enriched["duration_seconds"] = total_sec
                except (ValueError, KeyError, TypeError):
                    enriched["duration"] = None
                    enriched["duration_seconds"] = None
                enriched["status"] = "offen"
            else:
                # Dauer von Raise bis Clear
                try:
                    raise_dt = datetime.fromisoformat(alert["raiseTime"])
                    clear_dt = datetime.fromisoformat(alert["clearTime"])
                    if raise_dt.tzinfo is None:
                        raise_dt = raise_dt.replace(tzinfo=timezone.utc)
                    if clear_dt.tzinfo is None:
                        clear_dt = clear_dt.replace(tzinfo=timezone.utc)
                    delta = clear_dt - raise_dt
                    total_sec = int(delta.total_seconds())
                    stunden = total_sec // 3600
                    minuten = (total_sec % 3600) // 60
                    sekunden = total_sec % 60
                    if stunden > 0:
                        enriched["duration"] = f"{stunden}h {minuten}m"
                    elif minuten > 0:
                        enriched["duration"] = f"{minuten}m {sekunden}s"
                    else:
                        enriched["duration"] = f"{sekunden}s"
                    enriched["duration_seconds"] = total_sec
                except (ValueError, KeyError, TypeError):
                    enriched["duration"] = None
                    enriched["duration_seconds"] = None
                enriched["status"] = "geschlossen"
            return enriched

        return {
            "open_alerts": [_bereichere_alert(a) for a in offene_alerts],
            "open_count": len(offene_alerts),
            "all_alerts": [_bereichere_alert(a) for a in alle_alerts],
        }

