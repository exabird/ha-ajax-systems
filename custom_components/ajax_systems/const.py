"""Constants for Ajax Systems integration."""

DOMAIN = "ajax_systems"

# API Configuration
API_BASE_URL = "https://api.ajax.systems/api"
API_TIMEOUT = 30

# Authentication - Common
CONF_API_KEY = "api_key"
CONF_AUTH_MODE = "auth_mode"

# Authentication - Company mode
CONF_COMPANY_ID = "company_id"
CONF_COMPANY_TOKEN = "company_token"

# Authentication - User mode
CONF_USERNAME = "username"
CONF_PASSWORD_HASH = "password_hash"
CONF_SESSION_TOKEN = "session_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_USER_ID = "user_id"
CONF_TOKEN_EXPIRY = "token_expiry"

# Auth modes
AUTH_MODE_COMPANY = "company"
AUTH_MODE_USER = "user"

# Configuration
CONF_HUB_ID = "hub_id"
CONF_SPACE_ID = "space_id"

# AWS SQS Configuration (Enterprise API)
CONF_SQS_ENABLED = "sqs_enabled"
CONF_SQS_QUEUE_URL = "sqs_queue_url"
CONF_AWS_ACCESS_KEY = "aws_access_key"
CONF_AWS_SECRET_KEY = "aws_secret_key"
CONF_AWS_REGION = "aws_region"
DEFAULT_AWS_REGION = "eu-west-1"

# Update intervals (seconds)
DEFAULT_SCAN_INTERVAL = 3
MIN_SCAN_INTERVAL = 3
MAX_SCAN_INTERVAL = 300

# Session token TTL (15 minutes, refresh at 10 minutes)
SESSION_TOKEN_TTL = 15 * 60
SESSION_TOKEN_REFRESH_MARGIN = 5 * 60

# Platforms to set up
PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "sensor",
    "switch",
]

# Signal levels mapping
SIGNAL_LEVEL_MAP = {
    "NO_SIGNAL": 0,
    "WEAK": 33,
    "NORMAL": 66,
    "STRONG": 100,
}

# Device type categories for entity creation
MOTION_SENSORS = [
    "MotionProtect",
    "MotionProtectS",
    "MotionProtectFibra",
    "MotionProtectPlus",
    "MotionProtectSPlus",
    "MotionProtectPlusFibra",
    "MotionProtectOutdoor",
    "MotionCam",
    "MotionCamPhod",
    "MotionCamOutdoor",
    "CombiProtect",
    "CombiProtectS",
    "CombiProtectFibra",
]

DOOR_SENSORS = [
    "DoorProtect",
    "DoorProtectS",
    "DoorProtectU",
    "DoorProtectFibra",
    "DoorProtectPlus",
    "DoorProtectSPlus",
    "DoorProtectPlusFibra",
]

SMOKE_SENSORS = [
    "FireProtect",
    "FireProtectPlus",
    "FireProtect2",
    "FireProtect2Plus",
]

WATER_SENSORS = [
    "LeaksProtect",
    "WaterStop",
]

GLASS_BREAK_SENSORS = [
    "GlassProtect",
    "GlassProtectS",
    "GlassProtectFibra",
]

SWITCHES = [
    "Socket",
    "WallSwitch",
    "Relay",
    "LightSwitch",
]

SIRENS = [
    "HomeSiren",
    "HomeSirenS",
    "HomeSirenFibra",
    "StreetSiren",
    "StreetSirenPlus",
    "StreetSirenFibra",
]

KEYPADS = [
    "Keypad",
    "KeypadPlus",
    "KeypadCombi",
    "KeypadTouchscreen",
]

RANGE_EXTENDERS = [
    "RangeExtender",
    "RangeExtender2",
]
