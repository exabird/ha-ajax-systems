# Claude Code Instructions

## Project: Ajax Systems Home Assistant Integration

Custom Home Assistant integration for Ajax Systems security devices.

## Communication Rules

- **All GitHub communications must be in English** (issues, comments, PR descriptions, commit messages)
- Code comments in English

## Git Commit Rules - CRITICAL

- **NEVER add "Co-Authored-By" with Claude or any AI in commit messages**
- **NEVER mention Claude, AI, or any AI assistant in commit messages**
- Commits must appear as if written by a human developer only

## Tech Stack

- Python 3.11+
- Home Assistant Core
- aiohttp for async HTTP requests
- Session token authentication (X-Session-Token header)

## API Details

- **Base URL:** https://api.ajax.systems/api
- **Auth Header:** X-Api-Key (always required)
- **Session Header:** X-Session-Token (15 min TTL)
- **Password:** SHA-256 hashed before sending

## Key Files

- `custom_components/ajax_systems/api.py` - API client
- `custom_components/ajax_systems/coordinator.py` - Data update coordinator
- `custom_components/ajax_systems/config_flow.py` - Configuration flow
- `custom_components/ajax_systems/const.py` - Constants

## Key Endpoints

- `POST /login` - Authenticate and get session token
- `POST /refresh` - Refresh session token
- `GET /user/{userId}/spaces` - Get user spaces
- `GET /user/{userId}/hubs/{hubId}` - Get hub details
- `GET /user/{userId}/hubs/{hubId}/devices` - Get devices
- `PUT /user/{userId}/hubs/{hubId}/commands/arming` - Arm/disarm
