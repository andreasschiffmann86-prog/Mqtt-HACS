"""Kaffeemaschine Statistik - Home Assistant Integration."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_QOS, CONF_TOPIC, DEFAULT_QOS, DEFAULT_TOPIC, DOMAIN
from .store import KaffeeMaschineStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richtet die Integration ein."""
    hass.data.setdefault(DOMAIN, {})

    store = KaffeeMaschineStore(hass)
    await store.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "sensors": [],
        "unsubscribe": None,
    }

    topic = entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    qos = entry.data.get(CONF_QOS, DEFAULT_QOS)

    @callback
    def message_received(msg):
        """Wird aufgerufen wenn eine MQTT-Nachricht empfangen wird."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, ValueError):
            _LOGGER.warning(
                "Ungueltiger JSON-Payload auf Topic %s: %s",
                msg.topic,
                msg.payload,
            )
            return

        entry_data = {
            "getraenk": payload.get("getraenk", "Unbekannt"),
            "menge_ml": payload.get("menge_ml"),
            "temperatur": payload.get("temperatur"),
            "staerke": payload.get("staerke"),
            "zeitstempel": payload.get(
                "zeitstempel", datetime.now().isoformat(timespec="seconds")
            ),
        }

        _LOGGER.info(
            "Neuer Getraenkebezug: %s um %s",
            entry_data["getraenk"],
            entry_data["zeitstempel"],
        )

        async def _async_handle():
            await store.async_add_entry(entry_data)
            for sensor in hass.data[DOMAIN][entry.entry_id].get("sensors", []):
                sensor.async_write_ha_state()

        hass.async_create_task(_async_handle())

    unsubscribe = await mqtt.async_subscribe(hass, topic, message_received, qos)
    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe

    _LOGGER.info("Kaffeemaschine Integration gestartet, Topic: %s", topic)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlaedt die Integration."""
    unsubscribe = hass.data[DOMAIN][entry.entry_id].get("unsubscribe")
    if unsubscribe:
        unsubscribe()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
