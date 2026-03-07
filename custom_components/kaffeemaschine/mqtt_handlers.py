"""MQTT-Callback-Handler für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    SIGNAL_ALERT_UPDATE,
    SIGNAL_INFO_UPDATE,
    SIGNAL_ONLINE_UPDATE,
    SIGNAL_PRODUKTION_UPDATE,
    SIGNAL_UPDATE,
)
from .helpers import parse_mqtt_payload, parse_zeitstempel
from .models import KaffeemaschinenDaten

_LOGGER = logging.getLogger(__name__)


class MqttHandler:
    """Zentrale Klasse für alle MQTT-Callback-Verarbeitung."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
    ) -> None:
        """Handler initialisieren."""
        self.hass = hass
        self._entry_id = entry_id

    def _get_daten(self) -> KaffeemaschinenDaten:
        """Integrationsdaten aus hass.data lesen."""
        return self.hass.data[DOMAIN][self._entry_id]

    async def on_dispensing(self, nachricht) -> None:
        """DISPENSING-Nachricht verarbeiten (Bezug abgeschlossen)."""
        result = parse_mqtt_payload(nachricht.payload)
        if result is None:
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        payload, inner, device = result

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
        zeitstempel = parse_zeitstempel(zeitstempel_raw)

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

        await self._bezug_speichern(eintrag)

    async def _bezug_speichern(self, eintrag: dict) -> None:
        """Bezug speichern, Produktion beenden und Sensoren aktualisieren."""
        daten = self._get_daten()
        await daten.speicher.async_add_eintrag(eintrag, daten.max_entries)
        # Laufende Produktion abschließen – echte Daten sind jetzt im Sensor
        if daten.produktion_laufend is not None:
            daten.produktion_laufend = None
            async_dispatcher_send(
                self.hass, f"{SIGNAL_PRODUKTION_UPDATE}_{self._entry_id}"
            )
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_{self._entry_id}")

    @callback
    def on_dispensing_start(self, nachricht) -> None:
        """DISPENSING_START-Nachricht verarbeiten – Getränk ist in Zubereitung."""
        result = parse_mqtt_payload(nachricht.payload)
        if result is None:
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf DispensingStart-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        payload, inner, _device = result

        getraenk = (
            inner.get("name")
            or inner.get("beverageName")
            or inner.get("getraenk")
            or payload.get("name")
            or payload.get("beverageName")
            or payload.get("getraenk", "Unbekannt")
        )
        beverage_id = inner.get("beverageId", payload.get("beverageId"))
        is_double = inner.get("isDouble", payload.get("isDouble", False))
        estimated_seconds = (
            inner.get("estimatedCycleTimeSeconds")
            or payload.get("estimatedCycleTimeSeconds")
        )
        if estimated_seconds is None:
            raw_ms = (
                inner.get("estimatedCycleTime")
                or payload.get("estimatedCycleTime")
            )
            if raw_ms:
                estimated_seconds = int(raw_ms) // 1000

        start_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        produktion = {
            "getraenk": getraenk,
            "beverage_id": beverage_id,
            "is_double": is_double,
            "estimated_seconds": estimated_seconds,
            "start_time": start_time,
            "status": "IN_PRODUCTION",
        }

        self._get_daten().produktion_laufend = produktion
        async_dispatcher_send(
            self.hass, f"{SIGNAL_PRODUKTION_UPDATE}_{self._entry_id}"
        )
        _LOGGER.debug(
            "Produktion gestartet: %s (~%s s)", getraenk, estimated_seconds
        )

    async def on_online_status(self, nachricht) -> None:
        """Online-Status-Nachricht verarbeiten."""
        result = parse_mqtt_payload(nachricht.payload)
        if result is None:
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Online-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        payload, _inner, _device = result

        online = payload.get("online")
        if online is None:
            _LOGGER.debug("Kein 'online'-Feld im Payload: %s", payload)
            return

        zeitstempel = parse_zeitstempel(payload.get("timestamp"))

        daten = self._get_daten()
        daten.online = bool(online)
        daten.online_timestamp = zeitstempel
        async_dispatcher_send(
            self.hass, f"{SIGNAL_ONLINE_UPDATE}_{self._entry_id}"
        )

        # Bei Verbindungsverlust alle offenen Alerts automatisch schließen
        if not bool(online):
            await self._alerts_bei_offline_schliessen(zeitstempel)

    async def on_alert(self, nachricht) -> None:
        """Alert-Raise/Clear-Nachricht verarbeiten."""
        result = parse_mqtt_payload(nachricht.payload)
        if result is None:
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Alert-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        payload, inner, device = result

        message_type = payload.get("messageType") or payload.get("message_type", "")
        # Fallback: Subtopic-Suffix auswerten (.../alerts/raise → ALERT_RAISE)
        if not message_type:
            topic_suffix = nachricht.topic.split("/")[-1].upper()
            if topic_suffix == "RAISE":
                message_type = "ALERT_RAISE"
            elif topic_suffix == "CLEAR":
                message_type = "ALERT_CLEAR"
        message_id = payload.get("messageId") or payload.get("message_id")
        alert_id = inner.get("alertId") or inner.get("alert_id")
        store_id = payload.get("storeId")

        # Immer HA-Serverzeit (UTC) verwenden.
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
            await self._alert_raise_speichern(alert_eintrag)

        elif message_type == "ALERT_CLEAR":
            if not alert_id:
                _LOGGER.warning("ALERT_CLEAR ohne alertId empfangen: %s", payload)
                return
            await self._alert_clear_speichern(alert_id, zeitstempel, message_id)

        else:
            _LOGGER.debug(
                "Unbekannter messageType auf Alert-Topic: %s", message_type
            )

    @callback
    def on_info(self, nachricht) -> None:
        """EQUIPMENT_INFO-Nachricht verarbeiten – speichert Getränkemenü."""
        result = parse_mqtt_payload(nachricht.payload)
        if result is None:
            _LOGGER.warning(
                "Ungültiger JSON-Payload auf Info-Topic %s: %s",
                nachricht.topic,
                nachricht.payload,
            )
            return

        payload, inner, device = result

        message_type = payload.get("messageType", "")
        if message_type and message_type != "EQUIPMENT_INFO":
            _LOGGER.debug(
                "Info-Topic: unerwarteter messageType '%s' – ignoriert.",
                message_type,
            )
            return

        menu = {
            "beverages": inner.get("beverages", []),
            "beverage_counters": inner.get("beverageCounters", []),
            "machine_name": inner.get("machineName"),
            "machine_type": inner.get("machineType"),
            "serial_number": inner.get("serialNumber"),
            "software_version": device.get("softwareVersion", ""),
            "manufacturer": device.get("manufacturer"),
            "model": device.get("model"),
            "store_id": payload.get("storeId"),
            "timestamp": payload.get("timestamp"),
        }

        self._get_daten().geraete_menu = menu
        async_dispatcher_send(
            self.hass, f"{SIGNAL_INFO_UPDATE}_{self._entry_id}"
        )
        _LOGGER.debug(
            "Gerätemenü aktualisiert: %d Getränke, %d Zähler.",
            len(menu["beverages"]),
            len(menu["beverage_counters"]),
        )

    # ── Async-Hilfsmethoden ───────────────────────────────────────────────

    async def _alert_raise_speichern(self, alert: dict) -> None:
        """Alert-Raise speichern und Sensor aktualisieren."""
        daten = self._get_daten()
        await daten.speicher.async_add_alert_raise(alert)
        async_dispatcher_send(
            self.hass, f"{SIGNAL_ALERT_UPDATE}_{self._entry_id}"
        )

    async def _alert_clear_speichern(
        self, alert_id: str, clear_time: str, message_id: str | None
    ) -> None:
        """Alert-Clear speichern und Sensor aktualisieren."""
        daten = self._get_daten()
        await daten.speicher.async_add_alert_clear(alert_id, clear_time, message_id)
        async_dispatcher_send(
            self.hass, f"{SIGNAL_ALERT_UPDATE}_{self._entry_id}"
        )

    async def _alerts_bei_offline_schliessen(self, close_time: str) -> None:
        """Alle offenen Alerts schließen wenn die Maschine offline geht."""
        daten = self._get_daten()
        count = await daten.speicher.async_close_all_open_alerts(close_time)
        if count > 0:
            _LOGGER.info(
                "%d offene Alert(s) beim Offline-Event geschlossen.", count
            )
            async_dispatcher_send(
                self.hass, f"{SIGNAL_ALERT_UPDATE}_{self._entry_id}"
            )
