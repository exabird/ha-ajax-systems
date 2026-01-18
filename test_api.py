#!/usr/bin/env python3
"""Test script for Ajax Systems API."""
import asyncio
import aiohttp

# Load from env file manually
def load_env(filepath):
    env = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key] = value
    return env

env = load_env("/Users/anthony/Cursor/AJAX API/ajax-dashboard/.env.local")

API_BASE_URL = env.get("NEXT_PUBLIC_API_BASE_URL")
API_KEY = env.get("NEXT_PUBLIC_API_KEY")
COMPANY_ID = env.get("NEXT_PUBLIC_COMPANY_ID")
COMPANY_TOKEN = env.get("NEXT_PUBLIC_COMPANY_TOKEN")
HUB_ID = env.get("NEXT_PUBLIC_HUB_ID")


async def test_api():
    """Test the Ajax API."""
    print(f"Testing Ajax API...")
    print(f"Base URL: {API_BASE_URL}")
    print(f"Hub ID: {HUB_ID}")
    print("-" * 50)

    async with aiohttp.ClientSession() as session:
        headers = {
            "X-Api-Key": API_KEY,
            "X-Company-Token": COMPANY_TOKEN,
            "Content-Type": "application/json",
        }

        # Test 1: Get company spaces
        print("\n1. Testing GET /company/{companyId}/spaces...")
        try:
            async with session.get(
                f"{API_BASE_URL}/company/{COMPANY_ID}/spaces",
                headers=headers,
            ) as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   Spaces found: {len(data) if isinstance(data, list) else 'N/A'}")
                    if isinstance(data, list) and len(data) > 0:
                        for space in data:
                            print(f"   - {space.get('name', 'Unknown')} (ID: {space.get('id', 'N/A')})")
                            hubs = space.get('hubs', [])
                            for hub in hubs:
                                hub_id = hub.get('id', 'N/A')
                                marker = " <-- YOUR HUB" if hub_id == HUB_ID else ""
                                print(f"     Hub: {hub.get('name', 'Unknown')} (ID: {hub_id}){marker}")
                else:
                    text = await response.text()
                    print(f"   Error: {text[:200]}")
        except Exception as e:
            print(f"   Exception: {e}")

        # Test 2: Get hub details (only for YOUR hub)
        print(f"\n2. Testing GET hub details for {HUB_ID}...")
        try:
            # Try company endpoint for hub
            async with session.get(
                f"{API_BASE_URL}/company/{COMPANY_ID}/hubs/{HUB_ID}",
                headers=headers,
            ) as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    hub = await response.json()
                    print(f"   Hub Name: {hub.get('name', 'Unknown')}")
                    print(f"   Hub Type: {hub.get('type', hub.get('hubType', 'Unknown'))}")
                    print(f"   Online: {hub.get('online', 'Unknown')}")
                    print(f"   Arm State: {hub.get('armState', hub.get('state', 'Unknown'))}")
                else:
                    text = await response.text()
                    print(f"   Error: {text[:200]}")
        except Exception as e:
            print(f"   Exception: {e}")

        # Test 3: Get devices for YOUR hub only
        print(f"\n3. Testing GET devices for hub {HUB_ID}...")
        try:
            async with session.get(
                f"{API_BASE_URL}/company/{COMPANY_ID}/hubs/{HUB_ID}/devices",
                headers=headers,
                params={"enrich": "true"},
            ) as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    devices = await response.json()
                    device_list = devices if isinstance(devices, list) else devices.get('devices', [])
                    print(f"   Devices found: {len(device_list)}")
                    for device in device_list[:10]:  # Limit to first 10
                        print(f"   - {device.get('deviceName', device.get('name', 'Unknown'))} ({device.get('deviceType', 'Unknown')})")
                        print(f"     Online: {device.get('online', 'N/A')}, Battery: {device.get('batteryChargeLevelPercentage', 'N/A')}%")
                    if len(device_list) > 10:
                        print(f"   ... and {len(device_list) - 10} more devices")
                else:
                    text = await response.text()
                    print(f"   Error: {text[:200]}")
        except Exception as e:
            print(f"   Exception: {e}")

    print("\n" + "=" * 50)
    print("API Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_api())
