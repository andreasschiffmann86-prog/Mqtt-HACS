"""Gemeinsame Hilfsfunktionen für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


def parse_mqtt_payload(raw: str) -> tuple[dict, dict, dict] | None:
    """Parst MQTT-Payload und gibt (payload, inner, device) zurück.

    Gibt None zurück bei ungültigem JSON.
    - payload: das vollständige JSON-Objekt
    - inner:   payload["payload"] (verschachteltes Objekt) oder {}
    - device:  payload["device"] oder {}
    """
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return None
    inner = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}
    device = payload.get("device", {}) if isinstance(payload.get("device"), dict) else {}
    return payload, inner, device


def parse_zeitstempel(raw: str | None) -> str:
    """ISO-Zeitstempel normalisieren. Fallback: aktuelle UTC-Zeit.

    Ersetzt 'Z'-Suffix durch '+00:00' für datetime.fromisoformat()-Kompatibilität.
    """
    if raw:
        try:
            ts_clean = raw.replace("Z", "+00:00") if isinstance(raw, str) else raw
            return datetime.fromisoformat(ts_clean).isoformat(timespec="milliseconds")
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def get_config(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Liest Konfigurationswert mit Fallback options → data → default."""
    return entry.options.get(key, entry.data.get(key, default))
