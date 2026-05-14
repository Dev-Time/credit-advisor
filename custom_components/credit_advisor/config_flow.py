"""Config flow for Credit Card Advisor integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN


class CreditAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Credit Card Advisor."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return CreditAdvisorOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            options = {}
            if "agent_id" in user_input:
                options["agent_id"] = user_input["agent_id"]
            if user_input.get("storage_path"):
                options["storage_path"] = user_input["storage_path"]
            return self.async_create_entry(title="Credit Card Advisor", data={}, options=options)

        default_path = self.hass.config.path(DOMAIN)
        storage_description = f"Directory for card YAML files. Defaults to {default_path} (typically /config/credit_advisor/). Leave empty to use the default."

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("agent_id"): selector.ConversationAgentSelector(),
                    vol.Optional(
                        "storage_path",
                        description=storage_description,
                    ): str,
                }
            ),
        )


class CreditAdvisorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Credit Card Advisor."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        agent_id = self.config_entry.options.get("agent_id", "")
        storage_path = self.config_entry.options.get("storage_path", "")

        default_path = self.hass.config.path(DOMAIN)
        storage_description = f"Directory for card YAML files. Defaults to {default_path} (typically /config/credit_advisor/). Leave empty to use the default."

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "agent_id", default=agent_id
                    ): selector.ConversationAgentSelector(),
                    vol.Optional(
                        "storage_path",
                        default=storage_path,
                        description=storage_description,
                    ): str,
                }
            ),
        )
