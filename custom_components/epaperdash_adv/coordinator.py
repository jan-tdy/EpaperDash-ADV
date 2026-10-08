"""Data update coordinator for EpaperDash-ADV."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_COLOR_MODE,
    CONF_DASHBOARD_PATH,
    CONF_DITHER,
    CONF_HEIGHT,
    CONF_LONG_LIVED_TOKEN,
    CONF_REFRESH_INTERVAL,
    CONF_ROTATION,
    CONF_WIDTH,
    DEFAULT_COLOR_MODE,
    DEFAULT_DITHER,
    DEFAULT_HEIGHT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_ROTATION,
    DEFAULT_WIDTH,
    DOMAIN,
)
from .renderer import DashboardRenderer, RendererError

_LOGGER = logging.getLogger(__name__)


class EpaperDashCoordinator(DataUpdateCoordinator[bytes]):
    """Periodically captures the configured dashboard view."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        options = entry.options

        self.renderer = DashboardRenderer(
            hass=hass,
            base_url=hass.config.internal_url or hass.config.external_url or "http://localhost:8123",
            dashboard_path=options.get(CONF_DASHBOARD_PATH, entry.data.get(CONF_DASHBOARD_PATH)),
            access_token=entry.data[CONF_LONG_LIVED_TOKEN],
            width=options.get(CONF_WIDTH, DEFAULT_WIDTH),
            height=options.get(CONF_HEIGHT, DEFAULT_HEIGHT),
            rotation=options.get(CONF_ROTATION, DEFAULT_ROTATION),
            color_mode=options.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE),
            dither=options.get(CONF_DITHER, DEFAULT_DITHER),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(
                seconds=options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> bytes:
        try:
            return await self.renderer.async_capture()
        except RendererError as err:
            raise UpdateFailed(str(err)) from err

    async def async_apply_options(self) -> None:
        """Re-apply options (e.g. refresh interval) after an options update."""
        options = self.entry.options
        self.renderer.update_settings(
            dashboard_path=options.get(CONF_DASHBOARD_PATH, self.entry.data.get(CONF_DASHBOARD_PATH)),
            width=options.get(CONF_WIDTH, DEFAULT_WIDTH),
            height=options.get(CONF_HEIGHT, DEFAULT_HEIGHT),
            rotation=options.get(CONF_ROTATION, DEFAULT_ROTATION),
            color_mode=options.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE),
            dither=options.get(CONF_DITHER, DEFAULT_DITHER),
        )
        self.update_interval = timedelta(
            seconds=options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        )
