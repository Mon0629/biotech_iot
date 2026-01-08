#!/usr/bin/env python3
import subprocess
from fastapi import FastAPI, Request
import uvicorn
import json
import os

config_path = os.path.join(os.path.dirname(__file__), 'config', 'device_config.json')
app = FastAPI()

HOTSPOT_NAME = "BIOTECH"
HOTSPOT_PASSWORD = "momorevillame24"

with open(config_path, 'r') as f:
    device_config = json.load(f)

print("Loaded device config:", device_config)


def start_ap_mode():
    """Start NetworkManager hotspot for provisioning."""
    print("Starting AP Mode...")

    existing = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True, text=True
    )
    print("Existing connections:", existing.stdout.strip())

    if HOTSPOT_NAME not in existing.stdout:
        result = subprocess.run([
            "nmcli", "device", "wifi", "hotspot",
            "ifname", "wlan0",
            "con-name", HOTSPOT_NAME,
            "ssid", HOTSPOT_NAME,
            "password", HOTSPOT_PASSWORD
        ], capture_output=True, text=True)
        print("Hotspot creation stdout:", result.stdout)
        print("Hotspot creation stderr:", result.stderr)
        print("Hotspot creation returncode:", result.returncode)
    else:
        result = subprocess.run(["nmcli", "connection", "up", HOTSPOT_NAME],
                                capture_output=True, text=True)
        print("Bringing hotspot up stdout:", result.stdout)
        print("Bringing hotspot up stderr:", result.stderr)
        print("Return code:", result.returncode)


def stop_ap_mode():
    """Stop hotspot."""
    print("Stopping AP Mode...")
    result = subprocess.run(["nmcli", "connection", "down", HOTSPOT_NAME],
                            capture_output=True, text=True)
    print("AP stop stdout:", result.stdout)
    print("AP stop stderr:", result.stderr)
    print("AP stop returncode:", result.returncode)


def connect_to_wifi(ssid: str, password: str) -> bool:
    """Connect Pi to WiFi using NetworkManager with detailed logging."""
    print(f"Attempting to connect to WiFi SSID: {ssid}")

    # Delete old config
    del_result = subprocess.run(["nmcli", "connection", "delete", ssid],
                                capture_output=True, text=True)
    print(f"Deleted old connection '{ssid}' stdout:", del_result.stdout)
    print(f"Deleted old connection '{ssid}' stderr:", del_result.stderr)

    # Attempt connection
    result = subprocess.run([
        "nmcli", "device", "wifi", "connect", ssid,
        "password", password, "ifname", "wlan0"
    ], capture_output=True, text=True)

    print("WiFi connect stdout:", result.stdout)
    print("WiFi connect stderr:", result.stderr)
    print("WiFi connect returncode:", result.returncode)

    return result.returncode == 0


def switch_wifi(ssid: str, password: str, pairing_token: str):
    """Switch from AP mode to WiFi client mode."""
    print("Switching WiFi...")
    success = connect_to_wifi(ssid, password)
    if not success:
        print(f"Failed to connect to {ssid}")
        return {"status": "error", "message": f"Failed to connect to {ssid}"}

    print(f"Connected to {ssid}, stopping AP mode...")
    stop_ap_mode()

    # Commented out backend provisioning for now
    # API_URL = os.getenv("BACKEND_API_URL")
    # payload = {
    #     "machine_name": device_config.get("machine_name"),
    #     "serial_number": device_config.get("serial_number"),
    #     "model": device_config.get("model"),
    #     "firmware_version": device_config.get("firmware_version"),
    #     "pairing_token": pairing_token
    # }
    # response = requests.post(f"{API_URL}/devices/provision", json=payload)
    # print("Backend response:", response.text)

    return {"status": "ok", "message": f"Connected to {ssid}"}


@app.post("/provision")
async def provision_wifi(request: Request):
    data = await request.json()
    ssid = data.get("ssid")
    password = data.get("password")
    pairing_token = data.get("pairing_token")

    if not ssid or not password:
        return {"status": "error", "message": "SSID and password required"}

    device_info = switch_wifi(ssid, password, pairing_token)
    return device_info


if __name__ == "__main__":
    # Check if Pi is already on a WiFi network
    check = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
        capture_output=True, text=True
    )
    wlan0_active = "wlan0:connected" in check.stdout
    print("wlan0 status:", check.stdout.strip())

    if not wlan0_active:
        start_ap_mode()
    else:
        print("WiFi already connected. Skipping hotspot startup.")

    uvicorn.run(app, host="0.0.0.0", port=5000)
