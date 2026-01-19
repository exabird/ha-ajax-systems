# Ajax Systems API Authentication Guide

This guide explains the two authentication modes supported by the Ajax Systems API.

## Overview

The Ajax API supports two authentication modes:

| Mode | Use Case | Token Type | Token Lifetime |
|------|----------|------------|----------------|
| **User API** | Home users | Session Token | 15 minutes |
| **Company/PRO API** | Installers | Company Token | Long-lived |

---

## Getting API Access

### Option 1: User API Access (Home Users)

1. Visit [ajax.systems/api-request](https://ajax.systems/api-request/)
2. Fill out the request form:
   - Select "User API" as access type
   - Provide contact information
   - Describe your use case (e.g., "Home Assistant integration")
3. Wait for approval (typically 1-5 business days)
4. Receive your **API Key** by email

### Option 2: Company/PRO API Access (Installers)

Contact your Ajax installer or security company to obtain:
- **API Key**
- **Company ID**
- **Company Token**

These credentials are generated from the Ajax PRO Dashboard.

---

## User Authentication Mode

### Flow Diagram

```
┌─────────────────┐
│   Application   │
└────────┬────────┘
         │
         ▼ POST /login
┌─────────────────┐     ┌─────────────────┐
│   Ajax API      │────▶│ Session Token   │
│                 │     │ (15 min TTL)    │
│                 │     │                 │
│                 │     │ Refresh Token   │
│                 │     │ (7 day TTL)     │
└─────────────────┘     └────────┬────────┘
                                 │
         ┌───────────────────────┘
         │
         ▼ Use X-Session-Token header
┌─────────────────┐
│  API Requests   │
└────────┬────────┘
         │
         │ Token expired?
         ▼ POST /refresh
┌─────────────────┐
│  New Tokens     │
└─────────────────┘
```

### Step 1: Hash the Password

**IMPORTANT:** Never send plaintext passwords to the API.

```python
import hashlib

def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# Example
password = "mySecurePassword123"
password_hash = hash_password(password)
# Result: "e3b0c44298fc1c149afbf4c8996fb924..."
```

```javascript
// JavaScript/Node.js
const crypto = require('crypto');

function hashPassword(password) {
    return crypto.createHash('sha256').update(password).digest('hex');
}
```

### Step 2: Login

```http
POST /api/login HTTP/1.1
Host: api.ajax.systems
X-Api-Key: your-api-key
Content-Type: application/json

{
    "login": "user@example.com",
    "passwordHash": "e3b0c44298fc1c149afbf4c8996fb924...",
    "userRole": "USER"
}
```

**Response:**
```json
{
    "sessionToken": "abc123def456...",
    "userId": "user789xyz...",
    "refreshToken": "refresh123abc..."
}
```

### Step 3: Make Authenticated Requests

Include the session token in all subsequent requests:

```http
GET /api/user/{userId}/hubs/{hubId} HTTP/1.1
Host: api.ajax.systems
X-Api-Key: your-api-key
X-Session-Token: abc123def456...
```

### Step 4: Refresh Token Before Expiry

Session tokens expire after **15 minutes**. Refresh them proactively:

```http
POST /api/refresh HTTP/1.1
Host: api.ajax.systems
X-Api-Key: your-api-key
Content-Type: application/json

{
    "userId": "user789xyz...",
    "refreshToken": "refresh123abc..."
}
```

**Response:**
```json
{
    "sessionToken": "newSession456...",
    "userId": "user789xyz...",
    "refreshToken": "newRefresh789..."
}
```

### Token Lifecycle Management

```python
from datetime import datetime, timedelta

class TokenManager:
    SESSION_TOKEN_TTL = 15 * 60  # 15 minutes
    REFRESH_MARGIN = 5 * 60      # Refresh 5 minutes before expiry

    def __init__(self):
        self.session_token = None
        self.refresh_token = None
        self.token_expiry = None

    def set_tokens(self, session_token, refresh_token):
        self.session_token = session_token
        self.refresh_token = refresh_token
        self.token_expiry = datetime.now() + timedelta(seconds=self.SESSION_TOKEN_TTL)

    def needs_refresh(self) -> bool:
        if not self.token_expiry:
            return True
        return datetime.now() >= (self.token_expiry - timedelta(seconds=self.REFRESH_MARGIN))
```

---

## Company/PRO Authentication Mode

### Configuration

Company authentication uses a long-lived token that doesn't require refresh:

```http
GET /api/company/{companyId}/hubs/{hubId} HTTP/1.1
Host: api.ajax.systems
X-Api-Key: your-api-key
X-Company-Token: your-company-token
```

### Differences from User Mode

| Aspect | User Mode | Company Mode |
|--------|-----------|--------------|
| Token refresh | Required every 15 min | Not required |
| Login endpoint | POST /login | Not needed |
| Base path | `/user/{userId}/...` | `/company/{companyId}/...` |
| Access scope | User's hubs only | Company's managed hubs |

---

## Error Handling

### 401 Unauthorized

Causes:
- Expired session token
- Invalid token
- Invalid API key

Solution:
```python
async def make_request(self, endpoint):
    try:
        response = await self._request(endpoint)
        return response
    except AuthError:
        # Refresh token and retry
        await self.refresh_session()
        return await self._request(endpoint)
```

### 403 Forbidden

Causes:
- No access to the requested resource
- API key doesn't have required permissions

Solution:
- Verify API key permissions
- Check hub access rights

---

## Security Best Practices

### DO:
- Store tokens securely (encrypted storage, environment variables)
- Hash passwords client-side before sending
- Refresh tokens proactively
- Use HTTPS exclusively
- Implement proper error handling

### DON'T:
- Log or print tokens/API keys
- Store plaintext passwords
- Share API keys in public repositories
- Ignore token expiration

### Example: Secure Token Storage

```python
import os
from cryptography.fernet import Fernet

class SecureTokenStorage:
    def __init__(self):
        # Get encryption key from environment
        self.key = os.environ.get('TOKEN_ENCRYPTION_KEY')
        self.cipher = Fernet(self.key)

    def store_token(self, token: str) -> bytes:
        return self.cipher.encrypt(token.encode())

    def retrieve_token(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
```

---

## Integration with Home Assistant

This integration handles authentication automatically:

1. **Configuration Flow**
   - User enters credentials in the UI
   - Password is hashed before storage
   - Tokens are stored in Home Assistant's secure storage

2. **Runtime**
   - Coordinator manages token refresh
   - Automatic retry on 401 errors
   - Graceful handling of connection issues

3. **Token Persistence**
   - Session and refresh tokens stored between restarts
   - Automatic re-login if refresh token expires

---

## Quick Reference

### Required Headers - User Mode
```
X-Api-Key: <api-key>
X-Session-Token: <session-token>
Content-Type: application/json
```

### Required Headers - Company Mode
```
X-Api-Key: <api-key>
X-Company-Token: <company-token>
Content-Type: application/json
```

### Token Lifetimes
- Session Token: **15 minutes**
- Refresh Token: **7 days**
- Company Token: **Long-lived** (no expiry)

### Password Hash
```
SHA-256(plaintext_password) → 64-character hex string
```
