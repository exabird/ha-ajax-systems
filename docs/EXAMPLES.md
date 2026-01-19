# Ajax Systems API - Code Examples

Practical code examples for interacting with the Ajax Systems API.

## Table of Contents

- [Python Examples](#python-examples)
  - [Authentication](#authentication)
  - [Getting Devices](#getting-devices)
  - [Arming/Disarming](#armingdisarming)
  - [Controlling Switches](#controlling-switches)
- [cURL Examples](#curl-examples)
- [JavaScript/Node.js Examples](#javascriptnodejs-examples)
- [Complete Python Client](#complete-python-client)

---

## Python Examples

### Authentication

#### User Mode Login

```python
import hashlib
import aiohttp
import asyncio

API_BASE_URL = "https://api.ajax.systems/api"

async def login(api_key: str, email: str, password: str) -> dict:
    """Login and get session tokens."""
    # Hash the password
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}/login",
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "login": email,
                "passwordHash": password_hash,
                "userRole": "USER"
            }
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return {
                "session_token": data["sessionToken"],
                "refresh_token": data["refreshToken"],
                "user_id": data["userId"]
            }

# Usage
async def main():
    credentials = await login(
        api_key="your-api-key",
        email="user@example.com",
        password="your-password"
    )
    print(f"User ID: {credentials['user_id']}")
    print(f"Session Token: {credentials['session_token'][:20]}...")

asyncio.run(main())
```

#### Token Refresh

```python
async def refresh_session(api_key: str, user_id: str, refresh_token: str) -> dict:
    """Refresh an expired session token."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}/refresh",
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "userId": user_id,
                "refreshToken": refresh_token
            }
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return {
                "session_token": data["sessionToken"],
                "refresh_token": data["refreshToken"],
                "user_id": data["userId"]
            }
```

---

### Getting Devices

#### Get All Hubs

```python
async def get_hubs(api_key: str, session_token: str, user_id: str) -> list:
    """Get all hubs for a user."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_BASE_URL}/user/{user_id}/spaces",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token
            }
        ) as response:
            response.raise_for_status()
            spaces = await response.json()

            hubs = []
            for space in spaces:
                if "hubs" in space:
                    hubs.extend(space["hubs"])
            return hubs
```

#### Get Hub Details

```python
async def get_hub(api_key: str, session_token: str, user_id: str, hub_id: str) -> dict:
    """Get detailed hub information."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token
            }
        ) as response:
            response.raise_for_status()
            return await response.json()
```

#### Get All Devices

```python
async def get_devices(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str,
    enrich: bool = True
) -> list:
    """Get all devices for a hub."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/devices",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token
            },
            params={"enrich": str(enrich).lower()}
        ) as response:
            response.raise_for_status()
            data = await response.json()

            # Handle different response formats
            if isinstance(data, list):
                return data
            return data.get("devices", data.get("deviceInfos", []))

# Usage
async def list_devices():
    # Assuming you have credentials
    devices = await get_devices(api_key, session_token, user_id, hub_id)

    for device in devices:
        print(f"- {device['name']} ({device['type']})")
        print(f"  Battery: {device.get('batteryLevel', 'N/A')}%")
        print(f"  Signal: {device.get('signalLevel', 'N/A')}")
```

---

### Arming/Disarming

#### Arm Hub

```python
async def arm_hub(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str,
    ignore_problems: bool = False
) -> None:
    """Arm the entire hub."""
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/commands/arming",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token,
                "Content-Type": "application/json"
            },
            json={
                "command": "ARM",
                "ignoreProblems": ignore_problems
            }
        ) as response:
            if response.status == 412:
                raise Exception("Cannot arm: sensors have problems (open doors, etc.)")
            response.raise_for_status()
            print("Hub armed successfully")
```

#### Disarm Hub

```python
async def disarm_hub(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str
) -> None:
    """Disarm the entire hub."""
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/commands/arming",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token,
                "Content-Type": "application/json"
            },
            json={
                "command": "DISARM",
                "ignoreProblems": False
            }
        ) as response:
            response.raise_for_status()
            print("Hub disarmed successfully")
```

#### Arm Specific Group

```python
async def arm_group(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str,
    group_id: str,
    ignore_problems: bool = False
) -> None:
    """Arm a specific security group."""
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/groups/{group_id}/commands/arming",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token,
                "Content-Type": "application/json"
            },
            json={
                "command": "ARM",
                "ignoreProblems": ignore_problems
            }
        ) as response:
            response.raise_for_status()
            print(f"Group {group_id} armed successfully")
```

#### Set Night Mode

```python
async def set_night_mode(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str,
    group_id: str,
    enabled: bool
) -> None:
    """Enable or disable night mode for a group."""
    command = "NIGHT_MODE_ON" if enabled else "NIGHT_MODE_OFF"

    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/groups/{group_id}/commands/arming",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token,
                "Content-Type": "application/json"
            },
            json={
                "command": command,
                "ignoreProblems": False
            }
        ) as response:
            response.raise_for_status()
            print(f"Night mode {'enabled' if enabled else 'disabled'}")
```

---

### Controlling Switches

#### Turn Switch On/Off

```python
async def switch_device(
    api_key: str,
    session_token: str,
    user_id: str,
    hub_id: str,
    device_id: str,
    device_type: str,
    turn_on: bool
) -> None:
    """Turn a switch device on or off."""
    command = "SWITCH_ON" if turn_on else "SWITCH_OFF"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}/user/{user_id}/hubs/{hub_id}/devices/{device_id}/command",
            headers={
                "X-Api-Key": api_key,
                "X-Session-Token": session_token,
                "Content-Type": "application/json"
            },
            json={
                "command": command,
                "deviceType": device_type
            }
        ) as response:
            response.raise_for_status()
            print(f"Device turned {'on' if turn_on else 'off'}")

# Usage
await switch_device(
    api_key, session_token, user_id, hub_id,
    device_id="socket123",
    device_type="Socket",
    turn_on=True
)
```

---

## cURL Examples

### Login

```bash
curl -X POST "https://api.ajax.systems/api/login" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "user@example.com",
    "passwordHash": "SHA256_HASH_OF_PASSWORD",
    "userRole": "USER"
  }'
```

### Get Spaces

```bash
curl -X GET "https://api.ajax.systems/api/user/USER_ID/spaces" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "X-Session-Token: YOUR_SESSION_TOKEN"
```

### Get Devices

```bash
curl -X GET "https://api.ajax.systems/api/user/USER_ID/hubs/HUB_ID/devices?enrich=true" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "X-Session-Token: YOUR_SESSION_TOKEN"
```

### Arm Hub

```bash
curl -X PUT "https://api.ajax.systems/api/user/USER_ID/hubs/HUB_ID/commands/arming" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "X-Session-Token: YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "ARM",
    "ignoreProblems": false
  }'
```

### Switch Control

```bash
curl -X POST "https://api.ajax.systems/api/user/USER_ID/hubs/HUB_ID/devices/DEVICE_ID/command" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "X-Session-Token: YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "SWITCH_ON",
    "deviceType": "Socket"
  }'
```

---

## JavaScript/Node.js Examples

### Authentication

```javascript
const crypto = require('crypto');
const axios = require('axios');

const API_BASE_URL = 'https://api.ajax.systems/api';

function hashPassword(password) {
    return crypto.createHash('sha256').update(password).digest('hex');
}

async function login(apiKey, email, password) {
    const passwordHash = hashPassword(password);

    const response = await axios.post(`${API_BASE_URL}/login`, {
        login: email,
        passwordHash: passwordHash,
        userRole: 'USER'
    }, {
        headers: {
            'X-Api-Key': apiKey,
            'Content-Type': 'application/json'
        }
    });

    return {
        sessionToken: response.data.sessionToken,
        refreshToken: response.data.refreshToken,
        userId: response.data.userId
    };
}
```

### Get Devices

```javascript
async function getDevices(apiKey, sessionToken, userId, hubId) {
    const response = await axios.get(
        `${API_BASE_URL}/user/${userId}/hubs/${hubId}/devices`,
        {
            headers: {
                'X-Api-Key': apiKey,
                'X-Session-Token': sessionToken
            },
            params: { enrich: 'true' }
        }
    );

    const data = response.data;
    if (Array.isArray(data)) {
        return data;
    }
    return data.devices || data.deviceInfos || [];
}
```

### Arm/Disarm

```javascript
async function setArmingState(apiKey, sessionToken, userId, hubId, arm) {
    const command = arm ? 'ARM' : 'DISARM';

    await axios.put(
        `${API_BASE_URL}/user/${userId}/hubs/${hubId}/commands/arming`,
        {
            command: command,
            ignoreProblems: false
        },
        {
            headers: {
                'X-Api-Key': apiKey,
                'X-Session-Token': sessionToken,
                'Content-Type': 'application/json'
            }
        }
    );

    console.log(`Hub ${arm ? 'armed' : 'disarmed'} successfully`);
}
```

---

## Complete Python Client

A complete async Python client for the Ajax API:

```python
"""Complete Ajax Systems API Client."""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AjaxApiError(Exception):
    """Base exception for Ajax API errors."""


class AjaxAuthError(AjaxApiError):
    """Authentication error."""


class AjaxApi:
    """Ajax Systems API Client."""

    API_BASE_URL = "https://api.ajax.systems/api"
    SESSION_TOKEN_TTL = 15 * 60  # 15 minutes
    REFRESH_MARGIN = 5 * 60  # Refresh 5 minutes before expiry

    def __init__(
        self,
        api_key: str,
        # User auth
        username: Optional[str] = None,
        password: Optional[str] = None,
        # Company auth
        company_id: Optional[str] = None,
        company_token: Optional[str] = None,
    ):
        self._api_key = api_key
        self._username = username
        self._password_hash = hashlib.sha256(password.encode()).hexdigest() if password else None
        self._company_id = company_id
        self._company_token = company_token

        self._session_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        self._is_company_auth = bool(company_id and company_token)
        self._http_session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._http_session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_session:
            await self._http_session.close()

    def _needs_refresh(self) -> bool:
        if self._is_company_auth:
            return False
        if not self._token_expiry:
            return True
        return datetime.now() >= (self._token_expiry - timedelta(seconds=self.REFRESH_MARGIN))

    def _get_headers(self) -> dict:
        headers = {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json"
        }
        if self._is_company_auth:
            headers["X-Company-Token"] = self._company_token
        elif self._session_token:
            headers["X-Session-Token"] = self._session_token
        return headers

    def _get_base_path(self) -> str:
        if self._is_company_auth:
            return f"/company/{self._company_id}"
        return f"/user/{self._user_id}"

    async def _ensure_auth(self) -> None:
        if self._is_company_auth:
            return
        if self._needs_refresh():
            if self._refresh_token:
                await self._refresh_session()
            else:
                await self.login()

    async def login(self) -> dict:
        """Login and obtain session tokens."""
        if self._is_company_auth:
            raise AjaxApiError("Login not needed for company auth")

        async with self._http_session.post(
            f"{self.API_BASE_URL}/login",
            headers={"X-Api-Key": self._api_key, "Content-Type": "application/json"},
            json={
                "login": self._username,
                "passwordHash": self._password_hash,
                "userRole": "USER"
            }
        ) as response:
            if response.status == 401:
                raise AjaxAuthError("Invalid credentials")
            response.raise_for_status()
            data = await response.json()

        self._session_token = data["sessionToken"]
        self._refresh_token = data["refreshToken"]
        self._user_id = data["userId"]
        self._token_expiry = datetime.now() + timedelta(seconds=self.SESSION_TOKEN_TTL)

        _LOGGER.info("Logged in successfully")
        return data

    async def _refresh_session(self) -> None:
        """Refresh the session token."""
        async with self._http_session.post(
            f"{self.API_BASE_URL}/refresh",
            headers={"X-Api-Key": self._api_key, "Content-Type": "application/json"},
            json={
                "userId": self._user_id,
                "refreshToken": self._refresh_token
            }
        ) as response:
            if response.status == 401:
                # Refresh token expired, need full login
                await self.login()
                return
            response.raise_for_status()
            data = await response.json()

        self._session_token = data["sessionToken"]
        self._refresh_token = data["refreshToken"]
        self._token_expiry = datetime.now() + timedelta(seconds=self.SESSION_TOKEN_TTL)

        _LOGGER.debug("Session refreshed")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an API request."""
        await self._ensure_auth()

        url = f"{self.API_BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())

        async with self._http_session.request(
            method, url, headers=headers, **kwargs
        ) as response:
            if response.status == 401:
                await self._refresh_session()
                return await self._request(method, endpoint, **kwargs)
            if response.status == 204:
                return None
            response.raise_for_status()
            return await response.json()

    # High-level methods
    async def get_spaces(self) -> list:
        """Get all spaces."""
        return await self._request("GET", f"{self._get_base_path()}/spaces")

    async def get_hub(self, hub_id: str) -> dict:
        """Get hub details."""
        return await self._request("GET", f"{self._get_base_path()}/hubs/{hub_id}")

    async def get_devices(self, hub_id: str) -> list:
        """Get all devices for a hub."""
        result = await self._request(
            "GET",
            f"{self._get_base_path()}/hubs/{hub_id}/devices",
            params={"enrich": "true"}
        )
        if isinstance(result, list):
            return result
        return result.get("devices", result.get("deviceInfos", []))

    async def arm_hub(self, hub_id: str, ignore_problems: bool = False) -> None:
        """Arm the hub."""
        await self._request(
            "PUT",
            f"{self._get_base_path()}/hubs/{hub_id}/commands/arming",
            json={"command": "ARM", "ignoreProblems": ignore_problems}
        )

    async def disarm_hub(self, hub_id: str) -> None:
        """Disarm the hub."""
        await self._request(
            "PUT",
            f"{self._get_base_path()}/hubs/{hub_id}/commands/arming",
            json={"command": "DISARM", "ignoreProblems": False}
        )

    async def switch_device(
        self, hub_id: str, device_id: str, device_type: str, turn_on: bool
    ) -> None:
        """Control a switch device."""
        command = "SWITCH_ON" if turn_on else "SWITCH_OFF"
        await self._request(
            "POST",
            f"{self._get_base_path()}/hubs/{hub_id}/devices/{device_id}/command",
            json={"command": command, "deviceType": device_type}
        )


# Usage example
async def main():
    async with AjaxApi(
        api_key="your-api-key",
        username="user@example.com",
        password="your-password"
    ) as api:
        # Login happens automatically
        spaces = await api.get_spaces()

        for space in spaces:
            print(f"Space: {space.get('name')}")

            # Get hub details
            for hub in space.get("hubs", []):
                hub_id = hub["id"]
                hub_details = await api.get_hub(hub_id)
                print(f"  Hub: {hub_details.get('name')} - {hub_details.get('state')}")

                # Get devices
                devices = await api.get_devices(hub_id)
                for device in devices:
                    print(f"    - {device['name']} ({device['type']})")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Error Handling Best Practices

```python
async def safe_api_call():
    """Example with proper error handling."""
    try:
        devices = await api.get_devices(hub_id)
        return devices

    except AjaxAuthError as e:
        _LOGGER.error("Authentication failed: %s", e)
        # Maybe re-authenticate or notify user
        raise

    except aiohttp.ClientResponseError as e:
        if e.status == 412:
            _LOGGER.warning("Cannot arm: sensors have problems")
        elif e.status == 429:
            _LOGGER.warning("Rate limited, waiting...")
            await asyncio.sleep(60)
            return await safe_api_call()  # Retry
        else:
            _LOGGER.error("API error: %s", e)
        raise

    except aiohttp.ClientError as e:
        _LOGGER.error("Connection error: %s", e)
        raise
```
