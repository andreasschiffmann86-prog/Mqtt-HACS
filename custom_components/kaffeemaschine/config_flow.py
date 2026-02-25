"""Config Flow für die Kaffeemaschinen-Integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_MAX_TIMELINE_ENTRIES,
    CONF_MQTT_ONLINE_TOPIC,
    CONF_MQTT_TOPIC,
    DEFAULT_MAX_TIMELINE_ENTRIES,
    DEFAULT_MQTT_ONLINE_TOPIC,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
)


class KaffeemaschinConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow für Kaffeemaschine MQTT."""

    VERSION = 1

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
                        CONF_MQTT_TOPIC: topic,
                        CONF_MQTT_ONLINE_TOPIC: user_input.get(
                            CONF_MQTT_ONLINE_TOPIC, DEFAULT_MQTT_ONLINE_TOPIC
                        ),
                        CONF_MAX_TIMELINE_ENTRIES: user_input.get(
                            CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
                vol.Required(CONF_MQTT_ONLINE_TOPIC, default=DEFAULT_MQTT_ONLINE_TOPIC): str,
                vol.Optional(
                    CONF_MAX_TIMELINE_ENTRIES, default=DEFAULT_MAX_TIMELINE_ENTRIES
                ): vol.All(int, vol.Range(min=5, max=100)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options Flow bereitstellen."""
        return KaffeemaschinenOptionsFlow(config_entry)


class KaffeemaschinenOptionsFlow(config_entries.OptionsFlow):
    """Options Flow für Kaffeemaschine MQTT."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialisierung."""
        self.config_entry = config_entry

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

        current_topic = self.config_entry.options.get(
            CONF_MQTT_TOPIC,
            self.config_entry.data.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC),
        )
        current_online_topic = self.config_entry.options.get(
            CONF_MQTT_ONLINE_TOPIC,
            self.config_entry.data.get(CONF_MQTT_ONLINE_TOPIC, DEFAULT_MQTT_ONLINE_TOPIC),
        )
        current_max = self.config_entry.options.get(
            CONF_MAX_TIMELINE_ENTRIES,
            self.config_entry.data.get(
                CONF_MAX_TIMELINE_ENTRIES, DEFAULT_MAX_TIMELINE_ENTRIES
            ),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_MQTT_TOPIC, default=current_topic): str,
                vol.Required(CONF_MQTT_ONLINE_TOPIC, default=current_online_topic): str,
                vol.Optional(
                    CONF_MAX_TIMELINE_ENTRIES, default=current_max
                ): vol.All(int, vol.Range(min=5, max=100)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
