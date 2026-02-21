"""Sensor platform for Kaffeemaschine integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import signal_new_drink
from .const import DOMAIN
from .timeline import KaffeeMaschineTimeline

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kaffeemaschine sensors from a config entry."""
    timeline: KaffeeMaschineTimeline = hass.data[DOMAIN][entry.entry_id]["timeline"]

    entities = [
        KaffeeMaschineLetzteGetraenkSensor(entry, timeline),
        KaffeeMaschineBezuegeHeuteSensor(entry, timeline),
        KaffeeMaschineBezuegeGesamtSensor(entry, timeline),
        KaffeeMaschineLieblingsgetraenkSensor(entry, timeline),
        KaffeeMaschineTimelineSensor(entry, timeline),
    ]
    async_add_entities(entities)


class _KaffeeMaschineBaseSensor(SensorEntity):
    """Base class for Kaffeemaschine sensors."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize sensor."""
        self._entry = entry
        self._timeline = timeline

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher updates when entity is added."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_new_drink(self._entry.entry_id),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Handle a new drink event by refreshing state."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Kaffeemaschine",
            "model": "MQTT Statistik",
        }


class KaffeeMaschineLetzteGetraenkSensor(_KaffeeMaschineBaseSensor):
    """Sensor for the last drink consumed."""

    _attr_icon = "mdi:coffee"
    _attr_name = "Kaffeemaschine Letztes Getränk"

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize."""
        super().__init__(entry, timeline)
        self._attr_unique_id = f"{entry.entry_id}_letztes_getraenk"

    @property
    def state(self) -> str:
        """Return the last drink name."""
        last = self._timeline.get_last_drink()
        if last is None:
            return "Unbekannt"
        return last.get("getraenk", "Unbekannt")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        last = self._timeline.get_last_drink()
        if last is None:
            return {}
        return {
            "menge_ml": last.get("menge_ml"),
            "temperatur": last.get("temperatur"),
            "staerke": last.get("staerke"),
            "zeitstempel": last.get("zeitstempel"),
        }


class KaffeeMaschineBezuegeHeuteSensor(_KaffeeMaschineBaseSensor):
    """Sensor for the number of drinks today."""

    _attr_icon = "mdi:counter"
    _attr_name = "Kaffeemaschine Bezüge Heute"
    _attr_native_unit_of_measurement = "Bezüge"

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize."""
        super().__init__(entry, timeline)
        self._attr_unique_id = f"{entry.entry_id}_bezuege_heute"

    @property
    def state(self) -> int:
        """Return drinks today."""
        return self._timeline.get_today_count()


class KaffeeMaschineBezuegeGesamtSensor(_KaffeeMaschineBaseSensor):
    """Sensor for the total number of drinks."""

    _attr_icon = "mdi:counter"
    _attr_name = "Kaffeemaschine Bezüge Gesamt"
    _attr_native_unit_of_measurement = "Bezüge"

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize."""
        super().__init__(entry, timeline)
        self._attr_unique_id = f"{entry.entry_id}_bezuege_gesamt"

    @property
    def state(self) -> int:
        """Return total drinks."""
        return self._timeline.get_total_count()


class KaffeeMaschineLieblingsgetraenkSensor(_KaffeeMaschineBaseSensor):
    """Sensor for the favourite drink."""

    _attr_icon = "mdi:star"
    _attr_name = "Kaffeemaschine Lieblingsgetränk"

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize."""
        super().__init__(entry, timeline)
        self._attr_unique_id = f"{entry.entry_id}_lieblingsgetraenk"

    @property
    def state(self) -> str:
        """Return favourite drink."""
        return self._timeline.get_favorite_drink() or "Unbekannt"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        counts = self._timeline.get_count_by_type()
        fav = self._timeline.get_favorite_drink()
        if fav is None:
            return {"anzahl": 0}
        return {"anzahl": counts.get(fav, 0)}


class KaffeeMaschineTimelineSensor(_KaffeeMaschineBaseSensor):
    """Sensor exposing the full timeline."""

    _attr_icon = "mdi:timeline"
    _attr_name = "Kaffeemaschine Timeline"

    def __init__(self, entry: ConfigEntry, timeline: KaffeeMaschineTimeline) -> None:
        """Initialize."""
        super().__init__(entry, timeline)
        self._attr_unique_id = f"{entry.entry_id}_timeline"

    @property
    def state(self) -> int:
        """Return total number of timeline entries."""
        return self._timeline.get_total_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the last 20 entries as attribute."""
        return {"entries": self._timeline.get_entries(limit=20)}
