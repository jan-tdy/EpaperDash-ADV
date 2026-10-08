"""Dashboard screenshot rendering for e-ink friendly output.

Uses a headless Chromium instance (via Playwright) to open the configured
Lovelace dashboard view exactly as a browser would, then converts the
resulting screenshot into a grayscale/1-bit image suitable for an e-ink
panel. This is a real screenshot of whatever dashboard the user builds in
Lovelace - there is no special "card" to configure here.
"""
from __future__ import annotations

import asyncio
import logging
import time
from io import BytesIO

from homeassistant.core import HomeAssistant

from .const import COLOR_MODE_BW, COLOR_MODE_GRAYSCALE4, COLOR_MODE_GRAYSCALE16

_LOGGER = logging.getLogger(__name__)

# Serializes browser start/stop across concurrent config entries so we never
# launch two Chromium processes racing on the same Playwright install step.
_BROWSER_LOCK = asyncio.Lock()


class RendererError(Exception):
    """Raised when the dashboard screenshot cannot be produced."""


class DashboardRenderer:
    """Renders a single Lovelace dashboard view to an e-ink-ready PNG."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        dashboard_path: str,
        access_token: str,
        width: int,
        height: int,
        rotation: int,
        color_mode: str,
        dither: bool,
    ) -> None:
        self._hass = hass
        self._base_url = base_url.rstrip("/")
        self._dashboard_path = dashboard_path
        self._access_token = access_token
        self._width = width
        self._height = height
        self._rotation = rotation
        self._color_mode = color_mode
        self._dither = dither
        self._playwright = None
        self._browser = None

    def update_settings(
        self,
        dashboard_path: str,
        width: int,
        height: int,
        rotation: int,
        color_mode: str,
        dither: bool,
    ) -> None:
        """Update capture settings in place (used when options are changed)."""
        self._dashboard_path = dashboard_path
        self._width = width
        self._height = height
        self._rotation = rotation
        self._color_mode = color_mode
        self._dither = dither

    async def async_start(self) -> None:
        """Launch the shared headless browser if it is not already running."""
        async with _BROWSER_LOCK:
            if self._browser is not None:
                return
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
                )
            except Exception as err:  # noqa: BLE001 - surfaced to the user as RendererError
                await self._async_cleanup_failed_start()
                raise RendererError(
                    "Nepodarilo sa spustiť headless Chromium (Playwright). Over, že bežiaci"
                    " Home Assistant Docker image obsahuje potrebné systémové knižnice"
                    " - pozri README, sekcia 'Systémové závislosti'."
                ) from err

    async def _async_cleanup_failed_start(self) -> None:
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self._browser = None

    async def async_stop(self) -> None:
        """Shut down the headless browser."""
        async with _BROWSER_LOCK:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    async def async_capture(self) -> bytes:
        """Capture the configured dashboard view and return processed PNG bytes."""
        if self._browser is None:
            await self.async_start()

        context = await self._browser.new_context(
            viewport={"width": self._width, "height": self._height},
            device_scale_factor=1,
            color_scheme="light",
        )
        await context.add_init_script(self._auth_init_script())
        page = await context.new_page()
        try:
            url = f"{self._base_url}{self._dashboard_path}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            # Lovelace keeps rendering (charts, graphs, map tiles) for a short
            # while after the network goes idle - give it a moment to settle.
            await page.wait_for_timeout(1500)
            screenshot = await page.screenshot(type="png")
        except Exception as err:  # noqa: BLE001
            raise RendererError(
                f"Nepodarilo sa načítať dashboard '{self._dashboard_path}': {err}"
            ) from err
        finally:
            await context.close()

        return await self._hass.async_add_executor_job(self._process_image, screenshot)

    def _auth_init_script(self) -> str:
        """Pre-seed the frontend's auth storage with the long-lived access token.

        The Lovelace frontend normally logs in via an interactive OAuth flow.
        Since nothing is clicking "login" for a headless capture, we set the
        same localStorage structure the frontend itself writes after a
        successful login, using a long-lived access token and an expiry far
        in the future so it never attempts a silent token refresh.
        """
        expires = int(time.time()) + 10 * 365 * 24 * 3600
        token = self._access_token.replace("\\", "\\\\").replace("'", "\\'")
        return (
            "window.localStorage.setItem('hassTokens', JSON.stringify({"
            f"access_token: '{token}',"
            "token_type: 'Bearer',"
            f"expires: {expires},"
            "hassUrl: location.origin,"
            "clientId: location.origin"
            "}));"
        )

    def _process_image(self, raw_png: bytes):
        from PIL import Image

        image = Image.open(BytesIO(raw_png)).convert("RGB")
        if self._rotation:
            image = image.rotate(-self._rotation, expand=True)

        if self._color_mode == COLOR_MODE_BW:
            image = image.convert("L")
            image = image.convert("1" if self._dither else "L")
            if not self._dither:
                image = image.point(lambda p: 255 if p > 127 else 0)
        elif self._color_mode == COLOR_MODE_GRAYSCALE4:
            image = image.convert("L")
            image = image.point(lambda p: round(p / 17) * 17)
        elif self._color_mode == COLOR_MODE_GRAYSCALE16:
            image = image.convert("L")
        # COLOR_MODE_COLOR: keep RGB as-is (useful for debugging, most e-ink
        # panels can't actually show it).

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
