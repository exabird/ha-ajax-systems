"""Alarm control panel platform for Ajax Systems."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AjaxDataUpdateCoordinator, AjaxGroup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ajax Systems alarm control panel."""
    coordinator: AjaxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[AlarmControlPanelEntity] = []

    # Add main hub alarm panel
    if coordinator.data.hub:
        entities.append(AjaxAlarmControlPanel(coordinator))

    # Add group alarm panels if groups mode is enabled
    for group_id, group in coordinator.data.groups.items():
        entities.append(AjaxGroupAlarmControlPanel(coordinator, group_id, group))

    async_add_entities(entities)


class AjaxAlarmControlPanel(
    CoordinatorEntity[AjaxDataUpdateCoordinator], AlarmControlPanelEntity
):
    """Representation of the Ajax hub alarm control panel."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
    )
    _attr_code_arm_required = False

    def __init__(self, coordinator: AjaxDataUpdateCoordinator) -> None:
        """Initialize the alarm control panel."""
        super().__init__(coordinator)
        hub = coordinator.data.hub

        self._attr_unique_id = f"{DOMAIN}_{hub.id}_alarm"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="Ajax Systems",
            model=hub.model,
            sw_version=hub.firmware_version,
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the alarm."""
        hub = self.coordinator.data.hub
        if not hub:
            return None

        if not hub.online:
            return AlarmControlPanelState.UNAVAILABLE

        if hub.armed:
            return AlarmControlPanelState.ARMED_AWAY

        return AlarmControlPanelState.DISARMED

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.hub is not None and self.coordinator.data.hub.online

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        await self.coordinator.async_disarm()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        await self.coordinator.async_arm()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home mode (same as away for Ajax)."""
        await self.coordinator.async_arm()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AjaxGroupAlarmControlPanel(
    CoordinatorEntity[AjaxDataUpdateCoordinator], AlarmControlPanelEntity
):
    """Representation of an Ajax group alarm control panel."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    _attr_code_arm_required = False

    def __init__(
        self,
        coordinator: AjaxDataUpdateCoordinator,
        group_id: str,
        group: AjaxGroup,
    ) -> None:
        """Initialize the group alarm control panel."""
        super().__init__(coordinator)
        self._group_id = group_id
        hub = coordinator.data.hub

        self._attr_unique_id = f"{DOMAIN}_{hub.id}_group_{group_id}"
        self._attr_name = group.name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="Ajax Systems",
            model=hub.model,
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the group alarm."""
        group = self.coordinator.data.groups.get(self._group_id)
        if not group:
            return None

        if group.armed:
            if group.night_mode:
                return AlarmControlPanelState.ARMED_NIGHT
            return AlarmControlPanelState.ARMED_AWAY

        return AlarmControlPanelState.DISARMED

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the group."""
        await self.coordinator.async_disarm_group(self._group_id)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the group in away mode."""
        await self.coordinator.async_arm_group(self._group_id)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the group in home mode."""
        await self.coordinator.async_arm_group(self._group_id)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Arm the group in night mode."""
        await self.coordinator.async_set_night_mode(self._group_id, enabled=True)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
