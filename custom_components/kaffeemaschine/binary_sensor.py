"""Binary Sensoren für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BINARY_SENSOR_ONLINE,
    DOMAIN,
    SIGNAL_ONLINE_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary Sensoren für diesen Konfigurationseintrag einrichten."""
    async_add_entities([
        KaffeemaschineOnlineSensor(hass, entry.entry_id),
    ])


class KaffeemaschineOnlineSensor(BinarySensorEntity):
    """Binary Sensor für den Online-Status der Kaffeemaschine."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = BINARY_SENSOR_ONLINE

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
    ) -> None:
        """Sensor initialisieren."""
        self.hass = hass
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{BINARY_SENSOR_ONLINE}"

    @property
    def device_info(self) -> DeviceInfo:
        """Geräteinformationen für das HA-Geräte-Dashboard."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Kaffeemaschine",
        )

    async def async_added_to_hass(self) -> None:
        """Auf Dispatcher-Signale hören."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ONLINE_UPDATE}_{self._entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Sensor-Status aktualisieren."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Online-Status zurückgeben."""
        daten = self.hass.data.get(DOMAIN, {}).get(self._entry_id)
        return daten.online if daten else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusätzliche Attribute zurückgeben."""
        daten = self.hass.data.get(DOMAIN, {}).get(self._entry_id)
        attrs: dict[str, Any] = {}
        if daten and daten.online_timestamp:
            attrs["letztes_update"] = daten.online_timestamp
        return attrs
