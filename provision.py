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
import threading

# ---------------- LOGGING SETUP ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
# ------------------------------------------------

#BACKEND_API="hydronew.me/api/v1/devices/provision"
#BACKEND_API = "https://auntlike-karrie-caboshed.ngrok-free.dev/api/v1/devices/provision"
BACKEND_API = "https://latarsha-nonconcessive-telically.ngrok-free.dev/api/v1/devices/provision"

config_path = os.path.join(os.path.dirname(__file__), 'config', 'device_config.json')
app = FastAPI()

watchdog_enabled = True

HOTSPOT_NAME = "BIOTECH"
HOTSPOT_PASSWORD = "momorevillame24"

with open(config_path, 'r') as f:
    data = json.load(f)

print("DEVICE CONFIG:", data)
logger.info("Loaded device config: %s", data)

def get_current_ssid() -> str | None:
    """Return the SSID wlan0 is currently connected to, or None if disconnected."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "device", "status"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split(":")
            if len(parts) >= 3 and parts[0] == "wlan0":
                state, conn = parts[1], parts[2]
                if state == "connected" and conn != HOTSPOT_NAME:
                    return conn
        return None
    except Exception:
        return None


def is_ap_active() -> bool:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
        capture_output=True,
        text=True
    )
    return any(
        line.startswith(HOTSPOT_NAME + ":")
        for line in result.stdout.splitlines()
    )

def is_client_wifi_connected() -> str | None:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
        capture_output=True,
        text=True
    )

    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue

        device, dev_type, state, connection = parts

        if (
            device == "wlan0"
            and dev_type == "wifi"
            and state in ["connected", "connecting"]
            and connection != HOTSPOT_NAME
        ):
            return True

    return None



def is_client_wifi_connected() -> bool:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
        capture_output=True,
        text=True
    )

    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue

        device, dev_type, state, connection = parts

        if (
            device == "wlan0"
            and dev_type == "wifi"
            and state in ["connected", "connecting"]
            and connection != HOTSPOT_NAME
        ):
            return True

    return False


def get_saved_wifi_connections() -> list:
    """
    Get list of saved WiFi connections from NetworkManager (excluding the hotspot).
    Returns a list of connection names that are WiFi type.
    """
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
            capture_output=True,
            text=True
        )
        saved_networks = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(":")
            if len(parts) >= 2:
                name, conn_type = parts[0], parts[1]
                # Include wifi connections but exclude the hotspot
                if conn_type == "802-11-wireless" and name != HOTSPOT_NAME:
                    saved_networks.append(name)
        return saved_networks
    except Exception as e:
        logger.error("Error getting saved WiFi connections: %s", e)
        return []


def try_connect_saved_network(timeout: int = 15) -> bool:
    """
    Try to connect to a saved WiFi network.
    Returns True if successfully connected, False otherwise.
    """
    saved_networks = get_saved_wifi_connections()
    
    if not saved_networks:
        logger.info("No saved WiFi networks found")
        return False
    
    logger.info("Found saved WiFi networks: %s", saved_networks)
    
    for network in saved_networks:
        logger.info("Attempting to connect to saved network: %s", network)
        result = subprocess.run(
            ["nmcli", "connection", "up", network],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Successfully initiated connection to: %s", network)
            # Wait for connection to be fully established
            start_time = time.time()
            while time.time() - start_time < timeout:
                if is_client_wifi_connected():
                    logger.info("Connected to saved network: %s", network)
                    return True
                time.sleep(1)
        else:
            logger.warning("Failed to connect to %s: %s", network, result.stderr.strip())
    
    return False


def wait_for_wlan_state(target_state: str, timeout: int = 10) -> bool:
    """Wait until wlan0 reaches the desired state (e.g., disconnected) or timeout"""
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[0] == "wlan0":
                if parts[1] == target_state:
                    return True
        time.sleep(0.5)
    return False


def wifi_watchdog(poll_interval: int = 5):
    """
    Continuously monitors WiFi connectivity.
    - If wlan0 is disconnected → start AP mode
    - If wlan0 reconnects → stop AP mode
    """
    global watchdog_enabled
    logger.info("WiFi watchdog started")
    last_switch_time = 0
    min_interval = 5  # seconds to avoid rapid flapping

    while True:
        try:

            if not watchdog_enabled:
                time.sleep(poll_interval)
                continue

            ap_active = is_ap_active()
            wlan_connected = is_client_wifi_connected()
            now = time.time()

            if not wlan_connected and not ap_active and now - last_switch_time > min_interval:
                logger.warning("WiFi disconnected — switching to AP mode")
                start_ap_mode(wait_until_up=True)
                last_switch_time = now

            elif wlan_connected and ap_active and now - last_switch_time > min_interval:
                logger.info("WiFi reconnected — disabling AP mode")
                stop_ap_mode()
                wait_for_wlan_state("disconnected")
                last_switch_time = now

        except Exception:
            logger.exception("WiFi watchdog error")

        time.sleep(poll_interval)


def start_ap_mode(wait_until_up: bool = False):
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

    if wait_until_up:
        logger.info("Waiting for AP to be fully active...")
        wait_for_wlan_state("connected", timeout=10)


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
    wait_for_wlan_state("disconnected")


def connect_to_wifi(ssid: str, password: str) -> bool:
    print(f"Connecting to WiFi: {ssid}")

    subprocess.run(
        ["nmcli", "device", "wifi", "rescan", "ifname", "wlan0"],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )

    time.sleep(3)

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
    global watchdog_enabled
    logger.info("Background task started: switch_wifi")
    print("Background task: switching WiFi...")

    watchdog_enabled = False

    stop_ap_mode()
    wait_for_wlan_state("disconnected", timeout=10)

    current_ssid = get_current_ssid()
    if current_ssid == ssid:
        logger.info("Device Already Connected to this Wifi")
        print("Device Already Connected")
        send_device_config(pairing_token)

    # First attempt
    success = connect_to_wifi(ssid, password)
    if not success:
        logger.warning("First WiFi connection attempt failed — retrying once...")
        time.sleep(3)
        success = connect_to_wifi(ssid, password)

    if success:
        logger.info("Connected to WiFi: %s", ssid)
        print(f"Connected to {ssid}")
        send_device_config(pairing_token)
    else:
        logger.error("Failed to connect to WiFi after retry: %s", ssid)
        print(f"Failed to connect to {ssid} after retry")

    watchdog_enabled = True


@app.post("/provision")
async def provision_wifi(request: Request):
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
            "message": "SSID, password, and pairing token are required"
        }

    global watchdog_enabled
    watchdog_enabled = False  # temporarily stop watchdog

    stop_ap_mode()
    wait_for_wlan_state("disconnected", timeout=10)

    # Try connecting to Wi-Fi
    success = connect_to_wifi(ssid, password)
    if not success:
        logger.warning("First Wi-Fi connection attempt failed — retrying once...")
        time.sleep(3)
        success = connect_to_wifi(ssid, password)

    if not success:
        watchdog_enabled = True
        return {"status": "error", "message": f"Failed to connect to Wi-Fi {ssid}"}

    # Connected — send config to backend and get response
    try:
        with open(config_path, "r") as f:
            device_info = json.load(f)

        payload = {
            "pairing_token": pairing_token,
            "serial_number": device_info["serial_number"],
            "machine_name": device_info.get("machine_name"),
            "model": device_info.get("model"),
            "firmware_version": device_info.get("firmware_version")
        }

        response = requests.post(BACKEND_API, json=payload, timeout=10)
        backend_status = "ok" if response.status_code == 200 else "error"
        backend_message = response.text

    except Exception as e:
        backend_status = "error"
        backend_message = str(e)

    watchdog_enabled = True

    # Forward backend response to frontend
    return {
        "status": backend_status,
        "message": backend_message,
        "device": device_info
    }


if __name__ == "__main__":
    logger.info("Provision service starting")

    # Wait until NetworkManager is ready
    for _ in range(10):
        try:
            if subprocess.run(["nmcli", "-t", "-f", "DEVICE", "device"], capture_output=True, text=True).returncode == 0:
                break
        except Exception:
            time.sleep(1)

    # Check if already connected to WiFi
    if is_client_wifi_connected():
        logger.info("Wi-Fi already connected. Skipping hotspot startup.")
    else:
        # Not connected - check if there are saved networks and try to connect
        logger.info("Not currently connected to WiFi. Checking for saved networks...")
        saved_networks = get_saved_wifi_connections()
        
        if saved_networks:
            logger.info("Found saved networks: %s. Attempting to connect...", saved_networks)
            if try_connect_saved_network(timeout=20):
                logger.info("Successfully connected to a saved network. Skipping hotspot startup.")
            else:
                logger.info("Could not connect to any saved network — starting AP mode")
                start_ap_mode(wait_until_up=True)
        else:
            logger.info("No saved Wi-Fi networks found — starting AP mode")
            start_ap_mode(wait_until_up=True)

    threading.Thread(target=wifi_watchdog, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=5000)

