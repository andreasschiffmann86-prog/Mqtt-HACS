"""Kaffeemaschine MQTT Statistics integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .config_flow import CONF_QOS
from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN
from .timeline import KaffeeMaschineTimeline

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


def signal_new_drink(entry_id: str) -> str:
    """Return the dispatcher signal name for a config entry."""
    return f"{DOMAIN}_new_drink_{entry_id}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kaffeemaschine from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    timeline = KaffeeMaschineTimeline()
    await timeline.async_setup(hass)

    hass.data[DOMAIN][entry.entry_id] = {
        "timeline": timeline,
        "unsubscribe": None,
    }

    topic: str = entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    qos: int = entry.data.get(CONF_QOS, 0)

    @callback
    def _on_message(msg: Any) -> None:
        """Handle incoming MQTT message."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            _LOGGER.warning(
                "Kaffeemaschine: Ungültiger JSON-Payload empfangen: %s", msg.payload
            )
            return

        getraenk: str = payload.get("getraenk", "Unbekannt")
        menge_ml: int | None = payload.get("menge_ml")
        temperatur: int | None = payload.get("temperatur")
        staerke: str | None = payload.get("staerke")
        zeitstempel: str = payload.get("zeitstempel", "")

        async def _save_and_update() -> None:
            await timeline.add_entry(
                getraenk, menge_ml, temperatur, staerke, zeitstempel
            )
            async_dispatcher_send(hass, signal_new_drink(entry.entry_id))

        hass.async_create_task(_save_and_update())

    unsubscribe = await mqtt.async_subscribe(hass, topic, _on_message, qos)

    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unsubscribe = hass.data[DOMAIN][entry.entry_id].get("unsubscribe")
    if callable(unsubscribe):
        unsubscribe()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
