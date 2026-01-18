"""Config flow for Ajax Systems integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AjaxApi, AjaxApiError, AjaxAuthError
from .const import (
    CONF_API_KEY,
    CONF_HUB_ID,
    CONF_PASSWORD_HASH,
    CONF_REFRESH_TOKEN,
    CONF_SESSION_TOKEN,
    CONF_SPACE_ID,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AjaxSystemsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ajax Systems."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api: AjaxApi | None = None
        self._api_key: str | None = None
        self._username: str | None = None
        self._password_hash: str | None = None
        self._user_id: str | None = None
        self._session_token: str | None = None
        self._refresh_token: str | None = None
        self._spaces: list[dict[str, Any]] = []
        self._selected_space: dict[str, Any] | None = None
        self._hubs: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._username = user_input[CONF_USERNAME]
            self._password_hash = AjaxApi.hash_password(user_input[CONF_PASSWORD])

            session = async_get_clientsession(self.hass)
            self._api = AjaxApi(
                session=session,
                api_key=self._api_key,
                username=self._username,
                password_hash=self._password_hash,
            )

            try:
                await self._api.login(self._username, self._password_hash)
                self._user_id = self._api.user_id
                self._session_token = self._api.session_token
                self._refresh_token = self._api.refresh_token

                # Get spaces
                self._spaces = await self._api.get_spaces()

                if not self._spaces:
                    errors["base"] = "no_spaces"
                elif len(self._spaces) == 1:
                    # Only one space, skip selection
                    self._selected_space = self._spaces[0]
                    return await self._get_hubs_and_create_entry()
                else:
                    # Multiple spaces, show selection
                    return await self.async_step_select_space()

            except AjaxAuthError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "auth_error"
            except AjaxApiError as err:
                _LOGGER.error("API error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_space(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle space selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            space_id = user_input[CONF_SPACE_ID]
            for space in self._spaces:
                if space.get("id") == space_id:
                    self._selected_space = space
                    break

            if self._selected_space:
                return await self._get_hubs_and_create_entry()
            else:
                errors["base"] = "invalid_space"

        # Build space options
        space_options = {
            space["id"]: space.get("name", f"Space {space['id']}")
            for space in self._spaces
        }

        return self.async_show_form(
            step_id="select_space",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SPACE_ID): vol.In(space_options),
                }
            ),
            errors=errors,
        )

    async def _get_hubs_and_create_entry(self) -> FlowResult:
        """Get hubs for the selected space and create config entry."""
        if not self._selected_space or not self._api:
            return self.async_abort(reason="unknown")

        space_id = self._selected_space.get("id")
        space_name = self._selected_space.get("name", "Ajax")

        # Get hubs from space
        hubs = self._selected_space.get("hubs", [])

        if not hubs:
            return self.async_abort(reason="no_hubs")

        # Use first hub (most common case)
        hub = hubs[0]
        hub_id = hub.get("id")

        # Check if already configured
        await self.async_set_unique_id(f"{DOMAIN}_{hub_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=space_name,
            data={
                CONF_API_KEY: self._api_key,
                CONF_USERNAME: self._username,
                CONF_PASSWORD_HASH: self._password_hash,
                CONF_USER_ID: self._user_id,
                CONF_SESSION_TOKEN: self._session_token,
                CONF_REFRESH_TOKEN: self._refresh_token,
                CONF_SPACE_ID: space_id,
                CONF_HUB_ID: hub_id,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._username = user_input[CONF_USERNAME]
            self._password_hash = AjaxApi.hash_password(user_input[CONF_PASSWORD])

            session = async_get_clientsession(self.hass)
            api = AjaxApi(
                session=session,
                api_key=self._api_key,
                username=self._username,
                password_hash=self._password_hash,
            )

            try:
                await api.login(self._username, self._password_hash)

                # Update existing entry
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_API_KEY: self._api_key,
                            CONF_USERNAME: self._username,
                            CONF_PASSWORD_HASH: self._password_hash,
                            CONF_USER_ID: api.user_id,
                            CONF_SESSION_TOKEN: api.session_token,
                            CONF_REFRESH_TOKEN: api.refresh_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except AjaxAuthError:
                errors["base"] = "auth_error"
            except AjaxApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return AjaxSystemsOptionsFlow(config_entry)


class AjaxSystemsOptionsFlow(OptionsFlow):
    """Handle options flow for Ajax Systems."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            "scan_interval", DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )
