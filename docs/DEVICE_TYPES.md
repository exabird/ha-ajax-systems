# Ajax Systems Device Types Reference

Complete reference for all device types supported by the Ajax Systems API.

## Table of Contents

- [Device Categories](#device-categories)
- [Motion Sensors](#motion-sensors)
- [Door/Window Sensors](#doorwindow-sensors)
- [Fire/Smoke Sensors](#firesmoke-sensors)
- [Water Leak Sensors](#water-leak-sensors)
- [Glass Break Sensors](#glass-break-sensors)
- [Switches & Relays](#switches--relays)
- [Sirens](#sirens)
- [Keypads](#keypads)
- [Hubs](#hubs)
- [Other Devices](#other-devices)
- [Device State Properties](#device-state-properties)
- [Signal Levels](#signal-levels)

---

## Device Categories

| Category | Device Types | Home Assistant Entity |
|----------|-------------|----------------------|
| Motion | MotionProtect, MotionCam, CombiProtect | `binary_sensor` (motion) |
| Door/Window | DoorProtect | `binary_sensor` (door) |
| Fire/Smoke | FireProtect | `binary_sensor` (smoke) |
| Water | LeaksProtect, WaterStop | `binary_sensor` (moisture) |
| Glass Break | GlassProtect | `binary_sensor` (vibration) |
| Switches | Socket, Relay, WallSwitch | `switch` |
| Sirens | HomeSiren, StreetSiren | `binary_sensor` |
| Keypads | Keypad, KeypadPlus | `binary_sensor` |

---

## Motion Sensors

### MotionProtect Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `MotionProtect` | MotionProtect | Basic PIR motion |
| `MotionProtectS` | MotionProtect S | Slim design |
| `MotionProtectFibra` | MotionProtect Fibra | Wired connection |
| `MotionProtectPlus` | MotionProtect Plus | Dual PIR + microwave |
| `MotionProtectSPlus` | MotionProtect S Plus | Slim + dual tech |
| `MotionProtectPlusFibra` | MotionProtect Plus Fibra | Wired dual tech |
| `MotionProtectOutdoor` | MotionProtect Outdoor | Outdoor rated |

**State Properties:**
```json
{
  "motion": true,           // Motion detected
  "tamper": false,          // Cover opened
  "batteryLevel": 95,       // Battery percentage
  "signalLevel": "STRONG",  // Signal strength
  "temperature": 22.5       // Temperature (if supported)
}
```

### MotionCam Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `MotionCam` | MotionCam | Photo on alarm |
| `MotionCamPhod` | MotionCam PhOD | Photo on demand |
| `MotionCamOutdoor` | MotionCam Outdoor | Outdoor with camera |

**Additional Properties:**
```json
{
  "photoAvailable": true,   // Photo capture available
  "lastPhotoTimestamp": 1699123456000
}
```

### CombiProtect Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `CombiProtect` | CombiProtect | Motion + glass break |
| `CombiProtectS` | CombiProtect S | Slim combo |
| `CombiProtectFibra` | CombiProtect Fibra | Wired combo |

**State Properties:**
```json
{
  "motion": false,
  "glassBreak": false,
  "tamper": false,
  "batteryLevel": 88
}
```

---

## Door/Window Sensors

### DoorProtect Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `DoorProtect` | DoorProtect | Basic magnetic contact |
| `DoorProtectS` | DoorProtect S | Slim design |
| `DoorProtectU` | DoorProtect U | Universal mounting |
| `DoorProtectFibra` | DoorProtect Fibra | Wired connection |
| `DoorProtectPlus` | DoorProtect Plus | Tilt & vibration |
| `DoorProtectSPlus` | DoorProtect S Plus | Slim + extra sensors |
| `DoorProtectPlusFibra` | DoorProtect Plus Fibra | Wired advanced |

**State Properties:**
```json
{
  "open": true,             // Door/window open
  "tamper": false,          // Cover opened
  "batteryLevel": 100,
  "signalLevel": "NORMAL",
  "tilt": false,            // Plus models only
  "vibration": false        // Plus models only
}
```

---

## Fire/Smoke Sensors

### FireProtect Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `FireProtect` | FireProtect | Smoke + temperature |
| `FireProtectPlus` | FireProtect Plus | + CO detection |
| `FireProtect2` | FireProtect 2 | Next gen smoke |
| `FireProtect2Plus` | FireProtect 2 Plus | Next gen + CO |

**State Properties:**
```json
{
  "smoke": false,           // Smoke detected
  "temperature": 24.0,      // Current temperature
  "temperatureAlarm": false,// Temperature threshold exceeded
  "co": false,              // CO detected (Plus models)
  "coLevel": 0,             // CO PPM (Plus models)
  "tamper": false,
  "batteryLevel": 92
}
```

---

## Water Leak Sensors

| API Type | Product Name | Features |
|----------|-------------|----------|
| `LeaksProtect` | LeaksProtect | Water leak detection |
| `WaterStop` | WaterStop | Valve control |

### LeaksProtect

**State Properties:**
```json
{
  "leak": false,            // Water detected
  "tamper": false,
  "batteryLevel": 100,
  "signalLevel": "STRONG"
}
```

### WaterStop

**State Properties:**
```json
{
  "leak": false,
  "valveState": "OPEN",     // OPEN, CLOSED
  "tamper": false,
  "batteryLevel": 85
}
```

**Commands:**
- `VALVE_OPEN` - Open water valve
- `VALVE_CLOSE` - Close water valve

---

## Glass Break Sensors

| API Type | Product Name | Features |
|----------|-------------|----------|
| `GlassProtect` | GlassProtect | Acoustic glass break |
| `GlassProtectS` | GlassProtect S | Slim design |
| `GlassProtectFibra` | GlassProtect Fibra | Wired connection |

**State Properties:**
```json
{
  "glassBreak": false,      // Glass break detected
  "tamper": false,
  "batteryLevel": 97,
  "signalLevel": "NORMAL"
}
```

---

## Switches & Relays

| API Type | Product Name | Features |
|----------|-------------|----------|
| `Socket` | Socket | Smart plug |
| `WallSwitch` | WallSwitch | In-wall switch |
| `Relay` | Relay | Dry contact relay |
| `LightSwitch` | LightSwitch | Touch light switch |

**State Properties:**
```json
{
  "state": "ON",            // ON, OFF
  "power": 150.5,           // Current power (Watts)
  "energy": 1234.5,         // Total energy (kWh)
  "signalLevel": "STRONG"
}
```

**Commands:**
- `SWITCH_ON` - Turn device on
- `SWITCH_OFF` - Turn device off

**Example Command:**
```json
POST /user/{userId}/hubs/{hubId}/devices/{deviceId}/command
{
  "command": "SWITCH_ON",
  "deviceType": "Socket"
}
```

---

## Sirens

### HomeSiren Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `HomeSiren` | HomeSiren | Indoor siren |
| `HomeSirenS` | HomeSiren S | Slim indoor |
| `HomeSirenFibra` | HomeSiren Fibra | Wired indoor |

### StreetSiren Family

| API Type | Product Name | Features |
|----------|-------------|----------|
| `StreetSiren` | StreetSiren | Outdoor siren |
| `StreetSirenPlus` | StreetSiren Plus | + LED frame |
| `StreetSirenFibra` | StreetSiren Fibra | Wired outdoor |

**State Properties:**
```json
{
  "active": false,          // Siren sounding
  "tamper": false,
  "batteryLevel": 100,
  "signalLevel": "STRONG"
}
```

---

## Keypads

| API Type | Product Name | Features |
|----------|-------------|----------|
| `Keypad` | Keypad | Basic keypad |
| `KeypadPlus` | KeypadPlus | + Card reader |
| `KeypadCombi` | KeypadCombi | + Panic button |
| `KeypadTouchscreen` | KeypadTouchscreen | Touch display |

**State Properties:**
```json
{
  "tamper": false,
  "batteryLevel": 95,
  "signalLevel": "NORMAL",
  "lastUsed": 1699123456000
}
```

---

## Hubs

| API Type | Product Name | Features |
|----------|-------------|----------|
| `Hub` | Hub | Basic hub |
| `Hub2` | Hub 2 | Improved hub |
| `HubPlus` | Hub Plus | Extended range |
| `Hub2Plus` | Hub 2 Plus | Premium hub |
| `HubHybrid` | Hub Hybrid | Fibra + wireless |

**Hub Properties:**
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
  "wifiSignalLevel": "NORMAL",
  "batteryLevel": 100,
  "batteryState": "CHARGING",
  "powerState": "MAINS"
}
```

**Hub States:**
- `ARMED` - Fully armed
- `DISARMED` - Fully disarmed
- `PARTIAL_ARMED` - Some groups armed
- `ARMING` - Arming in progress
- `DISARMING` - Disarming in progress

---

## Other Devices

### Range Extenders

| API Type | Product Name |
|----------|-------------|
| `RangeExtender` | ReX |
| `RangeExtender2` | ReX 2 |

### Buttons

| API Type | Product Name |
|----------|-------------|
| `Button` | Button |
| `DoubleButton` | DoubleButton |
| `SpaceControl` | SpaceControl |

### Transmitters

| API Type | Product Name |
|----------|-------------|
| `Transmitter` | Transmitter |
| `MultiTransmitter` | MultiTransmitter |
| `MultiTransmitterFibra` | MultiTransmitter Fibra |

---

## Device State Properties

### Common Properties (All Devices)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique device ID |
| `type` | string | Device type code |
| `name` | string | User-defined name |
| `roomId` | string | Room assignment |
| `groupId` | string | Security group |
| `online` | boolean | Connection status |
| `batteryLevel` | integer | Battery % (0-100) |
| `signalLevel` | string | Signal strength |

### Battery-Powered Devices

| Property | Type | Description |
|----------|------|-------------|
| `batteryLevel` | integer | 0-100 percentage |
| `batteryState` | string | OK, LOW, CRITICAL |

### Wireless Devices

| Property | Type | Description |
|----------|------|-------------|
| `signalLevel` | string | Signal strength |
| `jeweller` | boolean | Uses Jeweller protocol |

### Temperature-Capable Devices

| Property | Type | Description |
|----------|------|-------------|
| `temperature` | float | Celsius |
| `temperatureAlarm` | boolean | Threshold exceeded |

---

## Signal Levels

The API returns signal levels as string constants:

| API Value | Percentage | Description |
|-----------|------------|-------------|
| `NO_SIGNAL` | 0% | No signal |
| `WEAK` | 33% | Poor signal |
| `NORMAL` | 66% | Good signal |
| `STRONG` | 100% | Excellent signal |

**Conversion Code:**
```python
SIGNAL_LEVEL_MAP = {
    "NO_SIGNAL": 0,
    "WEAK": 33,
    "NORMAL": 66,
    "STRONG": 100,
}

def signal_to_percent(signal_level: str) -> int:
    return SIGNAL_LEVEL_MAP.get(signal_level, 0)
```

---

## Device Type Detection

Use these lists to categorize devices:

```python
MOTION_SENSORS = [
    "MotionProtect", "MotionProtectS", "MotionProtectFibra",
    "MotionProtectPlus", "MotionProtectSPlus", "MotionProtectPlusFibra",
    "MotionProtectOutdoor", "MotionCam", "MotionCamPhod",
    "MotionCamOutdoor", "CombiProtect", "CombiProtectS", "CombiProtectFibra"
]

DOOR_SENSORS = [
    "DoorProtect", "DoorProtectS", "DoorProtectU", "DoorProtectFibra",
    "DoorProtectPlus", "DoorProtectSPlus", "DoorProtectPlusFibra"
]

SMOKE_SENSORS = [
    "FireProtect", "FireProtectPlus", "FireProtect2", "FireProtect2Plus"
]

WATER_SENSORS = ["LeaksProtect", "WaterStop"]

GLASS_BREAK_SENSORS = ["GlassProtect", "GlassProtectS", "GlassProtectFibra"]

SWITCHES = ["Socket", "WallSwitch", "Relay", "LightSwitch"]

SIRENS = [
    "HomeSiren", "HomeSirenS", "HomeSirenFibra",
    "StreetSiren", "StreetSirenPlus", "StreetSirenFibra"
]

KEYPADS = ["Keypad", "KeypadPlus", "KeypadCombi", "KeypadTouchscreen"]
```

---

## API Response Examples

### Get Devices Response

```json
GET /user/{userId}/hubs/{hubId}/devices?enrich=true

[
  {
    "id": "device001",
    "type": "MotionProtect",
    "name": "Living Room Motion",
    "roomId": "room001",
    "groupId": "group001",
    "online": true,
    "batteryLevel": 95,
    "signalLevel": "STRONG",
    "state": {
      "motion": false,
      "tamper": false
    },
    "firmwareVersion": "5.54.1.0"
  },
  {
    "id": "device002",
    "type": "DoorProtect",
    "name": "Front Door",
    "roomId": "room002",
    "groupId": "group001",
    "online": true,
    "batteryLevel": 100,
    "signalLevel": "NORMAL",
    "state": {
      "open": false,
      "tamper": false
    }
  },
  {
    "id": "device003",
    "type": "Socket",
    "name": "Lamp Socket",
    "roomId": "room001",
    "groupId": null,
    "online": true,
    "signalLevel": "STRONG",
    "state": {
      "state": "OFF",
      "power": 0
    }
  }
]
```
