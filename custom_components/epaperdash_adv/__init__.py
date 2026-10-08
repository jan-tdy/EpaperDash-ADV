"""The EpaperDash-ADV integration.

Takes a real screenshot of a Lovelace dashboard view you design yourself and
serves it as an e-ink friendly image, both as a plain unauthenticated URL
(for the e-ink device itself) and as an `image` entity inside Home
Assistant.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import DATA_ACCESS_TOKEN, DOMAIN, PLATFORMS, SERVICE_CAPTURE_DEBUG, SERVICE_REFRESH
from .coordinator import EpaperDashCoordinator
from .http import EpaperDashImageView

_LOGGER = logging.getLogger(__name__)

_browser_install_lock = asyncio.Lock()
_browser_install_done = False


async def _async_ensure_browser_installed(hass: HomeAssistant) -> None:
    """Download the Chromium build Playwright needs, once per HA run.

    This is a no-op (fast) if it has already been downloaded previously, so
    it is safe to call on every config entry setup.
    """
    global _browser_install_done  # noqa: PLW0603
    async with _browser_install_lock:
        if _browser_install_done:
            return

        def _install() -> None:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
                capture_output=True,
                text=True,
            )

        try:
            await hass.async_add_executor_job(_install)
        except subprocess.CalledProcessError as err:
            raise ConfigEntryNotReady(
                "Playwright sa nepodarilo nainštalovať/spustiť. Ak bežíš v Home Assistant"
                " Container, over, že tvoj Docker image obsahuje systémové knižnice"
                f" potrebné pre Chromium (pozri README). Detail: {err.stderr}"
            ) from err
        _browser_install_done = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an EpaperDash-ADV config entry."""
    await _async_ensure_browser_installed(hass)

    hass.data.setdefault(DOMAIN, {})

    if "_view_registered" not in hass.data[DOMAIN]:
        hass.http.register_view(EpaperDashImageView(hass))
        hass.data[DOMAIN]["_view_registered"] = True

    coordinator = EpaperDashCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "token": entry.data[DATA_ACCESS_TOKEN],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data is None:
        return
    coordinator: EpaperDashCoordinator = entry_data["coordinator"]
    await coordinator.async_apply_options()
    await coordinator.async_request_refresh()


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        return

    async def _async_handle_refresh(call: ServiceCall) -> None:
        entry_id = call.data["entry_id"]
        entry_data = hass.data[DOMAIN].get(entry_id)
        if entry_data is None:
            raise ValueError(f"Unknown EpaperDash-ADV entry_id: {entry_id}")
        await entry_data["coordinator"].async_request_refresh()

    async def _async_handle_capture_debug(call: ServiceCall) -> None:
        entry_id = call.data["entry_id"]
        entry_data = hass.data[DOMAIN].get(entry_id)
        if entry_data is None:
            raise ValueError(f"Unknown EpaperDash-ADV entry_id: {entry_id}")
        coordinator: EpaperDashCoordinator = entry_data["coordinator"]
        await coordinator.async_request_refresh()
        if coordinator.data is None:
            return

        def _write() -> None:
            path = hass.config.path("www", "epaperdash_adv_debug.png")
            with open(path, "wb") as debug_file:
                debug_file.write(coordinator.data)

        await hass.async_add_executor_job(_write)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        _async_handle_refresh,
        schema=vol.Schema({vol.Required("entry_id"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CAPTURE_DEBUG,
        _async_handle_capture_debug,
        schema=vol.Schema({vol.Required("entry_id"): cv.string}),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an EpaperDash-ADV config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data is not None:
            await entry_data["coordinator"].renderer.async_stop()
    return unload_ok
