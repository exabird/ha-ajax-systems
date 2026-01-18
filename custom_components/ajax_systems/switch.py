"""Switch platform for Ajax Systems."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AjaxDataUpdateCoordinator, AjaxDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ajax Systems switches."""
    coordinator: AjaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []

    for device_id, device in coordinator.data.devices.items():
        if device.is_switch:
            entities.append(AjaxSwitch(coordinator, device))

    async_add_entities(entities)


class AjaxSwitch(CoordinatorEntity[AjaxDataUpdateCoordinator], SwitchEntity):
    """Representation of an Ajax switch/relay."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_id = device.id

        self._attr_unique_id = f"{DOMAIN}_{device.id}_switch"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="Ajax Systems",
            model=device.device_type,
            via_device=(DOMAIN, coordinator.hub_id),
        )

    def _get_device(self) -> AjaxDevice | None:
        """Get device data from coordinator."""
        return self.coordinator.data.devices.get(self._device_id)

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        device = self._get_device()
        if device:
            # Check for switch state in raw data
            raw = device.raw_data
            return raw.get("switchState", raw.get("state", False))
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device = self._get_device()
        return device is not None and device.online

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_switch_device(self._device_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_switch_device(self._device_id, False)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
