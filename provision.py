#!/usr/bin/env python3
import subprocess
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json
import os

config_path = os.path.join(os.path.dirname(__file__), 'config', 'device_config.json')
app = FastAPI()

HOTSPOT_NAME = "BIOTECH"
HOTSPOT_PASSWORD = "momorevillame24"


with open(config_path, 'r') as f:
    device_config = json.load(f)

print(device_config)

def start_ap_mode():
    """Start NetworkManager hotspot for provisioning."""
    print("Starting AP Mode...")

    existing = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True, text=True
    )

    if HOTSPOT_NAME not in existing.stdout:
        subprocess.run([
            "nmcli", "device", "wifi", "hotspot",
            "ifname", "wlan0",
            "con-name", HOTSPOT_NAME,
            "ssid", HOTSPOT_NAME,
            "password", HOTSPOT_PASSWORD
        ])
    else:
        subprocess.run(["nmcli", "connection", "up", HOTSPOT_NAME])


def stop_ap_mode():
    """Stop hotspot."""
    print("Stopping AP Mode...")
    subprocess.run(["nmcli", "connection", "down", HOTSPOT_NAME],
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def connect_to_wifi(ssid: str, password: str) -> bool:
    """Connect Pi to WiFi using NetworkManager."""
    print(f"Connecting to WiFi: {ssid}")

    # Delete old config
    subprocess.run(["nmcli", "connection", "delete", ssid],
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    # Attempt connection
    result = subprocess.run([
        "nmcli", "device", "wifi", "connect", ssid,
        "password", password, "ifname", "wlan0"
    ])

    return result.returncode == 0


def switch_wifi(ssid: str, password: str, pairing_token: str):
    success = connect_to_wifi(ssid, password)
    if not success:
        print(f"Failed to connect to {ssid}")
        return {"status": "error", "message": f"Failed to connect to {ssid}"}

    print(f"Connected to {ssid}, shutting down AP mode...")
    stop_ap_mode()

    API_URL = os.getenv("BACKEND_API_URL")
    payload = {
        "machine_name": device_config.get("machine_name"),
        "serial_number": device_config.get("serial_number"),
        "model": device_config.get("model"),
        "firmware_version": device_config.get("firmware_version"),
        "pairing_token": pairing_token
    }

    try:
        import requests
        response = requests.post(f"{API_URL}/devices/provision", json=payload)
        if response.status_code == 200:
            device_info = response.json().get("device")
            print("Provisioning info sent to backend successfully.")
            return device_info  # <-- return backend-confirmed device info
        else:
            print(f"Failed to notify backend: {response.status_code} - {response.text}")
            return {"status": "error", "message": "Backend provisioning failed"}
    except Exception as e:
        print(f"Error notifying backend: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/provision")
async def provision_wifi(request: Request):
    data = await request.json()
    ssid = data.get("ssid")
    password = data.get("password")
    pairing_token = data.get("pairing_token")

    if not ssid or not password:
        return {"status": "error", "message": "SSID and password required"}

    # Call switch_wifi synchronously to get backend-confirmed device info
    device_info = switch_wifi(ssid, password, pairing_token)

    return {
        "status": "ok",
        "message": f"Provisioning completed for {ssid}",
        "device": device_info
    }



if __name__ == "__main__":
    # Check if Pi is already on a WiFi network
    check = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
        capture_output=True, text=True
    )
    wlan0_active = "wlan0:connected" in check.stdout

    if not wlan0_active:
        start_ap_mode()
    else:
        print("WiFi already connected. Skipping hotspot startup.")

    uvicorn.run(app, host="0.0.0.0", port=5000)

