"""Data update coordinator for Ajax Systems."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AjaxApi, AjaxApiError, AjaxAuthError
from .const import (
    CONF_AWS_ACCESS_KEY,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_KEY,
    CONF_SQS_ENABLED,
    CONF_SQS_QUEUE_URL,
    DEFAULT_AWS_REGION,
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

if TYPE_CHECKING:
    from .sqs_listener import AjaxSqsEvent, AjaxSqsListener

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
    room_name: str | None
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
    def display_name(self) -> str:
        """Return display name with room if available."""
        if self.room_name:
            return f"{self.name} - {self.room_name}"
        return self.name

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
class AjaxRoom:
    """Representation of an Ajax room."""

    id: str
    name: str
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AjaxData:
    """Data container for Ajax Systems."""

    hub: AjaxHub | None = None
    devices: dict[str, AjaxDevice] = field(default_factory=dict)
    groups: dict[str, AjaxGroup] = field(default_factory=dict)
    rooms: dict[str, AjaxRoom] = field(default_factory=dict)


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
        self._sqs_listener: AjaxSqsListener | None = None

        scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

        # Check if SQS is enabled (stored in options)
        sqs_enabled = entry.options.get(CONF_SQS_ENABLED, False)
        if sqs_enabled:
            # When SQS is enabled, use longer polling interval as fallback
            scan_interval = max(scan_interval, 30)
            _LOGGER.info("SQS enabled, using %s seconds polling as fallback", scan_interval)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        # Initialize SQS listener if enabled
        if sqs_enabled:
            self._init_sqs_listener(entry)

    async def _async_update_data(self) -> AjaxData:
        """Fetch data from API."""
        try:
            # Get hub data
            hub_data = await self.api.get_hub(self.hub_id)
            self._last_hub_data = hub_data
            hub = self._parse_hub(hub_data)

            # Get rooms
            rooms_data = await self.api.get_hub_rooms(self.hub_id)
            rooms = {}
            room_names = {}  # id -> name mapping for device parsing

            for room_data in rooms_data:
                room = self._parse_room(room_data)
                rooms[room.id] = room
                room_names[room.id] = room.name

            # Get devices
            devices_data = await self.api.get_hub_devices(self.hub_id, enrich=True)
            devices = {}

            for device_data in devices_data:
                device = self._parse_device(device_data, room_names)
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
                rooms=rooms,
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

    def _parse_room(self, data: dict[str, Any]) -> AjaxRoom:
        """Parse room data into AjaxRoom object."""
        return AjaxRoom(
            id=data.get("id", ""),
            name=data.get("roomName", f"Room {data.get('id', '')}"),
            raw_data=data,
        )

    def _parse_device(self, data: dict[str, Any], room_names: dict[str, str] | None = None) -> AjaxDevice:
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

        room_id = data.get("roomId", model.get("roomId"))
        room_name = room_names.get(room_id) if room_names and room_id else None

        return AjaxDevice(
            id=data.get("id", model.get("id", "")),
            name=device_name,
            device_type=device_type,
            room_id=room_id,
            room_name=room_name,
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

    async def async_set_hub_night_mode(
        self,
        enabled: bool,
        ignore_problems: bool = False,
    ) -> None:
        """Set night mode for the hub."""
        await self.api.set_hub_night_mode(self.hub_id, enabled, ignore_problems)
        await self.async_request_refresh()

    # SQS Listener methods
    def _init_sqs_listener(self, entry: ConfigEntry) -> None:
        """Initialize the SQS listener."""
        try:
            from .sqs_listener import AjaxSqsListener

            # SQS config is stored in options
            queue_url = entry.options.get(CONF_SQS_QUEUE_URL)
            aws_access_key = entry.options.get(CONF_AWS_ACCESS_KEY)
            aws_secret_key = entry.options.get(CONF_AWS_SECRET_KEY)
            aws_region = entry.options.get(CONF_AWS_REGION, DEFAULT_AWS_REGION)

            if not all([queue_url, aws_access_key, aws_secret_key]):
                _LOGGER.warning("SQS enabled but missing credentials")
                return

            self._sqs_listener = AjaxSqsListener(
                hass=self.hass,
                queue_url=queue_url,
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                region=aws_region,
                hub_id=self.hub_id,
            )
            self._sqs_listener.register_callback(self._handle_sqs_event)
            _LOGGER.info("SQS listener initialized for hub %s", self.hub_id)

        except ImportError as err:
            _LOGGER.warning("Could not import SQS listener: %s", err)
        except Exception as err:
            _LOGGER.error("Error initializing SQS listener: %s", err)

    async def async_start_sqs_listener(self) -> None:
        """Start the SQS listener."""
        if self._sqs_listener:
            await self._sqs_listener.start()

    async def async_stop_sqs_listener(self) -> None:
        """Stop the SQS listener."""
        if self._sqs_listener:
            await self._sqs_listener.stop()

    @callback
    def _handle_sqs_event(self, event: AjaxSqsEvent) -> None:
        """Handle an event from SQS."""
        from .sqs_listener import (
            EVENT_TYPE_ARM,
            EVENT_TYPE_DEVICE_STATE,
            EVENT_TYPE_DEVICE_TRIGGERED,
            EVENT_TYPE_DISARM,
            EVENT_TYPE_NIGHT_MODE,
        )

        _LOGGER.debug(
            "Processing SQS event: type=%s, device=%s",
            event.event_type,
            event.device_id,
        )

        # Update local state based on event type
        if event.event_type in (EVENT_TYPE_ARM, EVENT_TYPE_DISARM, EVENT_TYPE_NIGHT_MODE):
            # Hub arming state changed - trigger a refresh
            self.hass.async_create_task(self.async_request_refresh())

        elif event.event_type in (EVENT_TYPE_DEVICE_STATE, EVENT_TYPE_DEVICE_TRIGGERED):
            # Device state changed - update local data and notify listeners
            if event.device_id and self.data and event.device_id in self.data.devices:
                device = self.data.devices[event.device_id]
                if event.triggered is not None:
                    # Create updated device with new triggered state
                    self.data.devices[event.device_id] = AjaxDevice(
                        id=device.id,
                        name=device.name,
                        device_type=device.device_type,
                        room_id=device.room_id,
                        room_name=device.room_name,
                        group_id=device.group_id,
                        online=device.online,
                        battery_level=device.battery_level,
                        signal_strength=device.signal_strength,
                        temperature=device.temperature,
                        tampered=device.tampered,
                        triggered=event.triggered,
                        bypassed=device.bypassed,
                        firmware_version=device.firmware_version,
                        raw_data=device.raw_data,
                    )
                    # Notify listeners
                    self.async_set_updated_data(self.data)

    @property
    def sqs_enabled(self) -> bool:
        """Return True if SQS listener is enabled and running."""
        return self._sqs_listener is not None and self._sqs_listener.is_running
