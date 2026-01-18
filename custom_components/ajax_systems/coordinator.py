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
    SIGNAL_LEVEL_MAP,
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
    night_mode: bool = False
    firmware_version: str | None = None
    battery_level: int | None = None
    battery_state: str | None = None
    gsm_signal: str | None = None
    wifi_signal: str | None = None
    groups_enabled: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AjaxDevice:
    """Representation of an Ajax device."""

    id: str
    name: str
    device_type: str
    room_id: str | None
    group_id: str | None
    online: bool
    battery_level: int | None
    signal_strength: int | None  # Converted to percentage
    temperature: float | None
    tampered: bool
    triggered: bool
    bypassed: bool
    firmware_version: str | None = None
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
class AjaxGroup:
    """Representation of an Ajax group."""

    id: str
    name: str
    armed: bool
    night_mode: bool
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AjaxData:
    """Data container for Ajax Systems."""

    hub: AjaxHub | None = None
    devices: dict[str, AjaxDevice] = field(default_factory=dict)
    groups: dict[str, AjaxGroup] = field(default_factory=dict)


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

            for device_data in devices_data:
                device = self._parse_device(device_data)
                devices[device.id] = device

            # Parse groups if enabled
            groups = {}
            if hub.groups_enabled:
                for group_data in hub_data.get("groups", []):
                    group = self._parse_group(group_data)
                    groups[group.id] = group

            return AjaxData(
                hub=hub,
                devices=devices,
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
        state = data.get("state", data.get("armState", "DISARMED"))
        armed = "ARMED" in state.upper() and "DISARMED" not in state.upper()
        night_mode = "NIGHT_MODE" in state.upper() and "OFF" not in state.upper()

        battery = data.get("battery", {})
        battery_level = battery.get("chargeLevelPercentage")
        battery_state = battery.get("state")

        firmware = data.get("firmware", {})
        firmware_version = firmware.get("version")

        # Parse GSM and WiFi signal levels
        gsm = data.get("gsm", {})
        gsm_signal = gsm.get("signalLevel") if gsm else None

        wifi = data.get("wifi", {})
        wifi_signal = wifi.get("signalLevel") if wifi else None

        return AjaxHub(
            id=data.get("id", ""),
            name=data.get("name", "Ajax Hub"),
            model=data.get("hubSubtype", data.get("type", "Hub")),
            online=data.get("online", True),
            armed=armed,
            night_mode=night_mode,
            firmware_version=firmware_version,
            battery_level=battery_level,
            battery_state=battery_state,
            gsm_signal=gsm_signal,
            wifi_signal=wifi_signal,
            groups_enabled=data.get("groupsEnabled", False),
            raw_data=data,
        )

    def _parse_device(self, data: dict[str, Any]) -> AjaxDevice:
        """Parse device data into AjaxDevice object."""
        model = data.get("model", {})

        device_type = data.get("deviceType", model.get("deviceType", ""))
        device_name = data.get("deviceName", model.get("deviceName", data.get("name", "Device")))

        battery_level = model.get("batteryChargeLevelPercentage")
        signal_str = model.get("signalLevel", "")
        signal_strength = SIGNAL_LEVEL_MAP.get(signal_str) if signal_str else None
        temperature = model.get("temperature")

        triggered = self._determine_triggered_state(device_type, model)
        bypass_state = model.get("bypassState", [])
        bypassed = bool(bypass_state)

        return AjaxDevice(
            id=data.get("id", model.get("id", "")),
            name=device_name,
            device_type=device_type,
            room_id=data.get("roomId", model.get("roomId")),
            group_id=data.get("groupId", model.get("groupId")),
            online=model.get("online", data.get("online", False)),
            battery_level=battery_level,
            signal_strength=signal_strength,
            temperature=temperature,
            tampered=model.get("tampered", False),
            triggered=triggered,
            bypassed=bypassed,
            firmware_version=model.get("firmwareVersion"),
            raw_data=data,
        )

    def _determine_triggered_state(self, device_type: str, model: dict[str, Any]) -> bool:
        """Determine triggered state based on device type."""
        if any(t in device_type for t in DOOR_SENSORS):
            reed_closed = model.get("reedClosed", True)
            return not reed_closed
        elif any(t in device_type for t in MOTION_SENSORS):
            state = model.get("state", "")
            return state.upper() in ("ACTIVE", "ALARM", "TRIGGERED")
        elif any(t in device_type for t in SMOKE_SENSORS):
            state = model.get("state", "")
            return state.upper() in ("ALARM", "TRIGGERED", "SMOKE")
        elif any(t in device_type for t in WATER_SENSORS):
            state = model.get("state", "")
            return state.upper() in ("ALARM", "TRIGGERED", "LEAK")
        elif any(t in device_type for t in GLASS_BREAK_SENSORS):
            state = model.get("state", "")
            return state.upper() in ("ALARM", "TRIGGERED")
        return False

    def _parse_group(self, data: dict[str, Any]) -> AjaxGroup:
        """Parse group data into AjaxGroup object."""
        state = data.get("armState", data.get("state", "DISARMED"))
        armed = "ARMED" in state.upper() and "DISARMED" not in state.upper()
        night_mode = data.get("nightMode", False)

        return AjaxGroup(
            id=data.get("id", ""),
            name=data.get("name", f"Group {data.get('id', '')}"),
            armed=armed,
            night_mode=night_mode,
            raw_data=data,
        )

    # Arming methods
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
