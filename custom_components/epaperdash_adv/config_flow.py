"""Config flow for EpaperDash-ADV."""
from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    COLOR_MODES,
    CONF_COLOR_MODE,
    CONF_DASHBOARD_PATH,
    CONF_DITHER,
    CONF_HEIGHT,
    CONF_LONG_LIVED_TOKEN,
    CONF_REFRESH_INTERVAL,
    CONF_ROTATION,
    CONF_WIDTH,
    DATA_ACCESS_TOKEN,
    DEFAULT_COLOR_MODE,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_DITHER,
    DEFAULT_HEIGHT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_ROTATION,
    DEFAULT_WIDTH,
    DOMAIN,
    MIN_REFRESH_INTERVAL,
    ROTATIONS,
)


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_DASHBOARD_PATH, default=defaults.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH)
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_WIDTH, default=defaults.get(CONF_WIDTH, DEFAULT_WIDTH)
            ): NumberSelector(NumberSelectorConfig(min=100, max=3000, mode=NumberSelectorMode.BOX)),
            vol.Required(
                CONF_HEIGHT, default=defaults.get(CONF_HEIGHT, DEFAULT_HEIGHT)
            ): NumberSelector(NumberSelectorConfig(min=100, max=3000, mode=NumberSelectorMode.BOX)),
            vol.Required(
                CONF_ROTATION, default=str(defaults.get(CONF_ROTATION, DEFAULT_ROTATION))
            ): SelectSelector(
                SelectSelectorConfig(options=[str(r) for r in ROTATIONS])
            ),
            vol.Required(
                CONF_COLOR_MODE, default=defaults.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE)
            ): SelectSelector(SelectSelectorConfig(options=COLOR_MODES)),
            vol.Required(
                CONF_DITHER, default=defaults.get(CONF_DITHER, DEFAULT_DITHER)
            ): BooleanSelector(),
            vol.Required(
                CONF_REFRESH_INTERVAL,
                default=defaults.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(min=MIN_REFRESH_INTERVAL, max=86400, mode=NumberSelectorMode.BOX)
            ),
        }
    )


class EpaperDashAdvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of an EpaperDash-ADV entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._token = user_input[CONF_LONG_LIVED_TOKEN]
            return await self.async_step_settings()

        schema = vol.Schema(
            {
                vol.Required(CONF_LONG_LIVED_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_settings(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            data = {
                CONF_LONG_LIVED_TOKEN: self._token,
                DATA_ACCESS_TOKEN: secrets.token_urlsafe(32),
            }
            options = {
                CONF_DASHBOARD_PATH: user_input[CONF_DASHBOARD_PATH],
                CONF_WIDTH: int(user_input[CONF_WIDTH]),
                CONF_HEIGHT: int(user_input[CONF_HEIGHT]),
                CONF_ROTATION: int(user_input[CONF_ROTATION]),
                CONF_COLOR_MODE: user_input[CONF_COLOR_MODE],
                CONF_DITHER: user_input[CONF_DITHER],
                CONF_REFRESH_INTERVAL: int(user_input[CONF_REFRESH_INTERVAL]),
            }
            return self.async_create_entry(
                title=f"EpaperDash-ADV ({options[CONF_DASHBOARD_PATH]})",
                data=data,
                options=options,
            )

        return self.async_show_form(
            step_id="settings", data_schema=_settings_schema({})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EpaperDashAdvOptionsFlow(config_entry)


class EpaperDashAdvOptionsFlow(OptionsFlow):
    """Allow changing dashboard path, resolution and refresh settings later."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            options = {
                CONF_DASHBOARD_PATH: user_input[CONF_DASHBOARD_PATH],
                CONF_WIDTH: int(user_input[CONF_WIDTH]),
                CONF_HEIGHT: int(user_input[CONF_HEIGHT]),
                CONF_ROTATION: int(user_input[CONF_ROTATION]),
                CONF_COLOR_MODE: user_input[CONF_COLOR_MODE],
                CONF_DITHER: user_input[CONF_DITHER],
                CONF_REFRESH_INTERVAL: int(user_input[CONF_REFRESH_INTERVAL]),
            }
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init", data_schema=_settings_schema(self._config_entry.options)
        )
