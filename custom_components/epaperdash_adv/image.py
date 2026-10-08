"""Image entity exposing the latest dashboard screenshot inside Home Assistant."""
from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .coordinator import EpaperDashCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the EpaperDash-ADV image entity for this entry."""
    coordinator: EpaperDashCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([EpaperDashImageEntity(hass, coordinator, entry)])


class EpaperDashImageEntity(CoordinatorEntity[EpaperDashCoordinator], ImageEntity):
    """Shows the most recently captured dashboard screenshot."""

    _attr_content_type = "image/png"
    _attr_has_entity_name = True
    _attr_name = "Screenshot"

    def __init__(
        self, hass: HomeAssistant, coordinator: EpaperDashCoordinator, entry: ConfigEntry
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"{entry.entry_id}_screenshot"
        if coordinator.last_update_success:
            self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        return self.coordinator.data

    def _handle_coordinator_update(self) -> None:
        self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()
