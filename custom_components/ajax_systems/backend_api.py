"""Backend API client for Ajax Premium service."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError

_LOGGER = logging.getLogger(__name__)

# Backend URL - change for production
DEFAULT_BACKEND_URL = "https://ajax-premium.vercel.app"


class BackendApiError(Exception):
    """Base exception for Backend API errors."""


class BackendAuthError(BackendApiError):
    """Authentication error."""


class BackendPremiumRequired(BackendApiError):
    """Premium feature required error."""


class BackendRateLimitError(BackendApiError):
    """Rate limit exceeded error."""


class BackendApi:
    """API client for Ajax Premium Backend.

    This client connects to the premium backend service which:
    1. Proxies requests to Ajax Systems API
    2. Manages premium subscriptions
    3. Tracks API usage and rate limits
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        ajax_email: str,
        backend_url: str = DEFAULT_BACKEND_URL,
    ) -> None:
        """Initialize the backend API client."""
        self._session = session
        self._ajax_email = ajax_email.lower().strip()
        self._backend_url = backend_url.rstrip("/")
        self._premium_status: dict[str, Any] | None = None

    @property
    def ajax_email(self) -> str:
        """Return the Ajax email."""
        return self._ajax_email

    @property
    def is_premium(self) -> bool:
        """Return True if user has premium subscription."""
        if self._premium_status is None:
            return False
        return self._premium_status.get("isPremium", False)

    @property
    def premium_features(self) -> dict[str, bool]:
        """Return premium feature flags."""
        if self._premium_status is None:
            return {
                "eventHistory": False,
                "pushNotifications": False,
                "motionCamImages": False,
                "groupControl": False,
            }
        return self._premium_status.get("features", {})

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "X-Ajax-Email": self._ajax_email,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Make an API request to the backend."""
        url = f"{self._backend_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                **kwargs,
            ) as response:
                if response.status == 204:
                    return None

                data = await response.json()

                if response.status == 401:
                    raise BackendAuthError(data.get("error", "Authentication failed"))
                if response.status == 403:
                    raise BackendPremiumRequired(
                        data.get("message", "Premium feature required")
                    )
                if response.status == 429:
                    raise BackendRateLimitError(
                        data.get("error", "Rate limit exceeded")
                    )

                response.raise_for_status()
                return data

        except ClientResponseError as err:
            raise BackendApiError(f"API error: {err.status} - {err.message}") from err
        except ClientError as err:
            raise BackendApiError(f"Connection error: {err}") from err

    async def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        """Make a GET request."""
        result = await self._request("GET", endpoint, **kwargs)
        return result if result is not None else {}

    async def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any] | None:
        """Make a POST request."""
        return await self._request("POST", endpoint, **kwargs)

    # Premium status
    async def check_premium_status(self) -> dict[str, Any]:
        """Check premium subscription status."""
        result = await self.get(f"/api/check-premium?email={self._ajax_email}")
        self._premium_status = result
        _LOGGER.debug(
            "Premium status for %s: %s",
            self._ajax_email,
            "Premium" if self.is_premium else "Free",
        )
        return result

    # Hub methods
    async def get_hubs(self) -> list[dict[str, Any]]:
        """Get all accessible hubs."""
        result = await self.get("/api/ajax/hubs")
        return result.get("hubs", [])

    async def get_hub(self, hub_id: str) -> dict[str, Any]:
        """Get hub details."""
        return await self.get(f"/api/ajax/hubs/{hub_id}")

    async def get_devices(self, hub_id: str) -> list[dict[str, Any]]:
        """Get all devices for a hub."""
        result = await self.get(f"/api/ajax/devices?hubId={hub_id}")
        return result.get("devices", [])

    # Arming methods (Free)
    async def arm_hub(self, hub_id: str, ignore_problems: bool = False) -> None:
        """Arm the hub."""
        await self.post(
            "/api/ajax/arm",
            json={
                "hubId": hub_id,
                "action": "arm",
                "ignoreProblems": ignore_problems,
            },
        )
        _LOGGER.info("Hub %s armed", hub_id)

    async def disarm_hub(self, hub_id: str, ignore_problems: bool = False) -> None:
        """Disarm the hub."""
        await self.post(
            "/api/ajax/arm",
            json={
                "hubId": hub_id,
                "action": "disarm",
                "ignoreProblems": ignore_problems,
            },
        )
        _LOGGER.info("Hub %s disarmed", hub_id)

    # Group control (Premium)
    async def arm_group(
        self,
        hub_id: str,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Arm a specific group (Premium feature)."""
        if not self.premium_features.get("groupControl"):
            raise BackendPremiumRequired("Group control requires premium subscription")

        await self.post(
            "/api/ajax/groups",
            json={
                "hubId": hub_id,
                "groupId": group_id,
                "action": "arm",
                "ignoreProblems": ignore_problems,
            },
        )
        _LOGGER.info("Group %s armed", group_id)

    async def disarm_group(
        self,
        hub_id: str,
        group_id: str,
        ignore_problems: bool = False,
    ) -> None:
        """Disarm a specific group (Premium feature)."""
        if not self.premium_features.get("groupControl"):
            raise BackendPremiumRequired("Group control requires premium subscription")

        await self.post(
            "/api/ajax/groups",
            json={
                "hubId": hub_id,
                "groupId": group_id,
                "action": "disarm",
                "ignoreProblems": ignore_problems,
            },
        )
        _LOGGER.info("Group %s disarmed", group_id)

    async def set_night_mode(
        self,
        hub_id: str,
        group_id: str,
        enabled: bool,
        ignore_problems: bool = False,
    ) -> None:
        """Set night mode for a group (Premium feature)."""
        if not self.premium_features.get("groupControl"):
            raise BackendPremiumRequired("Group control requires premium subscription")

        action = "night_mode_on" if enabled else "night_mode_off"
        await self.post(
            "/api/ajax/groups",
            json={
                "hubId": hub_id,
                "groupId": group_id,
                "action": action,
                "ignoreProblems": ignore_problems,
            },
        )
        _LOGGER.info("Night mode %s for group %s", "enabled" if enabled else "disabled", group_id)

    # Events (Premium)
    async def get_events(self, hub_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get event history for a hub (Premium feature)."""
        if not self.premium_features.get("eventHistory"):
            raise BackendPremiumRequired("Event history requires premium subscription")

        result = await self.get(f"/api/ajax/events?hubId={hub_id}&limit={limit}")
        return result.get("events", [])

    # Validation
    async def validate_connection(self, hub_id: str) -> bool:
        """Validate that we can connect to the backend and access the hub."""
        try:
            await self.check_premium_status()
            hub = await self.get_hub(hub_id)
            return bool(hub and hub.get("id") == hub_id)
        except BackendApiError:
            return False
