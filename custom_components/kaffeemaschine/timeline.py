"""Timeline-Hilfsfunktionen für Kaffeemaschinen-Bezüge."""
from __future__ import annotations

from collections import Counter
from datetime import date


def get_bezuege_heute(eintraege: list[dict]) -> int:
    """Anzahl der Bezüge von heute berechnen."""
    heute = date.today().isoformat()
    zaehler = 0
    for eintrag in eintraege:
        zeitstempel = eintrag.get("zeitstempel", "")
        if zeitstempel.startswith(heute):
            zaehler += 1
    return zaehler


def get_lieblingsgetraenk(eintraege: list[dict]) -> str | None:
    """Das am häufigsten bezogene Getränk ermitteln."""
    if not eintraege:
        return None
    zaehler: Counter = Counter(
        eintrag.get("getraenk", "Unbekannt") for eintrag in eintraege
    )
    return zaehler.most_common(1)[0][0]


def get_letztes_getraenk(eintraege: list[dict]) -> dict | None:
    """Den letzten Bezug zurückgeben."""
    if not eintraege:
        return None
    return eintraege[-1]


def get_timeline(eintraege: list[dict], anzahl: int = 10) -> list[dict]:
    """Die letzten n Bezüge für die Timeline zurückgeben (neueste zuerst)."""
    return list(reversed(eintraege[-anzahl:]))
