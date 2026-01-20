"""The Ajax Systems integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AjaxApi, AjaxAuthError
from .const import (
    AUTH_MODE_COMPANY,
    AUTH_MODE_USER,
    CONF_API_KEY,
    CONF_AUTH_MODE,
    CONF_COMPANY_ID,
    CONF_COMPANY_TOKEN,
    CONF_HUB_ID,
    CONF_PASSWORD_HASH,
    CONF_REFRESH_TOKEN,
    CONF_SESSION_TOKEN,
    CONF_USER_ID,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AjaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ajax Systems from a config entry."""
    session = async_get_clientsession(hass)

    auth_mode = entry.data.get(CONF_AUTH_MODE, AUTH_MODE_USER)
    hub_id = entry.data[CONF_HUB_ID]

    if auth_mode == AUTH_MODE_COMPANY:
        # Company Token authentication
        api = AjaxApi(
            session=session,
            api_key=entry.data[CONF_API_KEY],
            company_id=entry.data[CONF_COMPANY_ID],
            company_token=entry.data[CONF_COMPANY_TOKEN],
        )
    else:
        # User Session authentication
        api = AjaxApi(
            session=session,
            api_key=entry.data[CONF_API_KEY],
            username=entry.data.get(CONF_USERNAME),
            password_hash=entry.data.get(CONF_PASSWORD_HASH),
        )

        # Restore tokens if available
        if entry.data.get(CONF_SESSION_TOKEN):
            api.set_tokens(
                session_token=entry.data[CONF_SESSION_TOKEN],
                refresh_token=entry.data[CONF_REFRESH_TOKEN],
                user_id=entry.data[CONF_USER_ID],
            )

    # Create coordinator
    coordinator = AjaxDataUpdateCoordinator(
        hass=hass,
        api=api,
        entry=entry,
        hub_id=hub_id,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except AjaxAuthError as err:
        raise ConfigEntryAuthFailed from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Update stored tokens after successful connection (User mode only)
    if auth_mode == AUTH_MODE_USER and api.session_token and api.refresh_token:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_SESSION_TOKEN: api.session_token,
                CONF_REFRESH_TOKEN: api.refresh_token,
                CONF_USER_ID: api.user_id,
            },
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start SQS listener if enabled
    await coordinator.async_start_sqs_listener()

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop SQS listener
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_stop_sqs_listener()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
