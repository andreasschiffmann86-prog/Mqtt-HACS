"""Config flow for Kaffeemaschine integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_QOS = "qos"
DEFAULT_QOS = 0


class KaffeeMaschineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kaffeemaschine."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input.get(CONF_TOPIC, "").strip()
            if not topic:
                errors[CONF_TOPIC] = "topic_required"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{topic}_{user_input.get(CONF_NAME, 'kaffeemaschine')}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Kaffeemaschine"),
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Meine Kaffeemaschine"): str,
                vol.Required(CONF_TOPIC, default=DEFAULT_TOPIC): str,
                vol.Optional(CONF_QOS, default=DEFAULT_QOS): vol.In([0, 1, 2]),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
