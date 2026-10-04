"""Config and options flow for Audioengine Infrared."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
    async_get_receivers,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from .const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DEFAULT_NAME,
    DOMAIN,
)


def _suggest(value: Any) -> dict[str, Any]:
    return {"suggested_value": value} if value is not None else {}


@callback
def _settings_schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    """Schema shared by the setup and options forms (everything but the name)."""
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_INFRARED_ENTITY_ID,
            description=_suggest(current.get(CONF_INFRARED_ENTITY_ID)),
        ): EntitySelector(
            EntitySelectorConfig(
                domain=INFRARED_DOMAIN, include_entities=async_get_emitters(hass)
            )
        ),
    }
    if receivers := async_get_receivers(hass):
        fields[
            vol.Optional(
                CONF_INFRARED_RECEIVER_ENTITY_ID,
                description=_suggest(current.get(CONF_INFRARED_RECEIVER_ENTITY_ID)),
            )
        ] = EntitySelector(
            EntitySelectorConfig(domain=INFRARED_DOMAIN, include_entities=receivers)
        )
    return vol.Schema(fields)


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    """Store a cleared receiver as None."""
    data = dict(user_input)
    data[CONF_INFRARED_RECEIVER_ENTITY_ID] = (
        data.get(CONF_INFRARED_RECEIVER_ENTITY_ID) or None
    )
    return data


class AudioengineInfraredConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return AudioengineInfraredOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single-step setup: name, emitter and optional receiver."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_infrared_entities")

        if user_input is not None:
            data = _normalise(user_input)
            name = data.pop(CONF_NAME).strip() or DEFAULT_NAME
            return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector()}
        ).extend(_settings_schema(self.hass, {}).schema)
        return self.async_show_form(step_id="user", data_schema=schema)


class AudioengineInfraredOptionsFlow(OptionsFlow):
    """Let the emitter and receiver be changed after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options form."""
        if user_input is not None:
            return self.async_create_entry(data=_normalise(user_input))

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_settings_schema(self.hass, current)
        )
