"""Konstanten für die Kaffeemaschinen-Integration."""

DOMAIN = "kaffeemaschine"

# Konfigurationsschlüssel
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_MAX_TIMELINE_ENTRIES = "max_timeline_entries"

# Standardwerte
DEFAULT_MQTT_TOPIC = "kaffeemaschine/getraenk"
DEFAULT_MAX_TIMELINE_ENTRIES = 20

# Speicher
STORAGE_KEY = "kaffeemaschine_timeline"
STORAGE_VERSION = 1

# Unterstützte Getränketypen
GETRAENKE_TYPEN = [
    "Espresso",
    "Kaffee",
    "Cappuccino",
    "Latte Macchiato",
    "Americano",
    "Heisswasser",
    "Dampf",
]

# Sensor-Einzigartige Kennungen
SENSOR_LETZTES_GETRAENK = "letztes_getraenk"
SENSOR_BEZUEGE_HEUTE = "bezuege_heute"
SENSOR_BEZUEGE_GESAMT = "bezuege_gesamt"
SENSOR_LIEBLINGSGETRAENK = "lieblingsgetraenk"
SENSOR_TIMELINE = "timeline"

# Signal für Daten-Updates
SIGNAL_UPDATE = f"{DOMAIN}_update"
