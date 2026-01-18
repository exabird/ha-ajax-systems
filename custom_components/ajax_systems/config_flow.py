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
from .backend_api import BackendApi, BackendApiError
from .const import (
    AUTH_MODE_COMPANY,
    AUTH_MODE_PREMIUM,
    AUTH_MODE_USER,
    BACKEND_URL,
    CONF_AJAX_EMAIL,
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

    VERSION = 2  # Bumped for new auth mode

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api: AjaxApi | None = None
        self._backend_api: BackendApi | None = None
        self._auth_mode: str | None = None
        # Premium auth (backend)
        self._ajax_email: str | None = None
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
        self._hubs: list[dict[str, Any]] = []
        self._selected_hub: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose auth mode."""
        if user_input is not None:
            self._auth_mode = user_input[CONF_AUTH_MODE]
            if self._auth_mode == AUTH_MODE_PREMIUM:
                return await self.async_step_premium_auth()
            elif self._auth_mode == AUTH_MODE_COMPANY:
                return await self.async_step_company_auth()
            return await self.async_step_user_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_MODE, default=AUTH_MODE_PREMIUM): vol.In(
                        {
                            AUTH_MODE_PREMIUM: "Standard (Email only - Recommended)",
                            AUTH_MODE_COMPANY: "Advanced: Company/PRO (Own API credentials)",
                            AUTH_MODE_USER: "Advanced: User API (Own API credentials)",
                        }
                    ),
                }
            ),
        )

    async def async_step_premium_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle premium/backend authentication."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._ajax_email = user_input[CONF_AJAX_EMAIL].lower().strip()

            session = async_get_clientsession(self.hass)
            self._backend_api = BackendApi(
                session=session,
                ajax_email=self._ajax_email,
                backend_url=BACKEND_URL,
            )

            try:
                # Check premium status and get hubs
                await self._backend_api.check_premium_status()
                self._hubs = await self._backend_api.get_hubs()

                if not self._hubs:
                    errors["base"] = "no_hubs"
                else:
                    return await self.async_step_select_hub()

            except BackendApiError as err:
                _LOGGER.error("Backend API error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="premium_auth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AJAX_EMAIL): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "premium_url": BACKEND_URL,
            },
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
                # Get spaces and extract hubs
                spaces = await self._api.get_spaces()
                self._hubs = []
                for space in spaces:
                    for hub in space.get("hubs", []):
                        self._hubs.append({
                            "id": hub.get("id"),
                            "name": hub.get("name"),
                            "spaceId": space.get("id"),
                            "spaceName": space.get("name"),
                        })

                if not self._hubs:
                    errors["base"] = "no_hubs"
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

                # Get spaces and extract hubs
                spaces = await self._api.get_spaces()
                self._hubs = []
                for space in spaces:
                    for hub in space.get("hubs", []):
                        self._hubs.append({
                            "id": hub.get("id"),
                            "name": hub.get("name"),
                            "spaceId": space.get("id"),
                            "spaceName": space.get("name"),
                        })

                if not self._hubs:
                    errors["base"] = "no_hubs"
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

            # Find the hub
            for hub in self._hubs:
                if hub.get("id") == hub_id:
                    self._selected_hub = hub
                    break

            if self._selected_hub:
                return await self._create_entry()
            else:
                errors["base"] = "invalid_hub"

        # Build hub options
        hub_options = {}
        for hub in self._hubs:
            hub_id = hub.get("id", "")
            hub_name = hub.get("name", "Unknown Hub")
            space_name = hub.get("spaceName", "")
            if space_name:
                hub_options[hub_id] = f"{hub_name} ({space_name})"
            else:
                hub_options[hub_id] = hub_name

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
        if not self._selected_hub:
            return self.async_abort(reason="unknown")

        hub_id = self._selected_hub.get("id")
        hub_name = self._selected_hub.get("name", "Ajax Hub")
        space_id = self._selected_hub.get("spaceId")

        # Check if already configured
        await self.async_set_unique_id(f"{DOMAIN}_{hub_id}")
        self._abort_if_unique_id_configured()

        # Build entry data based on auth mode
        data = {
            CONF_AUTH_MODE: self._auth_mode,
            CONF_HUB_ID: hub_id,
        }

        if space_id:
            data[CONF_SPACE_ID] = space_id

        if self._auth_mode == AUTH_MODE_PREMIUM:
            data[CONF_AJAX_EMAIL] = self._ajax_email
        elif self._auth_mode == AUTH_MODE_COMPANY:
            data[CONF_API_KEY] = self._api_key
            data[CONF_COMPANY_ID] = self._company_id
            data[CONF_COMPANY_TOKEN] = self._company_token
        else:  # AUTH_MODE_USER
            data[CONF_API_KEY] = self._api_key
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
        self._auth_mode = entry_data.get(CONF_AUTH_MODE, AUTH_MODE_PREMIUM)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)

            try:
                if self._auth_mode == AUTH_MODE_PREMIUM:
                    api = BackendApi(
                        session=session,
                        ajax_email=user_input[CONF_AJAX_EMAIL],
                        backend_url=BACKEND_URL,
                    )
                    await api.check_premium_status()
                elif self._auth_mode == AUTH_MODE_COMPANY:
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
                    if self._auth_mode == AUTH_MODE_USER:
                        new_data[CONF_PASSWORD_HASH] = AjaxApi.hash_password(
                            user_input[CONF_PASSWORD]
                        )
                        new_data[CONF_USER_ID] = api.user_id
                        new_data[CONF_SESSION_TOKEN] = api.session_token
                        new_data[CONF_REFRESH_TOKEN] = api.refresh_token

                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except (AjaxAuthError, BackendApiError):
                errors["base"] = "auth_error"
            except (AjaxApiError, BackendApiError):
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        # Show appropriate form based on auth mode
        if self._auth_mode == AUTH_MODE_PREMIUM:
            schema = vol.Schema(
                {
                    vol.Required(CONF_AJAX_EMAIL): str,
                }
            )
        elif self._auth_mode == AUTH_MODE_COMPANY:
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
