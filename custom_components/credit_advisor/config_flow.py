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
            if user_input.get("agent_id"):
                options["agent_id"] = user_input["agent_id"]
            if user_input.get("storage_path"):
                options["storage_path"] = user_input["storage_path"]
            return self.async_create_entry(title="Credit Card Advisor", data={}, options=options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "agent_id",
                        description="The conversation agent to use for card research (e.g. conversation.openai_home).",
                    ): selector.ConversationAgentSelector(),
                    vol.Optional(
                        "storage_path",
                        description="Override the default storage directory. Leave empty to use the default.",
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "agent_id",
                        default=agent_id,
                        description="The conversation agent to use for card research.",
                    ): selector.ConversationAgentSelector(),
                    vol.Optional(
                        "storage_path",
                        default=storage_path,
                        description="Override the default storage directory.",
                    ): str,
                }
            ),
        )
