"""Binary sensor platform for Ajax Systems."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up Ajax Systems binary sensors."""
    coordinator: AjaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    for device_id, device in coordinator.data.devices.items():
        # Motion sensors
        if device.is_motion_sensor:
            entities.append(AjaxMotionSensor(coordinator, device))

        # Door/window sensors
        if device.is_door_sensor:
            entities.append(AjaxDoorSensor(coordinator, device))

        # Smoke sensors
        if device.is_smoke_sensor:
            entities.append(AjaxSmokeSensor(coordinator, device))

        # Water leak sensors
        if device.is_water_sensor:
            entities.append(AjaxWaterSensor(coordinator, device))

        # Glass break sensors
        if device.is_glass_break_sensor:
            entities.append(AjaxGlassBreakSensor(coordinator, device))

        # Add tamper sensor for all devices
        entities.append(AjaxTamperSensor(coordinator, device))

        # Add connectivity sensor for all devices
        entities.append(AjaxConnectivitySensor(coordinator, device))

    async_add_entities(entities)


class AjaxBinarySensorBase(
    CoordinatorEntity[AjaxDataUpdateCoordinator], BinarySensorEntity
):
    """Base class for Ajax binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
        sensor_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device.id
        self._sensor_type = sensor_type

        self._attr_unique_id = f"{DOMAIN}_{device.id}_{sensor_type}"

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
    def available(self) -> bool:
        """Return True if entity is available."""
        device = self._get_device()
        return device is not None and device.online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxMotionSensor(AjaxBinarySensorBase):
    """Representation of an Ajax motion sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_name = "Motion"

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the motion sensor."""
        super().__init__(coordinator, device, "motion")

    @property
    def is_on(self) -> bool | None:
        """Return true if motion is detected."""
        device = self._get_device()
        return device.triggered if device else None


class AjaxDoorSensor(AjaxBinarySensorBase):
    """Representation of an Ajax door/window sensor."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_name = "Door"

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the door sensor."""
        super().__init__(coordinator, device, "door")

    @property
    def is_on(self) -> bool | None:
        """Return true if door is open."""
        device = self._get_device()
        return device.triggered if device else None


class AjaxSmokeSensor(AjaxBinarySensorBase):
    """Representation of an Ajax smoke sensor."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE
    _attr_name = "Smoke"

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the smoke sensor."""
        super().__init__(coordinator, device, "smoke")

    @property
    def is_on(self) -> bool | None:
        """Return true if smoke is detected."""
        device = self._get_device()
        return device.triggered if device else None


class AjaxWaterSensor(AjaxBinarySensorBase):
    """Representation of an Ajax water leak sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_name = "Water Leak"

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the water sensor."""
        super().__init__(coordinator, device, "water")

    @property
    def is_on(self) -> bool | None:
        """Return true if water leak is detected."""
        device = self._get_device()
        return device.triggered if device else None


class AjaxGlassBreakSensor(AjaxBinarySensorBase):
    """Representation of an Ajax glass break sensor."""

    _attr_device_class = BinarySensorDeviceClass.VIBRATION
    _attr_name = "Glass Break"

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the glass break sensor."""
        super().__init__(coordinator, device, "glass_break")

    @property
    def is_on(self) -> bool | None:
        """Return true if glass break is detected."""
        device = self._get_device()
        return device.triggered if device else None


class AjaxTamperSensor(AjaxBinarySensorBase):
    """Representation of an Ajax tamper sensor."""

    _attr_device_class = BinarySensorDeviceClass.TAMPER
    _attr_name = "Tamper"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the tamper sensor."""
        super().__init__(coordinator, device, "tamper")

    @property
    def is_on(self) -> bool | None:
        """Return true if tampered."""
        device = self._get_device()
        return device.tampered if device else None


class AjaxConnectivitySensor(AjaxBinarySensorBase):
    """Representation of an Ajax connectivity sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connectivity"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(coordinator, device, "connectivity")

    @property
    def is_on(self) -> bool | None:
        """Return true if connected."""
        device = self._get_device()
        return device.online if device else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Connectivity sensor is always available
        return self._get_device() is not None
