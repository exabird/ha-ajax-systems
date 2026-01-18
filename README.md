# Ajax Systems Integration for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/exabird/ha-ajax-systems)](https://github.com/exabird/ha-ajax-systems/releases)
[![License](https://img.shields.io/github/license/exabird/ha-ajax-systems)](LICENSE)

Custom Home Assistant integration for **Ajax Systems** security devices.

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

## Requirements

- **Ajax Systems API Key** - Required for authentication
- **Ajax Systems Account** - With access to your hub
- **Home Assistant 2024.1.0+**

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
4. Enter your credentials:
   - **API Key**: Your Ajax Systems API key
   - **Email**: Your Ajax account email
   - **Password**: Your Ajax account password
5. Select your space (if you have multiple)
6. Done!

## Getting an API Key

To use this integration, you need an API key from Ajax Systems:

1. Contact Ajax Systems support or visit their developer portal
2. Request API access for your account
3. You will receive an API key to use with this integration

## Supported Devices

### Hubs
- Hub, Hub 2, Hub Plus, Hub 2 Plus
- Hub Hybrid, Hub 4G variants

### Sensors
- MotionProtect (all variants)
- DoorProtect (all variants)
- FireProtect, FireProtect 2
- LeaksProtect, WaterStop
- GlassProtect
- CombiProtect

### Control Devices
- Keypad (all variants)
- Button, DoubleButton
- SpaceControl

### Switches & Relays
- Socket
- WallSwitch
- Relay
- LightSwitch

### Sirens
- HomeSiren
- StreetSiren (all variants)

## Services

### `ajax_systems.arm`
Arm the security system.

### `ajax_systems.disarm`
Disarm the security system.

## Troubleshooting

### Authentication Failed
- Verify your API key is correct
- Check your email and password
- Ensure your account has API access enabled

### No Devices Found
- Verify your hub is online in the Ajax app
- Check that devices are properly paired with your hub

### Slow Updates
- Adjust the scan interval in integration options
- Default is 30 seconds, minimum 10 seconds

## Support

- [GitHub Issues](https://github.com/exabird/ha-ajax-systems/issues)
- [Home Assistant Community](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not officially affiliated with or endorsed by Ajax Systems. Use at your own risk.
