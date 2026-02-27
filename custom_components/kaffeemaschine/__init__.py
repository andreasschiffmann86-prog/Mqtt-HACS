"""Kaffeemaschinen-Integration für Home Assistant."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_MAX_TIMELINE_ENTRIES,
    CONF_MQTT_ALERT_TOPIC,
    CONF_MQTT_ONLINE_TOPIC,
    CONF_MQTT_TOPIC,
    DEFAULT_MAX_TIMELINE_ENTRIES,
    DEFAULT_MQTT_ALERT_TOPIC,
    DEFAULT_MQTT_ONLINE_TOPIC,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
    SIGNAL_ALERT_UPDATE,
    SIGNAL_ONLINE_UPDATE,
    SIGNAL_UPDATE,
)
from .store import KaffeemaschineSpeicher

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migration älterer Config-Entries auf neue Version."""
    _LOGGER.info("Migriere Kaffeemaschinen-Config-Entry von Version %s", entry.version)

    if entry.version == 1:
        # Version 1 → 2: mqtt_alert_topic ergänzen falls nicht vorhanden
        new_data = dict(entry.data)
        if CONF_MQTT_ALERT_TOPIC not in new_data:
            new_data[CONF_MQTT_ALERT_TOPIC] = DEFAULT_MQTT_ALERT_TOPIC
            _LOGGER.info(
                "mqtt_alert_topic auf Standard '%s' gesetzt.", DEFAULT_MQTT_ALERT_TOPIC
            )
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Migration auf Version 2 erfolgreich.")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Konfigurationseintrag einrichten."""
    hass.data.setdefault(DOMAIN, {})

    topic = entry.options.get(
        CONF_MQTT_TOPIC, entry.data.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC)
    )
    online_topic = entry.options.get(
        CONF_MQTT_ONLINE_TOPIC,
        entry.data.get(CONF_MQTT_ONLINE_TOPIC, DEFAULT_MQTT_ONLINE_TOPIC),
    )
    max_entries = entry.options.get(
        CONF_MAX_TIMELINE_ENTRIES,
        entry.data.get(CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES),
    )
    alert_topic = entry.options.get(
        CONF_MQTT_ALERT_TOPIC,
        entry.data.get(CONF_MQTT_ALERT_TOPIC, DEFAULT_MQTT_ALERT_TOPIC),
    )

    speicher = KaffeemaschineSpeicher(hass, entry.entry_id)
    await speicher.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "speicher": speicher,
        "topic": topic,
        "online_topic": online_topic,
        "alert_topic": alert_topic,
        "max_entries": max_entries,
        "online": None,
        "online_timestamp": None,
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
        # (z.B. Maschinen senden {payload: {getraenk: ...}, timestamp: ...})
        inner = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}

        getraenk = inner.get("getraenk") or payload.get("getraenk", "Unbekannt")
        menge_ml = inner.get("menge_ml") or payload.get("menge_ml")
        temperatur = inner.get("temperatur") or payload.get("temperatur")
        kaffee_menge_gramm = inner.get("kaffee_menge_gramm") or payload.get("kaffee_menge_gramm")

        # Dispensing-Details aus verschachteltem Payload extrahieren
        canceled = inner.get("canceled", payload.get("canceled"))
        cup_size = inner.get("cupSize", payload.get("cupSize"))
        cycle_time = inner.get("cycleTime", payload.get("cycleTime"))
        extraction_time = inner.get("extractionTime", payload.get("extractionTime"))
        is_double = inner.get("isDouble", payload.get("isDouble"))
        strokes = inner.get("strokes", payload.get("strokes"))
        beverage_id = inner.get("beverageId", payload.get("beverageId"))
        ingredients = inner.get("ingredients", payload.get("ingredients"))

        # Geräte-Informationen
        device = payload.get("device", {}) if isinstance(payload.get("device"), dict) else {}
        device_model = device.get("model")
        device_serial = device.get("serialNumber")
        device_manufacturer = device.get("manufacturer")
        device_sw_version = device.get("softwareVersion")
        store_id = payload.get("storeId")

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
                zeitstempel = datetime.fromisoformat(ts_clean).isoformat(timespec="milliseconds")
            except ValueError:
                zeitstempel = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        else:
            zeitstempel = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        eintrag = {
            "getraenk": getraenk,
            "menge_ml": menge_ml,
            "temperatur": temperatur,
            "kaffee_menge_gramm": kaffee_menge_gramm,
            "zeitstempel": zeitstempel,
            "canceled": canceled,
            "cup_size": cup_size,
            "cycle_time": cycle_time,
            "extraction_time": extraction_time,
            "is_double": is_double,
            "strokes": strokes,
            "beverage_id": beverage_id,
            "ingredients": ingredients,
            "device_model": device_model,
            "device_serial": device_serial,
            "device_manufacturer": device_manufacturer,
            "device_sw_version": device_sw_version,
            "store_id": store_id,
        }

        hass.async_create_task(_bezug_speichern(hass, entry.entry_id, eintrag))

    async def _bezug_speichern(hass: HomeAssistant, entry_id: str, eintrag: dict):
        """Bezug speichern und Sensoren aktualisieren."""
        daten = hass.data[DOMAIN][entry_id]
        await daten["speicher"].async_add_eintrag(eintrag, daten["max_entries"])
        async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_{entry_id}")

    @callback
    def mqtt_online_nachricht_empfangen(nachricht):
        """Eingehende MQTT-Online-Status-Nachricht verarbeiten."""
        try:
            payload = json.loads(nachricht.payload)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Online-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        online = payload.get("online")
        if online is None:
            _LOGGER.debug("Kein 'online'-Feld im Payload: %s", payload)
            return

        zeitstempel_raw = payload.get("timestamp")
        if zeitstempel_raw:
            try:
                ts_clean = (
                    zeitstempel_raw.replace("Z", "+00:00")
                    if isinstance(zeitstempel_raw, str)
                    else zeitstempel_raw
                )
                zeitstempel = datetime.fromisoformat(ts_clean).isoformat(timespec="milliseconds")
            except ValueError:
                zeitstempel = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        else:
            zeitstempel = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        hass.data[DOMAIN][entry.entry_id]["online"] = bool(online)
        hass.data[DOMAIN][entry.entry_id]["online_timestamp"] = zeitstempel
        async_dispatcher_send(hass, f"{SIGNAL_ONLINE_UPDATE}_{entry.entry_id}")

        # Bei Verbindungsverlust alle offenen Alerts automatisch schließen
        if not bool(online):
            hass.async_create_task(_alerts_bei_offline_schliessen(hass, entry.entry_id, zeitstempel))

    @callback
    def mqtt_alert_nachricht_empfangen(nachricht):
        """Eingehende MQTT-Alert-Nachricht verarbeiten."""
        try:
            payload = json.loads(nachricht.payload)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Alert-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        message_type = payload.get("messageType") or payload.get("message_type", "")
        # Fallback: Subtopic-Suffix auswerten (.../alerts/raise → ALERT_RAISE)
        if not message_type:
            topic_suffix = nachricht.topic.split("/")[-1].upper()
            if topic_suffix == "RAISE":
                message_type = "ALERT_RAISE"
            elif topic_suffix == "CLEAR":
                message_type = "ALERT_CLEAR"
        message_id = payload.get("messageId") or payload.get("message_id")
        inner = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}
        alert_id = inner.get("alertId") or inner.get("alert_id")
        device = payload.get("device", {}) if isinstance(payload.get("device"), dict) else {}
        store_id = payload.get("storeId")

        # Immer HA-Serverzeit (UTC) verwenden.
        # Der Sender liefert lokale Zeit ohne korrekten Offset → ignorieren.
        zeitstempel = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        if message_type == "ALERT_RAISE":
            if not alert_id:
                _LOGGER.warning("ALERT_RAISE ohne alertId empfangen: %s", payload)
                return
            alert_eintrag = {
                "alertId": alert_id,
                "category": inner.get("category"),
                "description": inner.get("description"),
                "errorCode": inner.get("errorCode"),
                "severity": inner.get("severity"),
                "raiseTime": zeitstempel,
                "clearTime": None,
                "messageIdRaise": message_id,
                "messageIdClear": None,
                "deviceModel": device.get("model"),
                "deviceSerial": device.get("serialNumber"),
                "deviceManufacturer": device.get("manufacturer"),
                "deviceSwVersion": device.get("softwareVersion"),
                "deviceFwVersion": device.get("firmwareVersion"),
                "storeId": store_id,
            }
            hass.async_create_task(_alert_raise_speichern(hass, entry.entry_id, alert_eintrag))

        elif message_type == "ALERT_CLEAR":
            if not alert_id:
                _LOGGER.warning("ALERT_CLEAR ohne alertId empfangen: %s", payload)
                return
            hass.async_create_task(_alert_clear_speichern(hass, entry.entry_id, alert_id, zeitstempel, message_id))

        else:
            _LOGGER.debug("Unbekannter messageType auf Alert-Topic: %s", message_type)

    async def _alert_raise_speichern(hass: HomeAssistant, entry_id: str, alert: dict):
        """Alert-Raise speichern und Sensor aktualisieren."""
        daten = hass.data[DOMAIN][entry_id]
        await daten["speicher"].async_add_alert_raise(alert)
        async_dispatcher_send(hass, f"{SIGNAL_ALERT_UPDATE}_{entry_id}")

    async def _alert_clear_speichern(hass: HomeAssistant, entry_id: str, alert_id: str, clear_time: str, message_id: str | None):
        """Alert-Clear speichern und Sensor aktualisieren."""
        daten = hass.data[DOMAIN][entry_id]
        await daten["speicher"].async_add_alert_clear(alert_id, clear_time, message_id)
        async_dispatcher_send(hass, f"{SIGNAL_ALERT_UPDATE}_{entry_id}")

    async def _alerts_bei_offline_schliessen(hass: HomeAssistant, entry_id: str, close_time: str):
        """Alle offenen Alerts schließen wenn die Maschine offline geht."""
        daten = hass.data.get(DOMAIN, {}).get(entry_id)
        if not daten:
            return
        count = await daten["speicher"].async_close_all_open_alerts(close_time)
        if count > 0:
            _LOGGER.info("%d offene Alert(s) beim Offline-Event geschlossen.", count)
            async_dispatcher_send(hass, f"{SIGNAL_ALERT_UPDATE}_{entry_id}")

    try:
        unsubscribe = await mqtt.async_subscribe(
            hass, topic, mqtt_nachricht_empfangen, qos=0
        )
        unsubscribe_online = await mqtt.async_subscribe(
            hass, online_topic, mqtt_online_nachricht_empfangen, qos=0
        )
        # Wildcard-Subscription: fängt .../alerts/raise UND .../alerts/clear
        alert_topic_wildcard = alert_topic.rstrip("/") + "/#"
        _LOGGER.debug("Alert-Topic abonniert: %s", alert_topic_wildcard)
        unsubscribe_alert = await mqtt.async_subscribe(
            hass, alert_topic_wildcard, mqtt_alert_nachricht_empfangen, qos=0
        )
    except Exception as err:
        _LOGGER.error("MQTT-Subscription fehlgeschlagen: %s", err, exc_info=True)
        return False

    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe
    hass.data[DOMAIN][entry.entry_id]["unsubscribe_online"] = unsubscribe_online
    hass.data[DOMAIN][entry.entry_id]["unsubscribe_alert"] = unsubscribe_alert

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Plattformen konnten nicht entladen werden (evtl. nie geladen) – Cleanup trotzdem.", exc_info=True)
        unload_ok = True

    daten = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if daten:
        for key in ("unsubscribe", "unsubscribe_online", "unsubscribe_alert"):
            unsub = daten.get(key)
            if unsub:
                unsub()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Konfigurationseintrag neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)
