# ☕ Kaffeemaschine Statistik

Home Assistant Custom Integration für **Kaffeemaschinen-Statistik und Alert-Monitoring via MQTT** – HACS-kompatibel.

---

## Features

| Feature | Beschreibung |
|---------|-------------|
| 📡 **MQTT-Empfang** | Getränkedaten und Alerts in Echtzeit |
| 📊 **Statistiken** | Bezüge heute, Gesamtanzahl, Lieblingsgetränk |
| 🕒 **Timeline** | Persistenter Verlauf (bis zu 1000 Einträge) |
| 🚨 **Alert-Monitoring** | RAISE/CLEAR Alerts mit Live-Timer |
| 🔌 **Offline-Erkennung** | Automatisches Schließen offener Alerts bei Verbindungsverlust |
| 🃏 **Lovelace Card** | Drei Darstellungsmodi: Timeline, Alert-Status, Balkendiagramm |
| 🔄 **Persistenz** | Daten überleben Home Assistant Neustarts |

---

## Voraussetzungen

- Home Assistant **2024.1.0** oder neuer
- Funktionierender **MQTT Broker** (z.B. Mosquitto)
- MQTT-Integration in Home Assistant eingerichtet
- Kaffeemaschine sendet MQTT-Nachrichten im beschriebenen JSON-Format

---

## Installation via HACS

1. Öffne **HACS** → **Integrationen**
2. Klicke auf ⋮ → **Benutzerdefinierte Repositories**
3. URL eingeben: `https://github.com/andreasschiffmann86-prog/Mqtt-HACS`
4. Kategorie: **Integration** → **Hinzufügen**
5. „Kaffeemaschine Statistik" suchen und **Herunterladen** klicken
6. Home Assistant neu starten

### Lovelace Card (HACS)

1. **HACS** → **Frontend** → Benutzerdefiniertes Repository hinzufügen (gleiche URL, Kategorie: **Lovelace**)
2. „Kaffeemaschine Card" herunterladen
3. Browser-Cache leeren (`Strg+Shift+R`)

---

## Manuelle Installation

```
custom_components/kaffeemaschine/   →  <config>/custom_components/kaffeemaschine/
www/kaffeemaschine-card/            →  <config>/www/kaffeemaschine-card/
```

Lovelace-Ressource in `configuration.yaml` eintragen:

```yaml
lovelace:
  resources:
    - url: /local/kaffeemaschine-card/kaffeemaschine-card.js
      type: module
```

---

## Konfiguration

**Einstellungen → Geräte & Dienste → Integration hinzufügen → „Kaffeemaschine Statistik"**

| Feld | Beschreibung | Beispiel |
|------|-------------|---------|
| Name | Anzeigename | `Kaffeemaschine Büro` |
| MQTT Topic (Getränke) | Topic für Bezugsdaten | `pcm/store01/equipment/coffee01/123/beverages` |
| MQTT Topic (Online-Status) | Topic für Konnektivität | `pcm/store01/equipment/coffee01/123/connectivity` |
| MQTT Topic (Alerts) | Basis-Topic für Alerts (Wildcard `#` wird intern ergänzt) | `pcm/store01/equipment/coffee01/123/alerts` |

---

## MQTT Topics & Payload-Formate

### Getränkebezug

**Topic:** `pcm/store01/equipment/coffee01/123/beverages`

```json
{
  "messageType": "BEVERAGE_DISPENSING_FINISHED",
  "messageId": "abc-123",
  "timestamp": "2026-02-27T10:30:00Z",
  "device": {
    "model": "SuperCoffee 3000",
    "serialNumber": "123",
    "manufacturer": "Kaffeemaschinen GmbH",
    "softwareVersion": "2.9.0"
  },
  "storeId": "store01",
  "payload": {
    "beverageName": "Espresso",
    "beverageId": 1,
    "amount": 40,
    "temperature": 92,
    "cupSize": 1,
    "isDouble": false,
    "cycleTime": 28000,
    "extractionTime": 25000,
    "strokes": 1,
    "canceled": false,
    "ingredients": [
      { "type": 18, "amount": 8, "unit": 2 },
      { "type": 0,  "amount": 40, "unit": 1 }
    ]
  }
}
```

### Online-Status / Konnektivität

**Topic:** `pcm/store01/equipment/coffee01/123/connectivity`

```json
{
  "messageType": "CONNECTIVITY_CHANGED",
  "messageId": "def-456",
  "timestamp": "2026-02-27T10:00:00Z",
  "device": { "serialNumber": "123" },
  "storeId": "store01",
  "payload": {
    "online": true
  }
}
```

> Wenn `online: false` empfangen wird, werden alle offenen Alerts automatisch geschlossen.

### Alert RAISE

**Topic:** `pcm/store01/equipment/coffee01/123/alerts/raise`

```json
{
  "messageType": "ALERT_RAISE",
  "messageId": "ghi-789",
  "timestamp": "2026-02-27T10:45:00Z",
  "device": {
    "model": "SuperCoffee 3000",
    "serialNumber": "123",
    "manufacturer": "Kaffeemaschinen GmbH",
    "softwareVersion": "2.9.0",
    "firmwareVersion": "1.2.3"
  },
  "storeId": "store01",
  "payload": {
    "alertId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "category": "MACHINE",
    "description": "Error 68",
    "errorCode": 68,
    "severity": "STANDARD"
  }
}
```

### Alert CLEAR

**Topic:** `pcm/store01/equipment/coffee01/123/alerts/clear`

```json
{
  "messageType": "ALERT_CLEAR",
  "messageId": "jkl-012",
  "timestamp": "2026-02-27T10:50:00Z",
  "device": { "serialNumber": "123" },
  "storeId": "store01",
  "payload": {
    "alertId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
}
```

> Die Integration abonniert intern `alert_topic/#`, sodass beide Subtopics (`/raise`, `/clear`) automatisch empfangen werden.

---

## Sensor-Übersicht

| Sensor | Beschreibung |
|--------|-------------|
| `sensor.<name>_timeline` | Anzahl Timeline-Einträge + Verlauf der Bezüge als Attribut |
| `sensor.<name>_bezuge_heute` | Anzahl Bezüge am heutigen Tag |
| `sensor.<name>_bezuge_gesamt` | Gesamtanzahl aller Bezüge |
| `sensor.<name>_lieblingsgetrank` | Am häufigsten bezogenes Getränk |
| `sensor.<name>_letztes_getrank` | Zuletzt bezogenes Getränk |
| `sensor.<name>_letzter_bezug_status` | Status des letzten Bezugs (OK / Abgebrochen) |
| `sensor.<name>_gerate_info` | Gerätemodell und Seriennummer |
| `sensor.<name>_alert_timeline` | Anzahl offener Alerts + Alert-Liste als Attribut |
| `binary_sensor.<name>_konnektivitat` | Online-Status der Maschine (`on` = online) |

### Attribute von `sensor.<name>_alert_timeline`

```yaml
open_count: 1
open_alerts:
  - alertId: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    category: "MACHINE"
    description: "Error 68"
    errorCode: 68
    severity: "STANDARD"
    raiseTime: "2026-02-27T10:45:00+00:00"
    clearTime: null
    status: "offen"
    duration: "5m 12s"
    duration_seconds: 312
    storeId: "store01"
all_alerts:
  - ...  # alle Alerts (offen + geschlossen), neueste zuerst
```

---

## Lovelace Card

### Modus 1: Timeline-Card (Standard)

```yaml
type: custom:kaffeemaschine-card
entity: sensor.kaffeemaschine_timeline
online_entity: binary_sensor.kaffeemaschine_konnektivitat
title: "☕ Kaffeemaschine"
max_entries: 10
```

Zeigt Getränke-Timeline mit Statistiken (Heute / Gesamt / Lieblingsgetränk) und Online-Indikator.

---

### Modus 2: Alert-Card (`alert_only: true`)

```yaml
type: custom:kaffeemaschine-card
alert_only: true
alert_entity: sensor.kaffeemaschine_alert_timeline
online_entity: binary_sensor.kaffeemaschine_konnektivitat
title: "Maschinenstatus"
```

| Zustand | Header-Farbe | Darstellung |
|---------|-------------|-------------|
| Online, keine Alerts | Grün | „Alle Systeme in Ordnung" |
| Online, Alerts offen | Rot | Offene Alerts mit Live-Sekundentimer |
| Offline | Grau | Gedimmt, Hinweis „Keine Verbindung" |

---

### Modus 3: Balkendiagramm (`chart_only: true`)

```yaml
type: custom:kaffeemaschine-card
chart_only: true
entity: sensor.kaffeemaschine_timeline
title: "Getränke Übersicht"
```

Drei umschaltbare Zeiträume per Tab: **Heute** · **Diese Woche** · **Gesamt**

---

### Vollständiges Dashboard-Beispiel

```yaml
views:
  - title: Kaffeemaschine
    cards:
      - type: custom:kaffeemaschine-card
        entity: sensor.kaffeemaschine_timeline
        online_entity: binary_sensor.kaffeemaschine_konnektivitat
        title: "☕ Kaffeemaschine"
        max_entries: 10

      - type: custom:kaffeemaschine-card
        alert_only: true
        alert_entity: sensor.kaffeemaschine_alert_timeline
        online_entity: binary_sensor.kaffeemaschine_konnektivitat
        title: "Maschinenstatus"

      - type: custom:kaffeemaschine-card
        chart_only: true
        entity: sensor.kaffeemaschine_timeline
        title: "Getränke Übersicht"

      - type: entities
        title: Statistiken
        entities:
          - binary_sensor.kaffeemaschine_konnektivitat
          - sensor.kaffeemaschine_bezuge_heute
          - sensor.kaffeemaschine_bezuge_gesamt
          - sensor.kaffeemaschine_lieblingsgetrank
          - sensor.kaffeemaschine_letztes_getrank
          - sensor.kaffeemaschine_gerate_info
```

---

## Automatisierungs-Beispiele

### Benachrichtigung bei offenem Alert

```yaml
automation:
  - alias: "Kaffeemaschine Alert öffnet"
    trigger:
      - platform: state
        entity_id: sensor.kaffeemaschine_alert_timeline
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "☕ Kaffeemaschine Alert"
          message: >
            {{ state_attr('sensor.kaffeemaschine_alert_timeline', 'open_alerts')[0].description }}
            (Code {{ state_attr('sensor.kaffeemaschine_alert_timeline', 'open_alerts')[0].errorCode }})
```

### Benachrichtigung bei Verbindungsverlust

```yaml
automation:
  - alias: "Kaffeemaschine Offline"
    trigger:
      - platform: state
        entity_id: binary_sensor.kaffeemaschine_konnektivitat
        to: "off"
        for: "00:02:00"
    action:
      - service: notify.mobile_app
        data:
          title: "☕ Kaffeemaschine offline"
          message: "Die Kaffeemaschine hat seit 2 Minuten keine Verbindung."
```

---

## MQTT-Test mit mosquitto_pub

```bash
# Getränkebezug simulieren
mosquitto_pub -h <broker-ip> \
  -t "pcm/store01/equipment/coffee01/123/beverages" \
  -m '{"messageType":"BEVERAGE_DISPENSING_FINISHED","messageId":"test-001","timestamp":"2026-02-27T10:30:00Z","device":{"model":"TestMaschine","serialNumber":"123","manufacturer":"Test GmbH","softwareVersion":"1.0"},"storeId":"store01","payload":{"beverageName":"Espresso","beverageId":1,"amount":40,"temperature":92,"canceled":false}}'

# Alert auslösen
mosquitto_pub -h <broker-ip> \
  -t "pcm/store01/equipment/coffee01/123/alerts/raise" \
  -m '{"messageType":"ALERT_RAISE","messageId":"test-002","timestamp":"2026-02-27T10:45:00Z","device":{"serialNumber":"123"},"storeId":"store01","payload":{"alertId":"aaaaaaaa-0000-0000-0000-bbbbbbbbbbbb","category":"MACHINE","description":"Testfehler","errorCode":99,"severity":"STANDARD"}}'

# Alert schließen
mosquitto_pub -h <broker-ip> \
  -t "pcm/store01/equipment/coffee01/123/alerts/clear" \
  -m '{"messageType":"ALERT_CLEAR","messageId":"test-003","timestamp":"2026-02-27T10:50:00Z","device":{"serialNumber":"123"},"storeId":"store01","payload":{"alertId":"aaaaaaaa-0000-0000-0000-bbbbbbbbbbbb"}}'
```

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Integration erscheint nicht | Ordner korrekt unter `custom_components/kaffeemaschine/`? HA-Logs prüfen. |
| Keine MQTT-Nachrichten | Topic in der Konfiguration prüfen. Mit MQTT Explorer testen. |
| Alerts kommen nicht an | Alert-Topic prüfen – die Integration ergänzt intern `/#`. Basis-Topic ohne abschließendes `/` konfigurieren. |
| Timer zeigt „?" | Die Integration verwendet intern immer UTC-Serverzeit – Payload-Timestamp wird ignoriert. |
| Card lädt nicht | Browser-Cache leeren (`Strg+Shift+R`). Lovelace-Ressource registriert? Browser-Konsole auf JS-Fehler prüfen. |
| HTTP 500 beim Öffnen der Optionen | Integration deaktivieren und neu aktivieren – Config Entry Migration auf Version 2 läuft automatisch. |

### HA-Logs prüfen

**Einstellungen → System → Logs** → nach `kaffeemaschine` filtern.

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

---

*Entwickelt von [@andreasschiffmann86-prog](https://github.com/andreasschiffmann86-prog)*