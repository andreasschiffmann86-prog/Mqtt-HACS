# ☕ Kaffeemaschine Statistik

Home Assistant Custom Integration für **Kaffeemaschinen-Statistik via MQTT** – HACS-kompatibel.

---

## Übersicht & Features

- 📡 **MQTT-Empfang**: Empfängt Getränkedaten von deiner Kaffeemaschine in Echtzeit
- 📊 **Statistiken**: Bezüge heute, Gesamtanzahl, Lieblingsgetränk
- 🕒 **Timeline**: Persistenter Verlauf der letzten Getränkebezüge (bis zu 1000 Einträge)
- 🃏 **Lovelace Card**: Moderne Custom Card für die Timeline-Ansicht
- 🔄 **Persistenz**: Daten überleben Home Assistant Neustarts

---

## Voraussetzungen

- Home Assistant **2023.1.0** oder neuer
- Funktionierender **MQTT Broker** (z.B. Mosquitto)
- MQTT-Integration in Home Assistant bereits eingerichtet
- Kaffeemaschine (oder Gerät) sendet MQTT-Nachrichten im vorgegebenen JSON-Format

---

## Installation via HACS

1. Öffne **HACS** → **Integrationen**
2. Klicke auf die drei Punkte (⋮) → **Benutzerdefinierte Repositories**
3. Repository-URL eingeben: `https://github.com/andreasschiffmann86-prog/Mqtt-HACS`
4. Kategorie: **Integration** → **Hinzufügen**
5. Suche nach „Kaffeemaschine Statistik" und klicke auf **Herunterladen**
6. Home Assistant neu starten

### Lovelace Card installieren (HACS)

1. Öffne **HACS** → **Frontend**
2. Benutzerdefiniertes Repository hinzufügen (gleiche URL, Kategorie: **Lovelace**)
3. „Kaffeemaschine Card" herunterladen
4. HA neu starten oder Lovelace-Ressourcen neu laden

---

## Manuelle Installation

1. Lade das Repository als ZIP herunter und entpacke es
2. Kopiere den Ordner `custom_components/kaffeemaschine/` in dein HA-Verzeichnis:
   ```
   <config>/custom_components/kaffeemaschine/
   ```
3. Kopiere `www/kaffeemaschine-card/kaffeemaschine-card.js` nach:
   ```
   <config>/www/kaffeemaschine-card/kaffeemaschine-card.js
   ```
4. Füge die Lovelace-Ressource in `configuration.yaml` ein (oder über die UI):
   ```yaml
   lovelace:
     resources:
       - url: /local/kaffeemaschine-card/kaffeemaschine-card.js
         type: module
   ```
5. Home Assistant neu starten

---

## Konfiguration

### Config Flow (empfohlen)

1. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Suche nach „Kaffeemaschine Statistik"
3. Fülle die Felder aus:

| Feld | Beschreibung | Standard |
|------|-------------|---------|
| Name | Anzeigename der Integration | `Meine Kaffeemaschine` |
| MQTT Topic | Topic, auf dem deine Maschine publiziert | `kaffeemaschine/getraenk` |
| QoS | MQTT Quality of Service (0, 1 oder 2) | `0` |

### Lovelace Card einrichten

Füge die Card in dein Dashboard ein:

```yaml
type: custom:kaffeemaschine-card
entity: sensor.kaffeemaschine_timeline
title: "☕ Meine Kaffeemaschine"
```

---

## MQTT Payload Format

Deine Kaffeemaschine muss JSON-Nachrichten in folgendem Format senden:

```json
{
  "getraenk": "Espresso",
  "menge_ml": 40,
  "temperatur": 92,
  "staerke": "stark",
  "zeitstempel": "2026-02-21T10:30:00"
}
```

### Unterstützte Getränketypen

| Getränk | Icon |
|---------|------|
| Espresso | ☕ |
| Kaffee | ☕ |
| Cappuccino | 🍵 |
| Latte Macchiato | 🥛 |
| Americano | ☕ |
| Heißwasser | 💧 |
| Dampf | 💨 |

### Beispiel-Payloads

```json
{ "getraenk": "Cappuccino", "menge_ml": 150, "temperatur": 70, "staerke": "mittel", "zeitstempel": "2026-02-21T08:00:00" }
{ "getraenk": "Espresso", "menge_ml": 40, "temperatur": 92, "staerke": "stark", "zeitstempel": "2026-02-21T10:30:00" }
{ "getraenk": "Latte Macchiato", "menge_ml": 300, "temperatur": 65, "staerke": "mild", "zeitstempel": "2026-02-21T14:15:00" }
```

---

## Sensor-Übersicht

| Sensor | Beschreibung | Einheit |
|--------|-------------|---------|
| `sensor.kaffeemaschine_letztes_getraenk` | Name des zuletzt bezogenen Getränks | – |
| `sensor.kaffeemaschine_bezuege_heute` | Anzahl Bezüge am heutigen Tag | Bezüge |
| `sensor.kaffeemaschine_bezuege_gesamt` | Gesamtanzahl aller Bezüge | Bezüge |
| `sensor.kaffeemaschine_lieblingsgetraenk` | Am häufigsten bezogenes Getränk | – |
| `sensor.kaffeemaschine_timeline` | Anzahl Timeline-Einträge + letzte 20 Bezüge als Attribut | – |

### Attribute von `sensor.kaffeemaschine_letztes_getraenk`

```yaml
menge_ml: 40
temperatur: 92
staerke: "stark"
zeitstempel: "2026-02-21T10:30:00"
```

### Attribute von `sensor.kaffeemaschine_timeline`

```yaml
entries:
  - zeitstempel: "2026-02-21T10:30:00"
    getraenk: "Espresso"
    menge_ml: 40
    temperatur: 92
    staerke: "stark"
```

---

## Beispiel Lovelace Dashboard (YAML)

```yaml
views:
  - title: Kaffeemaschine
    cards:
      - type: custom:kaffeemaschine-card
        entity: sensor.kaffeemaschine_timeline
        title: "☕ Meine Kaffeemaschine"

      - type: entities
        title: Statistiken
        entities:
          - sensor.kaffeemaschine_bezuege_heute
          - sensor.kaffeemaschine_bezuege_gesamt
          - sensor.kaffeemaschine_lieblingsgetraenk
          - sensor.kaffeemaschine_letztes_getraenk

      - type: history-graph
        title: Bezüge heute
        entities:
          - sensor.kaffeemaschine_bezuege_heute
```

---

## Troubleshooting

### Integration erscheint nicht in HA

- Stelle sicher, dass der Ordner korrekt unter `custom_components/kaffeemaschine/` liegt
- Prüfe, ob die MQTT-Integration in HA konfiguriert ist
- Schaue in die HA-Logs unter **Einstellungen** → **System** → **Logs**

### Keine MQTT-Nachrichten werden empfangen

- Prüfe das Topic in der Integrationskonfiguration
- Teste mit einem MQTT-Client (z.B. MQTT Explorer):
  ```
  mosquitto_pub -h <broker> -t kaffeemaschine/getraenk -m '{"getraenk":"Espresso","menge_ml":40,"temperatur":92,"staerke":"stark","zeitstempel":"2026-02-21T10:30:00"}'
  ```
- Stelle sicher, dass der QoS-Level übereinstimmt

### Lovelace Card wird nicht angezeigt

- Prüfe, ob die Ressource in den Lovelace-Einstellungen registriert ist
- Leere den Browser-Cache (Strg+Shift+R)
- Prüfe die Browser-Konsole auf JavaScript-Fehler

### Sensoren zeigen veraltete Werte

- Sensoren werden bei jeder MQTT-Nachricht aktualisiert
- Prüfe den MQTT-Broker-Status
- HA-Logs auf Fehler prüfen

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

---

*Entwickelt von [@andreasschiffmann86-prog](https://github.com/andreasschiffmann86-prog)*