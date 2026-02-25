"""Kaffeemaschinen-Integration für Home Assistant."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_MAX_TIMELINE_ENTRIES,
    CONF_MQTT_TOPIC,
    DEFAULT_MAX_TIMELINE_ENTRIES,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
    SIGNAL_UPDATE,
)
from .store import KaffeemaschineSpeicher

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Konfigurationseintrag einrichten."""
    hass.data.setdefault(DOMAIN, {})

    topic = entry.options.get(
        CONF_MQTT_TOPIC, entry.data.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC)
    )
    max_entries = entry.options.get(
        CONF_MAX_TIMELINE_ENTRIES,
        entry.data.get(CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES),
    )

    speicher = KaffeemaschineSpeicher(hass, entry.entry_id)
    await speicher.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "speicher": speicher,
        "topic": topic,
        "max_entries": max_entries,
    }

    @callback
    def mqtt_nachricht_empfangen(nachricht):
        """Eingehende MQTT-Nachricht verarbeiten."""
        try:
            payload = json.loads(nachricht.payload)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        # Unterstütze sowohl flache als auch verschachtelte Payloads
        # (z.B. WMF-Maschinen senden {payload: {getraenk: ...}, timestamp: ...})
        inner = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}

        getraenk = inner.get("getraenk") or payload.get("getraenk", "Unbekannt")
        menge_ml = inner.get("menge_ml") or payload.get("menge_ml")
        temperatur = inner.get("temperatur") or payload.get("temperatur")
        kaffee_menge_gramm = inner.get("kaffee_menge_gramm") or payload.get("kaffee_menge_gramm")

        # Zeitstempel: unterstütze "zeitstempel" und "timestamp"
        zeitstempel_raw = (
            inner.get("zeitstempel")
            or payload.get("zeitstempel")
            or payload.get("timestamp")
        )

        if zeitstempel_raw:
            try:
                # "Z"-Suffix durch "+00:00" ersetzen für fromisoformat-Kompatibilität
                ts_clean = zeitstempel_raw.replace("Z", "+00:00") if isinstance(zeitstempel_raw, str) else zeitstempel_raw
                zeitstempel = datetime.fromisoformat(ts_clean).isoformat()
            except ValueError:
                zeitstempel = datetime.now().isoformat()
        else:
            zeitstempel = datetime.now().isoformat()

        eintrag = {
            "getraenk": getraenk,
            "menge_ml": menge_ml,
            "temperatur": temperatur,
            "kaffee_menge_gramm": kaffee_menge_gramm,
            "zeitstempel": zeitstempel,
        }

        hass.async_create_task(_bezug_speichern(hass, entry.entry_id, eintrag))

    async def _bezug_speichern(hass: HomeAssistant, entry_id: str, eintrag: dict):
        """Bezug speichern und Sensoren aktualisieren."""
        daten = hass.data[DOMAIN][entry_id]
        await daten["speicher"].async_add_eintrag(eintrag, daten["max_entries"])
        async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_{entry_id}")

    unsubscribe = await mqtt.async_subscribe(
        hass, topic, mqtt_nachricht_empfangen, qos=0
    )
    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        daten = hass.data[DOMAIN].pop(entry.entry_id)
        unsubscribe = daten.get("unsubscribe")
        if unsubscribe:
            unsubscribe()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Konfigurationseintrag neu laden."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
