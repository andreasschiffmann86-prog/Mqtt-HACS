"""Kaffeemaschinen-Integration für Home Assistant."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_MAX_TIMELINE_ENTRIES,
    CONF_MQTT_ALERT_TOPIC,
    CONF_MQTT_COMMAND_TOPIC,
    CONF_MQTT_DISPENSING_START_TOPIC,
    CONF_MQTT_INFO_TOPIC,
    CONF_MQTT_ONLINE_TOPIC,
    CONF_MQTT_TOPIC,
    DEFAULT_MAX_TIMELINE_ENTRIES,
    DEFAULT_MQTT_ALERT_TOPIC,
    DEFAULT_MQTT_COMMAND_TOPIC,
    DEFAULT_MQTT_DISPENSING_START_TOPIC,
    DEFAULT_MQTT_INFO_TOPIC,
    DEFAULT_MQTT_ONLINE_TOPIC,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
    SERVICE_BESTELLEN,
)
from .helpers import get_config
from .models import KaffeemaschinenDaten
from .mqtt_handlers import MqttHandler
from .store import KaffeemaschineSpeicher

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]

# ── Datengetriebene Migration ─────────────────────────────────────────────────
# Mapping: version → {Feld: Default}
_MIGRATIONS: dict[int, dict[str, Any]] = {
    1: {CONF_MQTT_ALERT_TOPIC: DEFAULT_MQTT_ALERT_TOPIC},
    2: {CONF_MQTT_DISPENSING_START_TOPIC: DEFAULT_MQTT_DISPENSING_START_TOPIC},
    3: {CONF_MQTT_INFO_TOPIC: DEFAULT_MQTT_INFO_TOPIC},
    4: {CONF_MQTT_COMMAND_TOPIC: DEFAULT_MQTT_COMMAND_TOPIC},
}


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migration älterer Config-Entries auf aktuelle Version."""
    _LOGGER.info("Migriere Kaffeemaschinen-Config-Entry von Version %s", entry.version)
    new_data = dict(entry.data)

    while entry.version in _MIGRATIONS:
        for key, default in _MIGRATIONS[entry.version].items():
            new_data.setdefault(key, default)
            _LOGGER.info(
                "  v%d→v%d: '%s' = '%s'",
                entry.version, entry.version + 1, key, default,
            )
        hass.config_entries.async_update_entry(
            entry, data=new_data, version=entry.version + 1
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Konfigurationseintrag einrichten."""
    hass.data.setdefault(DOMAIN, {})

    topic = get_config(entry, CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC)
    online_topic = get_config(entry, CONF_MQTT_ONLINE_TOPIC, DEFAULT_MQTT_ONLINE_TOPIC)
    alert_topic = get_config(entry, CONF_MQTT_ALERT_TOPIC, DEFAULT_MQTT_ALERT_TOPIC)
    dispensing_start_topic = get_config(entry, CONF_MQTT_DISPENSING_START_TOPIC, DEFAULT_MQTT_DISPENSING_START_TOPIC)
    info_topic = get_config(entry, CONF_MQTT_INFO_TOPIC, DEFAULT_MQTT_INFO_TOPIC)
    command_topic = get_config(entry, CONF_MQTT_COMMAND_TOPIC, DEFAULT_MQTT_COMMAND_TOPIC)
    max_entries = get_config(entry, CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES)

    speicher = KaffeemaschineSpeicher(hass, entry.entry_id)
    await speicher.async_load()

    daten = KaffeemaschinenDaten(
        speicher=speicher,
        topic=topic,
        online_topic=online_topic,
        alert_topic=alert_topic,
        dispensing_start_topic=dispensing_start_topic,
        info_topic=info_topic,
        command_topic=command_topic,
        max_entries=max_entries,
    )
    hass.data[DOMAIN][entry.entry_id] = daten

    # ── MQTT-Subscriptions via Handler-Klasse ─────────────────────────────
    handler = MqttHandler(hass, entry.entry_id)

    try:
        unsubscribe = await mqtt.async_subscribe(
            hass, topic, handler.on_dispensing, qos=0
        )
        unsubscribe_online = await mqtt.async_subscribe(
            hass, online_topic, handler.on_online_status, qos=0
        )
        # Wildcard-Subscription: fängt .../alerts/raise UND .../alerts/clear
        # Hinweis: rstrip("/") verhindert Doppel-Slashes bei Trailing-Slash im Topic.
        # Beispiel: "kaffeemaschine/alert" → "kaffeemaschine/alert/#"
        #           "kaffeemaschine/alert/" → "kaffeemaschine/alert/#" (nicht "...//# ")
        alert_topic_wildcard = alert_topic.rstrip("/") + "/#"
        _LOGGER.debug("Alert-Topic abonniert: %s", alert_topic_wildcard)
        unsubscribe_alert = await mqtt.async_subscribe(
            hass, alert_topic_wildcard, handler.on_alert, qos=0
        )
        _LOGGER.debug("DispensingStart-Topic abonniert: %s", dispensing_start_topic)
        unsubscribe_dispensing_start = await mqtt.async_subscribe(
            hass, dispensing_start_topic, handler.on_dispensing_start, qos=0
        )
        _LOGGER.debug("Info-Topic abonniert: %s", info_topic)
        unsubscribe_info = await mqtt.async_subscribe(
            hass, info_topic, handler.on_info, qos=0
        )
    except Exception as err:
        _LOGGER.error("MQTT-Subscription fehlgeschlagen: %s", err, exc_info=True)
        return False

    daten.unsubscribe = unsubscribe
    daten.unsubscribe_online = unsubscribe_online
    daten.unsubscribe_alert = unsubscribe_alert
    daten.unsubscribe_dispensing_start = unsubscribe_dispensing_start
    daten.unsubscribe_info = unsubscribe_info

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Service: kaffeemaschine.bestellen ─────────────────────────────────
    if not hass.services.has_service(DOMAIN, SERVICE_BESTELLEN):
        _bestellen_schema = vol.Schema({
            vol.Required("beverage_id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("beverage_name", default=""): cv.string,
            vol.Optional("entry_id"): cv.string,
        })

        async def async_handle_bestellen(call: ServiceCall) -> None:
            """Getränk via MQTT bestellen – Topic aus der Integration."""
            beverage_id: int = call.data["beverage_id"]
            beverage_name: str = call.data.get("beverage_name", "")
            entry_id = call.data.get("entry_id")
            alle = hass.data.get(DOMAIN, {})
            if entry_id:
                daten = alle.get(entry_id)
            else:
                daten = next(iter(alle.values()), None)
            if not daten:
                _LOGGER.error("kaffeemaschine.bestellen: keine aktive Integration gefunden.")
                return
            cmd_topic = daten.command_topic
            payload = json.dumps({"messageType": "START_BEVERAGE", "beverageId": beverage_id})
            await mqtt.async_publish(hass, cmd_topic, payload, qos=0, retain=False)
            _LOGGER.info(
                "Getränk bestellt: id=%d name='%s' topic=%s",
                beverage_id, beverage_name, cmd_topic,
            )

        hass.services.async_register(
            DOMAIN, SERVICE_BESTELLEN, async_handle_bestellen, schema=_bestellen_schema
        )
        _LOGGER.debug("Service %s.%s registriert.", DOMAIN, SERVICE_BESTELLEN)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Plattformen konnten nicht entladen werden (evtl. nie geladen) – Cleanup trotzdem.",
            exc_info=True,
        )
        unload_ok = True

    daten: KaffeemaschinenDaten | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if daten:
        for unsub in (
            daten.unsubscribe, daten.unsubscribe_online, daten.unsubscribe_alert,
            daten.unsubscribe_dispensing_start, daten.unsubscribe_info,
        ):
            if unsub:
                unsub()

    # Service abmelden wenn kein Entry mehr aktiv
    if not hass.data.get(DOMAIN):
        if hass.services.has_service(DOMAIN, SERVICE_BESTELLEN):
            hass.services.async_remove(DOMAIN, SERVICE_BESTELLEN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Konfigurationseintrag neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)
