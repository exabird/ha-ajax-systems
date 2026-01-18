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
    CONF_SPACE_ID,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class AjaxSystemsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ajax Systems."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api: AjaxApi | None = None
        self._auth_mode: str | None = None
        # Company auth
        self._api_key: str | None = None
        self._company_id: str | None = None
        self._company_token: str | None = None
        # User auth
        self._username: str | None = None
        self._password_hash: str | None = None
        self._user_id: str | None = None
        self._session_token: str | None = None
        self._refresh_token: str | None = None
        # Common
        self._spaces: list[dict[str, Any]] = []
        self._selected_space: dict[str, Any] | None = None
        self._selected_hub: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose auth mode."""
        if user_input is not None:
            self._auth_mode = user_input[CONF_AUTH_MODE]
            if self._auth_mode == AUTH_MODE_COMPANY:
                return await self.async_step_company_auth()
            return await self.async_step_user_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_MODE, default=AUTH_MODE_COMPANY): vol.In(
                        {
                            AUTH_MODE_COMPANY: "Company/PRO (API Key + Company Token)",
                            AUTH_MODE_USER: "User (API Key + Email/Password)",
                        }
                    ),
                }
            ),
        )

    async def async_step_company_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle company authentication."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._company_id = user_input[CONF_COMPANY_ID]
            self._company_token = user_input[CONF_COMPANY_TOKEN]

            session = async_get_clientsession(self.hass)
            self._api = AjaxApi(
                session=session,
                api_key=self._api_key,
                company_id=self._company_id,
                company_token=self._company_token,
            )

            try:
                # Get spaces
                self._spaces = await self._api.get_spaces()

                if not self._spaces:
                    errors["base"] = "no_spaces"
                else:
                    return await self.async_step_select_hub()

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
            step_id="company_auth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_COMPANY_ID): str,
                    vol.Required(CONF_COMPANY_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_user_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user authentication."""
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
                else:
                    return await self.async_step_select_hub()

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
            step_id="user_auth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle hub selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            hub_id = user_input[CONF_HUB_ID]

            # Find the hub and space
            for space in self._spaces:
                for hub in space.get("hubs", []):
                    if hub.get("id") == hub_id:
                        self._selected_hub = hub
                        self._selected_space = space
                        break
                if self._selected_hub:
                    break

            if self._selected_hub:
                return await self._create_entry()
            else:
                errors["base"] = "invalid_hub"

        # Build hub options from all spaces
        hub_options = {}
        for space in self._spaces:
            space_name = space.get("name", "Unknown Space")
            for hub in space.get("hubs", []):
                hub_id = hub.get("id", "")
                hub_name = hub.get("name", "Unknown Hub")
                hub_options[hub_id] = f"{hub_name} ({space_name})"

        if not hub_options:
            return self.async_abort(reason="no_hubs")

        return self.async_show_form(
            step_id="select_hub",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HUB_ID): vol.In(hub_options),
                }
            ),
            errors=errors,
        )

    async def _create_entry(self) -> FlowResult:
        """Create the config entry."""
        if not self._selected_hub or not self._selected_space:
            return self.async_abort(reason="unknown")

        hub_id = self._selected_hub.get("id")
        hub_name = self._selected_hub.get("name", "Ajax Hub")
        space_id = self._selected_space.get("id")

        # Check if already configured
        await self.async_set_unique_id(f"{DOMAIN}_{hub_id}")
        self._abort_if_unique_id_configured()

        # Build entry data based on auth mode
        data = {
            CONF_API_KEY: self._api_key,
            CONF_AUTH_MODE: self._auth_mode,
            CONF_HUB_ID: hub_id,
            CONF_SPACE_ID: space_id,
        }

        if self._auth_mode == AUTH_MODE_COMPANY:
            data[CONF_COMPANY_ID] = self._company_id
            data[CONF_COMPANY_TOKEN] = self._company_token
        else:
            data[CONF_USERNAME] = self._username
            data[CONF_PASSWORD_HASH] = self._password_hash
            data[CONF_USER_ID] = self._user_id
            data[CONF_SESSION_TOKEN] = self._session_token
            data[CONF_REFRESH_TOKEN] = self._refresh_token

        return self.async_create_entry(
            title=hub_name,
            data=data,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication."""
        self._auth_mode = entry_data.get(CONF_AUTH_MODE, AUTH_MODE_COMPANY)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)

            if self._auth_mode == AUTH_MODE_COMPANY:
                api = AjaxApi(
                    session=session,
                    api_key=user_input[CONF_API_KEY],
                    company_id=user_input[CONF_COMPANY_ID],
                    company_token=user_input[CONF_COMPANY_TOKEN],
                )
            else:
                api = AjaxApi(
                    session=session,
                    api_key=user_input[CONF_API_KEY],
                    username=user_input[CONF_USERNAME],
                    password_hash=AjaxApi.hash_password(user_input[CONF_PASSWORD]),
                )

            try:
                if not api.is_company_auth:
                    await api.login(
                        user_input[CONF_USERNAME],
                        AjaxApi.hash_password(user_input[CONF_PASSWORD]),
                    )

                # Update existing entry
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    new_data = {**entry.data, **user_input}
                    if not api.is_company_auth:
                        new_data[CONF_PASSWORD_HASH] = AjaxApi.hash_password(
                            user_input[CONF_PASSWORD]
                        )
                        new_data[CONF_USER_ID] = api.user_id
                        new_data[CONF_SESSION_TOKEN] = api.session_token
                        new_data[CONF_REFRESH_TOKEN] = api.refresh_token

                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except AjaxAuthError:
                errors["base"] = "auth_error"
            except AjaxApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        # Show appropriate form based on auth mode
        if self._auth_mode == AUTH_MODE_COMPANY:
            schema = vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_COMPANY_ID): str,
                    vol.Required(CONF_COMPANY_TOKEN): str,
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
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
