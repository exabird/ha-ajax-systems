# Ajax Systems API Reference

This document provides comprehensive documentation for the Ajax Systems API used by this Home Assistant integration.

**Base URL:** `https://api.ajax.systems/api`
**API Version:** 1.130.0

## Table of Contents

- [Authentication](#authentication)
  - [User Authentication Mode](#user-authentication-mode)
  - [Company/PRO Authentication Mode](#companypro-authentication-mode)
- [Core Endpoints](#core-endpoints)
  - [Login & Session Management](#login--session-management)
  - [Spaces](#spaces)
  - [Hubs](#hubs)
  - [Devices](#devices)
  - [Groups](#groups)
  - [Arming Commands](#arming-commands)
- [Data Structures](#data-structures)
- [Error Handling](#error-handling)
- [Rate Limits & Best Practices](#rate-limits--best-practices)

---

## Authentication

All API requests require authentication via headers. The API supports two authentication modes:

### Common Header

All requests must include:

```
X-Api-Key: <your-api-key>
Content-Type: application/json
```

### User Authentication Mode

For home users with API access. Uses session tokens that expire after 15 minutes.

**Headers:**
```
X-Api-Key: <your-api-key>
X-Session-Token: <session-token>
```

**Session Token Lifecycle:**
- TTL: 15 minutes
- Refresh Token TTL: 7 days
- Recommended: Refresh token at 10-minute mark to avoid expiration

**Password Hashing:**
> Never send plaintext passwords. Always use SHA-256 hashing.

```python
import hashlib
password_hash = hashlib.sha256(password.encode()).hexdigest()
```

### Company/PRO Authentication Mode

For installers and security companies with PRO dashboard access.

**Headers:**
```
X-Api-Key: <your-api-key>
X-Company-Token: <company-token>
```

Company tokens are long-lived and don't require refresh.

---

## Core Endpoints

### Login & Session Management

#### POST /login

Authenticate and obtain session tokens (User mode only).

**Request:**
```json
{
  "login": "user@example.com",
  "passwordHash": "<sha256-hash-of-password>",
  "userRole": "USER"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| login | string | Yes | Email address (max 64 bytes) |
| passwordHash | string | Yes | SHA-256 hash of password |
| userRole | string | No | `USER` (default) or `PRO` |

**Response:**
```json
{
  "sessionToken": "abc123...",
  "userId": "def456...",
  "refreshToken": "ghi789..."
}
```

#### POST /refresh

Refresh an expired session token.

**Request:**
```json
{
  "userId": "<user-id>",
  "refreshToken": "<refresh-token>"
}
```

**Response:**
```json
{
  "sessionToken": "<new-session-token>",
  "userId": "<user-id>",
  "refreshToken": "<new-refresh-token>"
}
```

---

### Spaces

Spaces are top-level containers that can contain hubs and other resources.

#### GET /user/{userId}/spaces

Get all spaces for a user.

**Response:**
```json
[
  {
    "id": "space123",
    "name": "My Home",
    "hubs": [...],
    "rooms": [...]
  }
]
```

#### GET /company/{companyId}/spaces

Get all spaces for a company (Company mode).

---

### Hubs

#### GET /user/{userId}/hubs/{hubId}

Get hub details.

**Response:**
```json
{
  "id": "hub123",
  "name": "Main Hub",
  "model": "Hub 2 Plus",
  "online": true,
  "state": "ARMED",
  "firmwareVersion": "2.15.1",
  "connectionType": "ETHERNET",
  "gsmSignalLevel": "STRONG",
  "batteryLevel": 100,
  "groups": [...],
  "rooms": [...]
}
```

**Hub States:**
- `ARMED` - System is armed
- `DISARMED` - System is disarmed
- `PARTIAL_ARMED` - Some groups armed
- `ARMING` - Arming in progress
- `DISARMING` - Disarming in progress

#### GET /company/{companyId}/hubs/{hubId}

Get hub details (Company mode).

---

### Devices

#### GET /user/{userId}/hubs/{hubId}/devices

Get all devices for a hub.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| enrich | boolean | true | Include detailed device info |

**Response:**
```json
[
  {
    "id": "device123",
    "type": "MotionProtect",
    "name": "Living Room Motion",
    "roomId": "room456",
    "groupId": "group789",
    "online": true,
    "batteryLevel": 95,
    "signalLevel": "STRONG",
    "state": {
      "motion": false,
      "tamper": false
    },
    "temperature": 22.5
  }
]
```

#### GET /company/{companyId}/hubs/{hubId}/devices

Get all devices (Company mode).

#### POST /user/{userId}/hubs/{hubId}/devices/{deviceId}/command

Send a command to a device.

**Request:**
```json
{
  "command": "SWITCH_ON",
  "deviceType": "Socket",
  "additionalParam": {}
}
```

**Common Commands:**
| Command | Applicable Devices | Description |
|---------|-------------------|-------------|
| `SWITCH_ON` | Socket, Relay, WallSwitch | Turn device on |
| `SWITCH_OFF` | Socket, Relay, WallSwitch | Turn device off |
| `MUTE` | Siren | Mute the siren |

---

### Groups

Groups allow you to organize devices and arm/disarm specific zones.

#### GET /user/{userId}/hubs/{hubId}/groups

Get all groups for a hub.

**Response:**
```json
[
  {
    "id": "group123",
    "groupName": "Perimeter",
    "state": "ARMED",
    "bulkArmInvolved": true,
    "bulkDisarmInvolved": true,
    "twoStageArming": "DISABLED"
  }
]
```

**Group States:**
- `ARMED`
- `DISARMED`

---

### Arming Commands

#### PUT /user/{userId}/hubs/{hubId}/commands/arming

Arm or disarm the entire hub.

**Request:**
```json
{
  "command": "ARM",
  "ignoreProblems": false
}
```

**Commands:**
| Command | Description |
|---------|-------------|
| `ARM` | Arm the hub |
| `DISARM` | Disarm the hub |

**Parameters:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| command | string | Required | ARM or DISARM |
| ignoreProblems | boolean | false | Arm even with open sensors |

#### PUT /user/{userId}/hubs/{hubId}/groups/{groupId}/commands/arming

Arm or disarm a specific group.

**Request:**
```json
{
  "command": "ARM",
  "ignoreProblems": false
}
```

**Commands:**
| Command | Description |
|---------|-------------|
| `ARM` | Arm the group |
| `DISARM` | Disarm the group |
| `NIGHT_MODE_ON` | Enable night mode |
| `NIGHT_MODE_OFF` | Disable night mode |

---

## Data Structures

### Signal Levels

```
NO_SIGNAL = 0%
WEAK = 33%
NORMAL = 66%
STRONG = 100%
```

### Device Types

See [DEVICE_TYPES.md](./DEVICE_TYPES.md) for complete device type documentation.

### Event Types

| Type | Description |
|------|-------------|
| `ALARM` | Alarm triggered |
| `ALARM_RECOVERED` | Alarm cleared |
| `MALFUNCTION` | Device malfunction |
| `FUNCTION_RECOVERED` | Malfunction cleared |
| `SECURITY` | Security event |
| `COMMON` | Common event |
| `USER` | User action |
| `LIFECYCLE` | System lifecycle event |

### Transition States

| State | Description |
|-------|-------------|
| `TRIGGERED` | Event just triggered |
| `RECOVERED` | Event recovered |
| `IMPULSE` | Momentary event |

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 202 | Async operation in progress |
| 204 | Success (no content) |
| 400 | Bad request |
| 401 | Authentication failed |
| 403 | Access forbidden |
| 404 | Resource not found |
| 412 | Precondition failed (e.g., arming prevented) |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Error Response Format

```json
{
  "error": "AUTHENTICATION_FAILED",
  "message": "Invalid session token"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Expired or invalid token | Refresh session token |
| 403 Forbidden | No access to resource | Check permissions |
| 412 Precondition Failed | Cannot arm (open sensors) | Use `ignoreProblems: true` or close sensors |

---

## Rate Limits & Best Practices

### Recommended Polling Intervals

| Operation | Minimum Interval | Recommended |
|-----------|-----------------|-------------|
| Device status | 10 seconds | 30 seconds |
| Hub status | 10 seconds | 30 seconds |
| Event logs | 30 seconds | 60 seconds |

### Best Practices

1. **Token Management**
   - Refresh tokens proactively (at 10-minute mark, before 15-minute expiry)
   - Store refresh tokens securely
   - Handle 401 errors by refreshing and retrying

2. **Efficient Polling**
   - Use `enrich=true` to get all device data in one call
   - Batch requests where possible
   - Implement exponential backoff on errors

3. **Error Handling**
   - Always handle 401/403 errors gracefully
   - Implement retry logic with backoff
   - Log errors for debugging

4. **Security**
   - Never log or expose API keys or tokens
   - Always use HTTPS
   - Hash passwords client-side before sending

---

## Additional Resources

- [Device Types Reference](./DEVICE_TYPES.md)
- [Authentication Guide](./AUTHENTICATION.md)
- [Examples](./EXAMPLES.md)
