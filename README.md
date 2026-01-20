# Ajax Systems Integration for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/exabird/ha-ajax-systems)](https://github.com/exabird/ha-ajax-systems/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/exabird)

**100% Open Source** Home Assistant integration for Ajax Systems security devices.

## Features

- **Alarm Control Panel** - Arm/disarm your Ajax security system
- **Motion Sensors** - MotionProtect, MotionCam, CombiProtect
- **Door/Window Sensors** - DoorProtect devices
- **Smoke Sensors** - FireProtect devices
- **Water Leak Sensors** - LeaksProtect devices
- **Glass Break Sensors** - GlassProtect devices
- **Switches** - Socket, WallSwitch, Relay devices
- **Battery & Signal Monitoring** - For all devices
- **Temperature Sensors** - Devices with temperature capability
- **Group/Zone Support** - Manage multiple security zones

## Prerequisites

You need API credentials from Ajax Systems to use this integration.

### How to Get API Access

#### Option 1: Request User API Access (Recommended for home users)

1. Go to **[ajax.systems/api-request](https://ajax.systems/api-request/)**
2. Fill out the request form:
   - Select "User API" as the access type
   - Provide your contact information
   - Describe your use case (e.g., "Home automation integration with Home Assistant")
3. Wait for approval (typically 1-5 business days)
4. Once approved, you'll receive an **API Key** by email

#### Option 2: Through Your Installer

If you have a security company managing your Ajax system:
- Contact your Ajax installer
- Ask them to provide API credentials from the PRO Dashboard
- They can generate Company ID and Company Token for you

### What Credentials Do I Need?

| Authentication Mode | Who Should Use | Required Credentials |
|---------------------|----------------|---------------------|
| **User API** | Home users with API access | API Key + Email + Password |
| **Company/PRO API** | Installers with PRO dashboard | API Key + Company ID + Company Token |

## Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click on **Integrations**
3. Click the **three dots** menu → **Custom repositories**
4. Add `https://github.com/exabird/ha-ajax-systems` with category **Integration**
5. Search for "Ajax Systems" and install
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub](https://github.com/exabird/ha-ajax-systems/releases)
2. Extract and copy `custom_components/ajax_systems` to your HA config folder
3. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for "Ajax Systems"
4. Choose your authentication mode:
   - **User API** - For home users with API key
   - **Company/PRO API** - For installers
5. Enter your credentials
6. Select your hub

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| Update Interval | 30s | How often to poll the Ajax API (10-300 seconds) |

## Supported Devices

### Hubs
- Hub, Hub 2, Hub Plus, Hub 2 Plus
- Hub Hybrid, Hub 4G variants

### Motion Sensors
- MotionProtect (all variants: S, Plus, Fibra, Outdoor)
- MotionCam (all variants: Phod, Outdoor)
- CombiProtect (all variants)

### Door/Window Sensors
- DoorProtect (all variants: S, Plus, U, Fibra)

### Fire/Smoke Sensors
- FireProtect, FireProtect Plus
- FireProtect 2, FireProtect 2 Plus

### Water Sensors
- LeaksProtect
- WaterStop

### Glass Break Sensors
- GlassProtect (all variants)

### Switches & Relays
- Socket
- WallSwitch
- Relay
- LightSwitch

### Sirens
- HomeSiren (all variants)
- StreetSiren (all variants)

### Keypads
- Keypad (all variants)
- KeypadTouchscreen

## Example Automations

### Arm when everyone leaves
```yaml
automation:
  - alias: "Arm Ajax when leaving"
    trigger:
      - platform: state
        entity_id: zone.home
        to: "0"
    action:
      - service: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.ajax_hub
```

### Motion notification while armed
```yaml
automation:
  - alias: "Motion alert when armed"
    trigger:
      - platform: state
        entity_id: binary_sensor.motionprotect_motion
        to: "on"
    condition:
      - condition: state
        entity_id: alarm_control_panel.ajax_hub
        state: "armed_away"
    action:
      - service: notify.mobile_app
        data:
          message: "Motion detected while system is armed!"
```

## Troubleshooting

### "Authentication Failed"
- Verify your API Key is correct and approved
- Check your email/password (User mode) or Company credentials (PRO mode)
- Ensure your account has access to the hub

### "No Hubs Found"
- Verify your hub is online in the Ajax app
- Check that your API credentials have access to this hub

### Slow Updates
- Increase the update interval in integration options
- Check your internet connection
- Verify Ajax Systems API is accessible

### Connection Errors
- Check your internet connection
- Try restarting Home Assistant
- Re-authenticate the integration if needed

## API Documentation

This integration uses the Ajax Systems API. Complete documentation is available in the [docs](./docs/) folder:

- **[API Reference](./docs/API_REFERENCE.md)** - Complete API endpoint documentation
- **[Authentication Guide](./docs/AUTHENTICATION.md)** - Detailed authentication modes and flows
- **[Device Types](./docs/DEVICE_TYPES.md)** - All supported device types and their properties
- **[Code Examples](./docs/EXAMPLES.md)** - Python, JavaScript, and cURL examples

### Quick API Overview

| Aspect | Details |
|--------|---------|
| Base URL | `https://api.ajax.systems/api` |
| Auth Modes | User (session token) / Company (long-lived token) |
| Session TTL | 15 minutes (refresh at 10 min) |
| Password | SHA-256 hashed |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Support

- **Issues**: [GitHub Issues](https://github.com/exabird/ha-ajax-systems/issues)
- **Discussions**: [GitHub Discussions](https://github.com/exabird/ha-ajax-systems/discussions)

### Support the Project

If you find this integration useful, consider buying me a coffee!

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://buymeacoffee.com/exabird)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not officially affiliated with or endorsed by Ajax Systems. Use at your own risk.

---

Made with ❤️ for the Home Assistant community
