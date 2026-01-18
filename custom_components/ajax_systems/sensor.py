"""Sensor platform for Ajax Systems."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SIGNAL_LEVEL_MAP
from .coordinator import AjaxDataUpdateCoordinator, AjaxDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ajax Systems sensors."""
    coordinator: AjaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Hub sensors
    if coordinator.data.hub:
        hub = coordinator.data.hub
        if hub.battery_level is not None:
            entities.append(AjaxHubBatterySensor(coordinator))
        if hub.gsm_signal is not None:
            entities.append(AjaxHubGsmSignalSensor(coordinator))
        if hub.wifi_signal is not None:
            entities.append(AjaxHubWifiSignalSensor(coordinator))

    # Device sensors
    for device_id, device in coordinator.data.devices.items():
        # Battery sensor
        if device.battery_level is not None:
            entities.append(AjaxDeviceBatterySensor(coordinator, device))

        # Signal strength sensor
        if device.signal_strength is not None:
            entities.append(AjaxDeviceSignalSensor(coordinator, device))

        # Temperature sensor
        if device.temperature is not None:
            entities.append(AjaxDeviceTemperatureSensor(coordinator, device))

    async_add_entities(entities)


class AjaxHubBatterySensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of the Ajax hub battery sensor."""

    _attr_has_entity_name = True
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AjaxDataUpdateCoordinator) -> None:
        """Initialize the hub battery sensor."""
        super().__init__(coordinator)
        hub = coordinator.data.hub

        self._attr_unique_id = f"{DOMAIN}_{hub.id}_battery"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="Ajax Systems",
            model=hub.model,
        )

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        hub = self.coordinator.data.hub
        return hub.battery_level if hub else None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxHubGsmSignalSensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of the Ajax hub GSM signal sensor."""

    _attr_has_entity_name = True
    _attr_name = "GSM Signal"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:signal-cellular-3"

    def __init__(self, coordinator: AjaxDataUpdateCoordinator) -> None:
        """Initialize the hub GSM signal sensor."""
        super().__init__(coordinator)
        hub = coordinator.data.hub

        self._attr_unique_id = f"{DOMAIN}_{hub.id}_gsm_signal"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="Ajax Systems",
            model=hub.model,
        )

    @property
    def native_value(self) -> int | None:
        """Return the GSM signal level."""
        hub = self.coordinator.data.hub
        if hub and hub.gsm_signal is not None:
            return SIGNAL_LEVEL_MAP.get(hub.gsm_signal, hub.gsm_signal)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxHubWifiSignalSensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of the Ajax hub WiFi signal sensor."""

    _attr_has_entity_name = True
    _attr_name = "WiFi Signal"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: AjaxDataUpdateCoordinator) -> None:
        """Initialize the hub WiFi signal sensor."""
        super().__init__(coordinator)
        hub = coordinator.data.hub

        self._attr_unique_id = f"{DOMAIN}_{hub.id}_wifi_signal"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="Ajax Systems",
            model=hub.model,
        )

    @property
    def native_value(self) -> int | None:
        """Return the WiFi signal level."""
        hub = self.coordinator.data.hub
        if hub and hub.wifi_signal is not None:
            return SIGNAL_LEVEL_MAP.get(hub.wifi_signal, hub.wifi_signal)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxDeviceBatterySensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of an Ajax device battery sensor."""

    _attr_has_entity_name = True
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the device battery sensor."""
        super().__init__(coordinator)
        self._device_id = device.id

        self._attr_unique_id = f"{DOMAIN}_{device.id}_battery"

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
    def native_value(self) -> int | None:
        """Return the battery level."""
        device = self._get_device()
        return device.battery_level if device else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device = self._get_device()
        return device is not None and device.online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxDeviceSignalSensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of an Ajax device signal strength sensor."""

    _attr_has_entity_name = True
    _attr_name = "Signal Strength"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:signal"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the device signal sensor."""
        super().__init__(coordinator)
        self._device_id = device.id

        self._attr_unique_id = f"{DOMAIN}_{device.id}_signal"

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
    def native_value(self) -> int | None:
        """Return the signal strength."""
        device = self._get_device()
        if device and device.signal_strength:
            return SIGNAL_LEVEL_MAP.get(device.signal_strength, 0)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device = self._get_device()
        return device is not None and device.online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxDeviceTemperatureSensor(
    CoordinatorEntity[AjaxDataUpdateCoordinator], SensorEntity
):
    """Representation of an Ajax device temperature sensor."""

    _attr_has_entity_name = True
    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        device: AjaxDevice,
    ) -> None:
        """Initialize the device temperature sensor."""
        super().__init__(coordinator)
        self._device_id = device.id

        self._attr_unique_id = f"{DOMAIN}_{device.id}_temperature"

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
    def native_value(self) -> float | None:
        """Return the temperature."""
        device = self._get_device()
        return device.temperature if device else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device = self._get_device()
        return device is not None and device.online

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
