"""Unauthenticated, token-protected image endpoint for e-ink devices.

A simple e-ink device typically has nothing more than a basic browser or a
periodic "fetch this URL and show it" script, and cannot go through Home
Assistant's normal login flow. The URL itself therefore carries a random,
per-entry secret token instead of requiring a session.
"""
from __future__ import annotations

import hmac
import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EpaperDashImageView(HomeAssistantView):
    """Serves the latest captured dashboard screenshot as a PNG."""

    url = "/api/epaperdash_adv/{entry_id}/{token}/image.png"
    name = "api:epaperdash_adv:image"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get(self, request: web.Request, entry_id: str, token: str) -> web.Response:
        entries = self._hass.data.get(DOMAIN, {})
        entry_data = entries.get(entry_id)
        if entry_data is None:
            return web.Response(status=404)

        if not hmac.compare_digest(entry_data["token"], token):
            return web.Response(status=404)

        coordinator = entry_data["coordinator"]
        if coordinator.data is None:
            return web.Response(status=503, text="No screenshot captured yet")

        return web.Response(
            body=coordinator.data,
            content_type="image/png",
            headers={"Cache-Control": "no-store"},
        )
