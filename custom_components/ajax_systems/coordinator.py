"""Data update coordinator for Ajax Systems."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AjaxApi, AjaxApiError, AjaxAuthError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DOOR_SENSORS,
    GLASS_BREAK_SENSORS,
    MOTION_SENSORS,
    SMOKE_SENSORS,
    SWITCHES,
    WATER_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AjaxHub:
    """Representation of an Ajax Hub."""

    id: str
    name: str
    model: str
    online: bool
    armed: bool
    firmware_version: str | None = None
    gsm_signal: int | None = None
    wifi_signal: int | None = None
    ethernet_connected: bool = False
    battery_charge: int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AjaxDevice:
    """Representation of an Ajax device."""

    id: str
    name: str
    device_type: str
    room_id: str | None
    room_name: str | None
    online: bool
    battery_level: int | None
    signal_strength: str | None
    temperature: float | None
    tampered: bool
    triggered: bool
    bypassed: bool
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_motion_sensor(self) -> bool:
        """Check if device is a motion sensor."""
        return any(t in self.device_type for t in MOTION_SENSORS)

    @property
    def is_door_sensor(self) -> bool:
        """Check if device is a door/window sensor."""
        return any(t in self.device_type for t in DOOR_SENSORS)

    @property
    def is_smoke_sensor(self) -> bool:
        """Check if device is a smoke sensor."""
        return any(t in self.device_type for t in SMOKE_SENSORS)

    @property
    def is_water_sensor(self) -> bool:
        """Check if device is a water leak sensor."""
        return any(t in self.device_type for t in WATER_SENSORS)

    @property
    def is_glass_break_sensor(self) -> bool:
        """Check if device is a glass break sensor."""
        return any(t in self.device_type for t in GLASS_BREAK_SENSORS)

    @property
    def is_switch(self) -> bool:
        """Check if device is a switch/relay."""
        return any(t in self.device_type for t in SWITCHES)


@dataclass
class AjaxData:
    """Data container for Ajax Systems."""

    hub: AjaxHub | None = None
    devices: dict[str, AjaxDevice] = field(default_factory=dict)
    rooms: dict[str, str] = field(default_factory=dict)
    groups: dict[str, dict[str, Any]] = field(default_factory=dict)


class AjaxDataUpdateCoordinator(DataUpdateCoordinator[AjaxData]):
    """Class to manage fetching Ajax Systems data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: AjaxApi,
        entry: ConfigEntry,
        hub_id: str,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.hub_id = hub_id
        self._last_hub_data: dict[str, Any] = {}

        scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> AjaxData:
        """Fetch data from API."""
        try:
            # Get hub data
            hub_data = await self.api.get_hub(self.hub_id)
            self._last_hub_data = hub_data

            hub = self._parse_hub(hub_data)

            # Get devices
            devices_data = await self.api.get_hub_devices(self.hub_id, enrich=True)
            devices = {}
            rooms = {}

            for device_data in devices_data:
                device = self._parse_device(device_data)
                devices[device.id] = device

                # Track rooms
                if device.room_id and device.room_name:
                    rooms[device.room_id] = device.room_name

            # Get groups if available
            groups = {}
            if "groups" in hub_data:
                for group_data in hub_data.get("groups", []):
                    group_id = group_data.get("id")
                    if group_id:
                        groups[group_id] = group_data

            return AjaxData(
                hub=hub,
                devices=devices,
                rooms=rooms,
                groups=groups,
            )

        except AjaxAuthError as err:
            _LOGGER.error("Authentication error: %s", err)
            raise UpdateFailed(f"Authentication error: {err}") from err
        except AjaxApiError as err:
            _LOGGER.error("API error: %s", err)
            raise UpdateFailed(f"Error fetching data: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _parse_hub(self, data: dict[str, Any]) -> AjaxHub:
        """Parse hub data into AjaxHub object."""
        # Determine armed state
        arm_state = data.get("armState", data.get("state", "DISARMED"))
        armed = arm_state.upper() == "ARMED"

        # Get connectivity info
        gsm_signal = None
        wifi_signal = None
        ethernet = False

        connectivity = data.get("connectivity", {})
        if connectivity:
            gsm = connectivity.get("gsm", {})
            gsm_signal = gsm.get("signalLevel")

            wifi = connectivity.get("wifi", {})
            wifi_signal = wifi.get("signalLevel")

            ethernet = connectivity.get("ethernet", {}).get("connected", False)

        return AjaxHub(
            id=data.get("id", ""),
            name=data.get("name", "Ajax Hub"),
            model=data.get("type", data.get("hubType", "Hub")),
            online=data.get("online", False),
            armed=armed,
            firmware_version=data.get("firmwareVersion"),
            gsm_signal=gsm_signal,
            wifi_signal=wifi_signal,
            ethernet_connected=ethernet,
            battery_charge=data.get("batteryChargeLevelPercentage"),
            raw_data=data,
        )

    def _parse_device(self, data: dict[str, Any]) -> AjaxDevice:
        """Parse device data into AjaxDevice object."""
        # Determine triggered state based on device type
        triggered = False
        device_type = data.get("deviceType", "")

        # For motion sensors, check motion state
        if any(t in device_type for t in MOTION_SENSORS):
            triggered = data.get("motionDetected", False)
        # For door sensors, check open state
        elif any(t in device_type for t in DOOR_SENSORS):
            triggered = data.get("openState", data.get("isOpen", False))
        # For smoke sensors, check alarm state
        elif any(t in device_type for t in SMOKE_SENSORS):
            triggered = data.get("smokeDetected", data.get("alarm", False))
        # For water sensors, check leak state
        elif any(t in device_type for t in WATER_SENSORS):
            triggered = data.get("leakDetected", data.get("alarm", False))
        # For glass break sensors
        elif any(t in device_type for t in GLASS_BREAK_SENSORS):
            triggered = data.get("glassBreakDetected", data.get("alarm", False))

        # Determine bypassed state
        bypass_state = data.get("bypassState", "")
        bypassed = bypass_state and "BYPASS" in bypass_state.upper()

        return AjaxDevice(
            id=data.get("id", ""),
            name=data.get("deviceName", data.get("name", "Device")),
            device_type=device_type,
            room_id=data.get("roomId"),
            room_name=data.get("roomName"),
            online=data.get("online", False),
            battery_level=data.get("batteryChargeLevelPercentage"),
            signal_strength=data.get("signalLevel"),
            temperature=data.get("temperature"),
            tampered=data.get("tampered", False),
            triggered=triggered,
            bypassed=bypassed,
            raw_data=data,
        )

    async def async_arm(self, ignore_problems: bool = False) -> None:
        """Arm the hub."""
        await self.api.arm_hub(self.hub_id, ignore_problems)
        await self.async_request_refresh()

    async def async_disarm(self, ignore_problems: bool = False) -> None:
        """Disarm the hub."""
        await self.api.disarm_hub(self.hub_id, ignore_problems)
        await self.async_request_refresh()

    async def async_arm_group(
        self,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Arm a specific group."""
        await self.api.arm_group(self.hub_id, group_id, ignore_problems)
        await self.async_request_refresh()

    async def async_disarm_group(
        self,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Disarm a specific group."""
        await self.api.disarm_group(self.hub_id, group_id, ignore_problems)
        await self.async_request_refresh()

    async def async_set_night_mode(
        self,
        group_id: str,
        enabled: bool,
        ignore_problems: bool = False,
    ) -> None:
        """Set night mode for a group."""
        await self.api.set_night_mode(
            self.hub_id, group_id, enabled, ignore_problems
        )
        await self.async_request_refresh()

    async def async_switch_device(
        self,
        device_id: str,
        state: bool,
    ) -> None:
        """Turn a switch device on or off."""
        device = self.data.devices.get(device_id)
        if device:
            await self.api.switch_device(
                self.hub_id,
                device_id,
                device.device_type,
                state,
            )
            await self.async_request_refresh()
