"""Konstanten für die Kaffeemaschinen-Integration."""

DOMAIN = "kaffeemaschine"

# Konfigurationsschlüssel
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_MQTT_ONLINE_TOPIC = "mqtt_online_topic"
CONF_MQTT_ALERT_TOPIC = "mqtt_alert_topic"
CONF_MQTT_DISPENSING_START_TOPIC = "mqtt_dispensing_start_topic"
CONF_MQTT_INFO_TOPIC = "mqtt_info_topic"
CONF_MQTT_COMMAND_TOPIC = "mqtt_command_topic"
CONF_MAX_TIMELINE_ENTRIES = "max_timeline_entries"

# Standardwerte
DEFAULT_MQTT_TOPIC = "kaffeemaschine/getraenk"
DEFAULT_MQTT_ONLINE_TOPIC = "status/lwt"
DEFAULT_MQTT_ALERT_TOPIC = "kaffeemaschine/alert"
DEFAULT_MQTT_DISPENSING_START_TOPIC = "kaffeemaschine/dispensing_start"
DEFAULT_MQTT_INFO_TOPIC = "pcm/Zehnt/equipment/coffee01/144/info"
DEFAULT_MQTT_COMMAND_TOPIC = "pcm/Zehnt/equipment/coffee01/144/command/start_beverage"
DEFAULT_MAX_TIMELINE_ENTRIES = 20

# Speicher
STORAGE_KEY = "kaffeemaschine_timeline"
STORAGE_VERSION = 1

# Sensor-Einzigartige Kennungen
SENSOR_LETZTES_GETRAENK = "letztes_getraenk"
SENSOR_BEZUEGE_HEUTE = "bezuege_heute"
SENSOR_BEZUEGE_GESAMT = "bezuege_gesamt"
SENSOR_LIEBLINGSGETRAENK = "lieblingsgetraenk"
SENSOR_TIMELINE = "timeline"
SENSOR_GERAETE_INFO = "geraete_info"
SENSOR_LETZTER_BEZUG_STATUS = "letzter_bezug_status"
SENSOR_ALERT_TIMELINE = "alert_timeline"
SENSOR_PRODUKTION_LAUFEND = "produktion_laufend"
SENSOR_GERAETE_MENU = "geraete_menu"

# Binary Sensor
BINARY_SENSOR_ONLINE = "online"

# Signal für Daten-Updates
SIGNAL_UPDATE = f"{DOMAIN}_update"
SIGNAL_ONLINE_UPDATE = f"{DOMAIN}_online_update"
SIGNAL_ALERT_UPDATE = f"{DOMAIN}_alert_update"
SIGNAL_PRODUKTION_UPDATE = f"{DOMAIN}_produktion_update"
SIGNAL_INFO_UPDATE = f"{DOMAIN}_info_update"

# Service-Namen
SERVICE_BESTELLEN = "bestellen"
