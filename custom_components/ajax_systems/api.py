"""API client for Ajax Systems."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError

from .const import (
    API_BASE_URL,
    API_TIMEOUT,
    SESSION_TOKEN_REFRESH_MARGIN,
    SESSION_TOKEN_TTL,
)

_LOGGER = logging.getLogger(__name__)


class AjaxApiError(Exception):
    """Base exception for Ajax API errors."""


class AjaxAuthError(AjaxApiError):
    """Authentication error."""


class AjaxConnectionError(AjaxApiError):
    """Connection error."""


class AjaxApi:
    """API client for Ajax Systems.

    Supports two authentication modes:
    1. Company Token (X-Company-Token) - for company/PRO accounts
    2. User Session Token (X-Session-Token) - for user accounts
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        # Company auth
        company_id: str | None = None,
        company_token: str | None = None,
        # User auth
        username: str | None = None,
        password_hash: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_key = api_key

        # Company auth
        self._company_id = company_id
        self._company_token = company_token

        # User auth
        self._username = username
        self._password_hash = password_hash
        self._session_token: str | None = None
        self._refresh_token: str | None = None
        self._user_id: str | None = None
        self._token_expiry: datetime | None = None

        # Determine auth mode
        self._is_company_auth = bool(company_id and company_token)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @property
    def is_company_auth(self) -> bool:
        """Return True if using company authentication."""
        return self._is_company_auth

    @property
    def company_id(self) -> str | None:
        """Return the company ID."""
        return self._company_id

    @property
    def user_id(self) -> str | None:
        """Return the user ID."""
        return self._user_id

    @property
    def session_token(self) -> str | None:
        """Return the session token."""
        return self._session_token

    @property
    def refresh_token(self) -> str | None:
        """Return the refresh token."""
        return self._refresh_token

    def set_tokens(
        self,
        session_token: str,
        refresh_token: str,
        user_id: str,
        token_expiry: datetime | None = None,
    ) -> None:
        """Set authentication tokens from stored data."""
        self._session_token = session_token
        self._refresh_token = refresh_token
        self._user_id = user_id
        self._token_expiry = token_expiry or (
            datetime.now() + timedelta(seconds=SESSION_TOKEN_TTL)
        )

    def _is_token_expired(self) -> bool:
        """Check if the session token is expired or about to expire."""
        if self._is_company_auth:
            return False  # Company tokens don't expire
        if not self._token_expiry:
            return True
        return datetime.now() >= (
            self._token_expiry - timedelta(seconds=SESSION_TOKEN_REFRESH_MARGIN)
        )

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid session token."""
        if self._is_company_auth:
            return  # Company tokens are always valid

        if self._is_token_expired():
            if self._refresh_token and self._user_id:
                await self._refresh_session()
            elif self._username and self._password_hash:
                await self.login(self._username, self._password_hash)
            else:
                raise AjaxAuthError("No valid authentication method available")

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers based on auth mode."""
        headers = {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

        if self._is_company_auth:
            headers["X-Company-Token"] = self._company_token
        elif self._session_token:
            headers["X-Session-Token"] = self._session_token

        return headers

    def _get_base_path(self) -> str:
        """Get base path for API calls based on auth mode."""
        if self._is_company_auth:
            return f"/company/{self._company_id}"
        return f"/user/{self._user_id}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        auth_required: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Make an API request."""
        if auth_required and not self._is_company_auth:
            await self._ensure_valid_token()

        url = f"{API_BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_auth_headers() if auth_required else {"X-Api-Key": self._api_key, "Content-Type": "application/json"})

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                **kwargs,
            ) as response:
                if response.status == 204:
                    return None
                if response.status == 202:
                    # Async operation in progress
                    return await response.json()

                response.raise_for_status()
                return await response.json()

        except ClientResponseError as err:
            if err.status == 401:
                if not self._is_company_auth and self._refresh_token and self._user_id:
                    await self._refresh_session()
                    return await self._request(method, endpoint, auth_required, **kwargs)
                raise AjaxAuthError("Authentication failed") from err
            if err.status == 403:
                raise AjaxAuthError("Access forbidden") from err
            if err.status == 412:
                raise AjaxApiError("Precondition failed - arming prevented") from err
            raise AjaxApiError(f"API error: {err.status} - {err.message}") from err
        except ClientError as err:
            raise AjaxConnectionError(f"Connection error: {err}") from err

    async def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        """Make a GET request."""
        result = await self._request("GET", endpoint, **kwargs)
        return result if result is not None else {}

    async def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any] | None:
        """Make a POST request."""
        return await self._request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs: Any) -> dict[str, Any] | None:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> None:
        """Make a DELETE request."""
        await self._request("DELETE", endpoint, **kwargs)

    # Authentication methods (User mode only)
    async def login(
        self,
        username: str,
        password_hash: str,
        user_role: str = "USER",
    ) -> dict[str, Any]:
        """Login and obtain session token (User auth mode only)."""
        if self._is_company_auth:
            raise AjaxApiError("Login not supported in company auth mode")

        self._username = username
        self._password_hash = password_hash

        data = {
            "login": username,
            "passwordHash": password_hash,
            "userRole": user_role,
        }

        result = await self._request(
            "POST",
            "/login",
            auth_required=False,
            json=data,
        )

        if not result:
            raise AjaxAuthError("Login failed - no response")

        self._session_token = result.get("sessionToken")
        self._refresh_token = result.get("refreshToken")
        self._user_id = result.get("userId")
        self._token_expiry = datetime.now() + timedelta(seconds=SESSION_TOKEN_TTL)

        _LOGGER.debug("Login successful for user %s", self._user_id)
        return result

    async def _refresh_session(self) -> None:
        """Refresh the session token (User auth mode only)."""
        if self._is_company_auth:
            return

        if not self._refresh_token or not self._user_id:
            raise AjaxAuthError("Cannot refresh - no refresh token")

        data = {
            "userId": self._user_id,
            "refreshToken": self._refresh_token,
        }

        result = await self._request(
            "POST",
            "/refresh",
            auth_required=False,
            json=data,
        )

        if not result:
            raise AjaxAuthError("Token refresh failed")

        self._session_token = result.get("sessionToken")
        self._refresh_token = result.get("refreshToken")
        self._user_id = result.get("userId")
        self._token_expiry = datetime.now() + timedelta(seconds=SESSION_TOKEN_TTL)

        _LOGGER.debug("Session token refreshed successfully")

    # Spaces methods
    async def get_spaces(self) -> list[dict[str, Any]]:
        """Get all spaces."""
        base = self._get_base_path()
        result = await self.get(f"{base}/spaces")
        return result if isinstance(result, list) else result.get("spaces", [])

    async def get_space(self, space_id: str) -> dict[str, Any]:
        """Get space details."""
        base = self._get_base_path()
        return await self.get(f"{base}/spaces/{space_id}")

    # Hub methods
    async def get_hub(self, hub_id: str) -> dict[str, Any]:
        """Get hub details."""
        base = self._get_base_path()
        return await self.get(f"{base}/hubs/{hub_id}")

    async def get_hub_devices(self, hub_id: str, enrich: bool = True) -> list[dict[str, Any]]:
        """Get all devices for a hub."""
        base = self._get_base_path()
        params = {"enrich": str(enrich).lower()}
        result = await self.get(
            f"{base}/hubs/{hub_id}/devices",
            params=params,
        )
        return result if isinstance(result, list) else result.get("devices", result.get("deviceInfos", []))

    # Arming methods
    async def arm_hub(self, hub_id: str, ignore_problems: bool = False) -> None:
        """Arm the hub."""
        base = self._get_base_path()
        data = {
            "command": "ARM",
            "ignoreProblems": ignore_problems,
        }
        await self.put(
            f"{base}/hubs/{hub_id}/commands/arming",
            json=data,
        )
        _LOGGER.info("Hub %s armed", hub_id)

    async def disarm_hub(self, hub_id: str, ignore_problems: bool = False) -> None:
        """Disarm the hub."""
        base = self._get_base_path()
        data = {
            "command": "DISARM",
            "ignoreProblems": ignore_problems,
        }
        await self.put(
            f"{base}/hubs/{hub_id}/commands/arming",
            json=data,
        )
        _LOGGER.info("Hub %s disarmed", hub_id)

    async def set_night_mode(
        self,
        hub_id: str,
        group_id: str,
        enabled: bool,
        ignore_problems: bool = False,
    ) -> None:
        """Set night mode for a group."""
        base = self._get_base_path()
        command = "NIGHT_MODE_ON" if enabled else "NIGHT_MODE_OFF"
        data = {
            "command": command,
            "ignoreProblems": ignore_problems,
        }
        await self.put(
            f"{base}/hubs/{hub_id}/groups/{group_id}/commands/arming",
            json=data,
        )
        _LOGGER.info("Night mode %s for group %s", "enabled" if enabled else "disabled", group_id)

    async def arm_group(
        self,
        hub_id: str,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Arm a specific group."""
        base = self._get_base_path()
        data = {
            "command": "ARM",
            "ignoreProblems": ignore_problems,
        }
        await self.put(
            f"{base}/hubs/{hub_id}/groups/{group_id}/commands/arming",
            json=data,
        )
        _LOGGER.info("Group %s armed", group_id)

    async def disarm_group(
        self,
        hub_id: str,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Disarm a specific group."""
        base = self._get_base_path()
        data = {
            "command": "DISARM",
            "ignoreProblems": ignore_problems,
        }
        await self.put(
            f"{base}/hubs/{hub_id}/groups/{group_id}/commands/arming",
            json=data,
        )
        _LOGGER.info("Group %s disarmed", group_id)

    # Device commands
    async def send_device_command(
        self,
        hub_id: str,
        device_id: str,
        command: str,
        device_type: str,
        additional_params: dict[str, Any] | None = None,
    ) -> None:
        """Send a command to a device."""
        base = self._get_base_path()
        data = {
            "command": command,
            "deviceType": device_type,
        }
        if additional_params:
            data["additionalParam"] = additional_params

        await self.post(
            f"{base}/hubs/{hub_id}/devices/{device_id}/command",
            json=data,
        )
        _LOGGER.info("Command %s sent to device %s", command, device_id)

    async def switch_device(
        self,
        hub_id: str,
        device_id: str,
        device_type: str,
        state: bool,
    ) -> None:
        """Turn a switch device on or off."""
        command = "SWITCH_ON" if state else "SWITCH_OFF"
        await self.send_device_command(hub_id, device_id, command, device_type)

    # Hub commands
    async def mute_hub(self, hub_id: str) -> None:
        """Mute hub sound indication."""
        base = self._get_base_path()
        await self.post(
            f"{base}/hubs/{hub_id}/commands/muteSoundIndication",
        )
        _LOGGER.info("Hub %s muted", hub_id)

    async def restore_after_alarm(self, hub_id: str) -> None:
        """Restore hub after alarm condition."""
        base = self._get_base_path()
        await self.post(
            f"{base}/hubs/{hub_id}/commands/restoreAfterAlarmCondition",
        )
        _LOGGER.info("Hub %s restored after alarm", hub_id)

    # Validation method
    async def validate_connection(self, hub_id: str) -> bool:
        """Validate that we can connect to the API and access the hub."""
        try:
            hub = await self.get_hub(hub_id)
            return bool(hub and hub.get("id") == hub_id)
        except AjaxApiError:
            return False
