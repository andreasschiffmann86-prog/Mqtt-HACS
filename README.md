# Kaffeemaschine MQTT – Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1.0%2B-blue)](https://www.home-assistant.io/)

Eine vollständige **Home Assistant Custom Integration** (HACS-kompatibel) zur Auswertung von Kaffeemaschinen-Statistiken via **MQTT**. Die Integration empfängt Getränkedaten, speichert sie persistent und stellt Sensoren sowie eine Lovelace Card bereit.

---

## Funktionen

- 📡 Empfang von MQTT-Nachrichten mit Getränkedaten
- 💾 Persistente Speicherung des Bezugsverlaufs (Timeline)
- 📊 Sensoren für Statistiken (letztes Getränk, Tagesanzahl, Gesamtanzahl, Lieblingsgetränk)
- 🃏 Lovelace Card zur Anzeige der Timeline im modernen HA-Design
- ⚙️ Konfigurierbar über die UI (Config Flow + Options Flow)

---

## Voraussetzungen

- Home Assistant **2023.1.0** oder neuer
- Funktionierender **MQTT-Broker** (z.B. Mosquitto), konfiguriert in Home Assistant
- HACS (optional, für einfache Installation)

---

## Installation

### Via HACS (empfohlen)

1. HACS öffnen → **Integrationen** → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. URL dieses Repositories eingeben, Kategorie: **Integration**
3. **Kaffeemaschine MQTT** in der HACS-Liste suchen und installieren
4. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/kaffeemaschine/` in das Verzeichnis  
   `<config>/custom_components/kaffeemaschine/` kopieren
2. Den Ordner `www/kaffeemaschine-card/` in das Verzeichnis  
   `<config>/www/kaffeemaschine-card/` kopieren
3. Home Assistant neu starten

---

## Einrichtung

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Nach **Kaffeemaschine MQTT** suchen
3. MQTT-Topic eingeben (Standard: `kaffeemaschine/getraenk`)
4. Maximale Timeline-Einträge festlegen (Standard: 20, min: 5, max: 100)

---

## MQTT-Topic und Payload

**Standard-Topic:** `kaffeemaschine/getraenk` (konfigurierbar)

**Payload-Format (JSON):**

```json
{
  "getraenk": "Espresso",
  "menge_ml": 40,
  "temperatur": 92,
  "staerke": "stark",
  "zeitstempel": "2026-02-21T10:30:00"
}
```

| Feld          | Typ    | Pflicht | Beschreibung                          |
|---------------|--------|---------|---------------------------------------|
| `getraenk`    | String | Ja      | Name des Getränks                     |
| `menge_ml`    | Int    | Nein    | Bezogene Menge in Millilitern         |
| `temperatur`  | Int    | Nein    | Brühtemperatur in °C                  |
| `staerke`     | String | Nein    | Stärke (z.B. `stark`, `normal`)       |
| `zeitstempel` | String | Nein    | ISO 8601 Zeitstempel (sonst: jetzt)   |

**Unterstützte Getränketypen:**  
`Espresso`, `Kaffee`, `Cappuccino`, `Latte Macchiato`, `Americano`, `Heisswasser`, `Dampf`

---

## Sensoren

| Sensor                                  | Beschreibung                                  |
|-----------------------------------------|-----------------------------------------------|
| `sensor.kaffeemaschine_letztes_getraenk`| Letztes Getränk mit Attributen (Menge, Temperatur, Stärke, Zeitstempel) |
| `sensor.kaffeemaschine_bezuege_heute`   | Anzahl der Bezüge am heutigen Tag             |
| `sensor.kaffeemaschine_bezuege_gesamt`  | Gesamtanzahl aller gespeicherten Bezüge       |
| `sensor.kaffeemaschine_lieblingsgetraenk`| Meist bezogenes Getränk                     |
| `sensor.kaffeemaschine_timeline`        | Gesamtanzahl + Timeline als Attribut (letzte 20 Bezüge) |

---

## Lovelace Card

### Installation der Card

1. `www/kaffeemaschine-card/kaffeemaschine-card.js` in `<config>/www/kaffeemaschine-card/` ablegen
2. In Home Assistant unter **Einstellungen → Dashboards → Ressourcen** eine neue Ressource hinzufügen:
   - URL: `/local/kaffeemaschine-card/kaffeemaschine-card.js`
   - Typ: **JavaScript-Modul**

### Konfiguration

```yaml
type: custom:kaffeemaschine-card
entity: sensor.kaffeemaschine_timeline
title: Kaffeemaschine        # optional
max_entries: 10              # optional, Standard: 10
```

Die Card zeigt:
- **Header** mit dem konfigurierten Titel
- **Statistik-Leiste:** Bezüge heute / Gesamt / Lieblingsgetränk
- **Timeline** der letzten Bezüge mit Icon, Name, Details und Zeitstempel

---

## Beispiel: Sensor-Automatisierung

```yaml
automation:
  - alias: "Kaffee-Benachrichtigung"
    trigger:
      - platform: state
        entity_id: sensor.kaffeemaschine_letztes_getraenk
    action:
      - service: notify.mobile_app
        data:
          message: >
            ☕ {{ states('sensor.kaffeemaschine_letztes_getraenk') }} bezogen!
            Heute bereits {{ states('sensor.kaffeemaschine_bezuege_heute') }} Bezüge.
```

---

## Test mit mosquitto_pub

```bash
mosquitto_pub -h <broker-ip> -t kaffeemaschine/getraenk -m '{
  "getraenk": "Espresso",
  "menge_ml": 40,
  "temperatur": 92,
  "staerke": "stark",
  "zeitstempel": "2026-02-21T10:30:00"
}'
```

---

## Technische Details

- Vollständig **async/await**
- Persistente Speicherung mit `homeassistant.helpers.storage.Store`
- Fehlerbehandlung bei ungültigen JSON-Payloads (Warnung im Log, kein Absturz)
- Config Flow + Options Flow für UI-Konfiguration
- HACS-kompatibel (`hacs.json`)
- Übersetzungen: Deutsch 🇩🇪 und Englisch 🇬🇧

---

## Lizenz

MIT License