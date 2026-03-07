"""Config Flow für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_MAX_TIMELINE_ENTRIES,
    CONF_MQTT_ALERT_TOPIC,
    CONF_MQTT_COMMAND_TOPIC,
    CONF_MQTT_DISPENSING_START_TOPIC,
    CONF_MQTT_INFO_TOPIC,
    CONF_MQTT_ONLINE_TOPIC,
    CONF_MQTT_TOPIC,
    DEFAULT_MAX_TIMELINE_ENTRIES,
    DEFAULT_MQTT_ALERT_TOPIC,
    DEFAULT_MQTT_COMMAND_TOPIC,
    DEFAULT_MQTT_DISPENSING_START_TOPIC,
    DEFAULT_MQTT_INFO_TOPIC,
    DEFAULT_MQTT_ONLINE_TOPIC,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
)
from .helpers import get_config

# Defaults-Mapping für Schema-Factory und Options-Flow
_ALL_DEFAULTS: dict[str, str | int] = {
    CONF_MQTT_TOPIC: DEFAULT_MQTT_TOPIC,
    CONF_MQTT_ONLINE_TOPIC: DEFAULT_MQTT_ONLINE_TOPIC,
    CONF_MQTT_ALERT_TOPIC: DEFAULT_MQTT_ALERT_TOPIC,
    CONF_MQTT_DISPENSING_START_TOPIC: DEFAULT_MQTT_DISPENSING_START_TOPIC,
    CONF_MQTT_INFO_TOPIC: DEFAULT_MQTT_INFO_TOPIC,
    CONF_MQTT_COMMAND_TOPIC: DEFAULT_MQTT_COMMAND_TOPIC,
    CONF_MAX_TIMELINE_ENTRIES: DEFAULT_MAX_TIMELINE_ENTRIES,
}


def _build_config_schema(defaults: dict) -> vol.Schema:
    """Erstellt das Topic-Schema mit gegebenen Defaults."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MQTT_TOPIC,
                default=defaults.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC),
            ): str,
            vol.Required(
                CONF_MQTT_ONLINE_TOPIC,
                default=defaults.get(CONF_MQTT_ONLINE_TOPIC, DEFAULT_MQTT_ONLINE_TOPIC),
            ): str,
            vol.Required(
                CONF_MQTT_ALERT_TOPIC,
                default=defaults.get(CONF_MQTT_ALERT_TOPIC, DEFAULT_MQTT_ALERT_TOPIC),
            ): str,
            vol.Required(
                CONF_MQTT_DISPENSING_START_TOPIC,
                default=defaults.get(CONF_MQTT_DISPENSING_START_TOPIC, DEFAULT_MQTT_DISPENSING_START_TOPIC),
            ): str,
            vol.Required(
                CONF_MQTT_INFO_TOPIC,
                default=defaults.get(CONF_MQTT_INFO_TOPIC, DEFAULT_MQTT_INFO_TOPIC),
            ): str,
            vol.Required(
                CONF_MQTT_COMMAND_TOPIC,
                default=defaults.get(CONF_MQTT_COMMAND_TOPIC, DEFAULT_MQTT_COMMAND_TOPIC),
            ): str,
            vol.Optional(
                CONF_MAX_TIMELINE_ENTRIES,
                default=defaults.get(CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES),
            ): vol.All(int, vol.Range(min=5, max=100)),
        }
    )


class KaffeemaschinConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow für Kaffeemaschine MQTT."""

    VERSION = 5

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ersten Schritt im Setup-Dialog behandeln."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC).strip()
            if not topic:
                errors[CONF_MQTT_TOPIC] = "invalid_topic"
            else:
                await self.async_set_unique_id(topic)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Kaffeemaschine ({topic})",
                    data={
                        key: user_input.get(key, default)
                        for key, default in _ALL_DEFAULTS.items()
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_config_schema(_ALL_DEFAULTS),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options Flow bereitstellen."""
        return KaffeemaschinenOptionsFlow()


class KaffeemaschinenOptionsFlow(config_entries.OptionsFlow):
    """Options Flow für Kaffeemaschine MQTT."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Options-Dialog anzeigen."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC).strip()
            if not topic:
                errors[CONF_MQTT_TOPIC] = "invalid_topic"
            else:
                return self.async_create_entry(title="", data=user_input)

        current = {
            key: get_config(self.config_entry, key, default)
            for key, default in _ALL_DEFAULTS.items()
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_build_config_schema(current),
            errors=errors,
        )
