"""Datenmodelle für die Kaffeemaschinen-Integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .store import KaffeemaschineSpeicher


@dataclass
class KaffeemaschinenDaten:
    """Typisierter Container für alle Laufzeitdaten einer Kaffeemaschine."""

    speicher: KaffeemaschineSpeicher
    topic: str
    online_topic: str
    alert_topic: str
    dispensing_start_topic: str
    info_topic: str
    command_topic: str
    max_entries: int
    online: bool | None = None
    online_timestamp: str | None = None
    produktion_laufend: dict | None = None
    geraete_menu: dict | None = None
    unsubscribe: Callable | None = None
    unsubscribe_online: Callable | None = None
    unsubscribe_alert: Callable | None = None
    unsubscribe_dispensing_start: Callable | None = None
    unsubscribe_info: Callable | None = None
