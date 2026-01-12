#!/usr/bin/env python3
import subprocess
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json
import os
import requests
import time
import logging
import sys

# ---------------- LOGGING SETUP (ADDED) ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
# ------------------------------------------------------

BACKEND_API = "https://auntlike-karrie-caboshed.ngrok-free.dev/api/v1/devices/provision"

config_path = os.path.join(os.path.dirname(__file__), 'config', 'device_config.json')
app = FastAPI()

HOTSPOT_NAME = "BIOTECH"
HOTSPOT_PASSWORD = "momorevillame24"

with open(config_path, 'r') as f:
    data = json.load(f)

print("DEVICE CONFIG:", data)
logger.info("Loaded device config: %s", data)

def start_ap_mode():
    logger.info("Starting AP Mode...")
    print("Starting AP Mode...")

    existing = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True,
        text=True
    )

    logger.info("Existing NM connections: %s", existing.stdout.strip())

    if HOTSPOT_NAME not in existing.stdout:
        result = subprocess.run([
            "nmcli", "device", "wifi", "hotspot",
            "ifname", "wlan0",
            "con-name", HOTSPOT_NAME,
            "ssid", HOTSPOT_NAME,
            "password", HOTSPOT_PASSWORD
        ], capture_output=True, text=True)

        logger.info("Hotspot create rc=%s stdout=%s stderr=%s",
                    result.returncode, result.stdout, result.stderr)
    else:
        result = subprocess.run(
            ["nmcli", "connection", "up", HOTSPOT_NAME],
            capture_output=True,
            text=True
        )
        logger.info("Hotspot up rc=%s stdout=%s stderr=%s",
                    result.returncode, result.stdout, result.stderr)

def stop_ap_mode():
    logger.info("Stopping AP Mode...")
    print("Stopping AP Mode...")

    result = subprocess.run(
        ["nmcli", "connection", "down", HOTSPOT_NAME],
        capture_output=True,
        text=True
    )

    logger.info("Hotspot down rc=%s stdout=%s stderr=%s",
                result.returncode, result.stdout, result.stderr)

def connect_to_wifi(ssid: str, password: str) -> bool:
    print(f"Connecting to WiFi: {ssid}")

    # Force rescan after AP mode
    subprocess.run(
        ["nmcli", "device", "wifi", "rescan", "ifname", "wlan0"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )

    time.sleep(3)  # non-negotiable

    # Debug: show visible networks
    scan = subprocess.run(
        ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
        capture_output=True,
        text=True
    )
    print("VISIBLE SSIDS:\n", scan.stdout)

    result = subprocess.run(
        [
            "nmcli", "device", "wifi", "connect", ssid,
            "password", password, "ifname", "wlan0"
        ],
        capture_output=True,
        text=True
    )

    print("NMCLI STDOUT:", result.stdout)
    print("NMCLI STDERR:", result.stderr)

    return result.returncode == 0


def send_device_config(pairing_token: str):
    logger.info("Sending device config to backend")

    if not os.path.exists(config_path):
        logger.error("Device config not found at %s", config_path)
        print("Device config not found")
        return False

    with open(config_path, "r") as f:
        device_info = json.load(f)

    payload = {
        "pairing_token": pairing_token,
        "serial_number": device_info["serial_number"],
        "machine_name": device_info.get("machine_name"),
        "model": device_info.get("model"),
        "firmware_version": device_info.get("firmware_version")
    }

    logger.info("Backend payload: %s", payload)

    try:
        response = requests.post(BACKEND_API, json=payload, timeout=10)
        print("Backend response:", response.status_code, response.text)

        logger.info(
            "Backend response status=%s body=%s",
            response.status_code,
            response.text
        )

        return response.status_code == 200
    except Exception:
        logger.exception("Exception while sending device config")
        return False

def switch_wifi(ssid: str, password: str, pairing_token: str):
    logger.info("Background task started: switch_wifi")
    print("Background task: switching WiFi...")

    stop_ap_mode()
    time.sleep(3)

    success = connect_to_wifi(ssid, password)

    if success:
        logger.info("Connected to WiFi: %s", ssid)
        print(f"Connected to {ssid}")
        send_device_config(pairing_token)
    else:
        logger.error("Failed to connect to WiFi: %s", ssid)
        print(f"Failed to connect to {ssid}")

@app.post("/provision")
async def provision_wifi(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    print("RECEIVED PROVISION PAYLOAD:", data)
    logger.info("Received provision payload: %s", data)

    ssid = data.get("ssid")
    password = data.get("password")
    pairing_token = data.get("pairing_token")

    if not ssid or not password or not pairing_token:
        logger.warning("Invalid provision request payload")
        return {
            "status": "error",
            "message": "SSID and password required and pairing token"
        }

    background_tasks.add_task(switch_wifi, ssid, password, pairing_token)

    logger.info("Provisioning task queued for SSID=%s", ssid)

    return {
        "status": "ok",
        "message": f"Provisioning started for {ssid}",
        "device": data
    }

if __name__ == "__main__":
    logger.info("Provision service starting")

    check = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
        capture_output=True,
        text=True
    )

    logger.info("NM device state: %s", check.stdout.strip())

    wlan0_active = "wlan0:connected" in check.stdout

    if not wlan0_active:
        start_ap_mode()
    else:
        logger.info("WiFi already connected. Skipping hotspot startup.")
        print("WiFi already connected. Skipping hotspot startup.")

    uvicorn.run(app, host="0.0.0.0", port=5000)

