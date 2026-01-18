#!/usr/bin/env python3
"""Detailed test script for Ajax Systems API."""
import asyncio
import aiohttp
import json

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


async def test_api_detailed():
    """Test the Ajax API with detailed output."""
    print("=" * 60)
    print("AJAX API DETAILED TEST")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        headers = {
            "X-Api-Key": API_KEY,
            "X-Company-Token": COMPANY_TOKEN,
            "Content-Type": "application/json",
        }

        # Get hub details
        print("\n--- HUB DETAILS ---")
        async with session.get(
            f"{API_BASE_URL}/company/{COMPANY_ID}/hubs/{HUB_ID}",
            headers=headers,
        ) as response:
            if response.status == 200:
                hub = await response.json()
                print(json.dumps(hub, indent=2, default=str)[:2000])

        # Get first device details
        print("\n--- FIRST DEVICE DETAILS ---")
        async with session.get(
            f"{API_BASE_URL}/company/{COMPANY_ID}/hubs/{HUB_ID}/devices",
            headers=headers,
            params={"enrich": "true"},
        ) as response:
            if response.status == 200:
                devices = await response.json()
                device_list = devices if isinstance(devices, list) else devices.get('devices', devices.get('deviceInfos', []))
                if device_list:
                    print(f"Total devices: {len(device_list)}")
                    print("\nFirst device structure:")
                    print(json.dumps(device_list[0], indent=2, default=str)[:3000])

                    # Look for battery info
                    print("\n--- BATTERY INFO SEARCH ---")
                    for d in device_list[:3]:
                        name = d.get('deviceName', d.get('name', 'Unknown'))
                        print(f"\n{name}:")
                        for key in d.keys():
                            if 'batt' in key.lower() or 'power' in key.lower() or 'charge' in key.lower():
                                print(f"  {key}: {d[key]}")
                        # Check nested objects
                        for key, value in d.items():
                            if isinstance(value, dict):
                                for k2, v2 in value.items():
                                    if 'batt' in k2.lower():
                                        print(f"  {key}.{k2}: {v2}")

    print("\n" + "=" * 60)
    print("DETAILED TEST COMPLETE!")


if __name__ == "__main__":
    asyncio.run(test_api_detailed())
