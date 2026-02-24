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
last_provision_result_path = os.path.join(os.path.dirname(__file__), 'config', 'last_provision_result.json')
app = FastAPI()

watchdog_enabled = True

HOTSPOT_NAME = "BIOTECH"
HOTSPOT_PASSWORD = "momorevillame24"

# MQTT topic for remote WiFi change (payload: {"ssid": "...", "password": "..."})
MQTT_TOPIC_WIFI_SET = "biotech/device/wifi/set"

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


def scan_ssids_while_ap() -> set[str] | None:
    """
    Scan for visible SSIDs without leaving AP mode (uses iw with ap-force).
    Returns set of SSID strings, or None if scan failed (e.g. iw not available).
    """
    try:
        result = subprocess.run(
            ["iw", "dev", "wlan0", "scan", "ap-force"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning("iw scan ap-force failed: %s", result.stderr.strip() or result.stdout)
            return None
        ssids = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("SSID:"):
                name = line[5:].strip()
                if name:
                    ssids.add(name)
        return ssids
    except FileNotFoundError:
        logger.warning("iw not found; cannot scan while in AP mode")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("iw scan timed out")
        return None
    except Exception as e:
        logger.exception("Scan while AP failed: %s", e)
        return None


def save_last_provision_result(result: dict):
    """Persist last provision attempt for GET /provision/result after reconnect."""
    os.makedirs(os.path.dirname(last_provision_result_path), exist_ok=True)
    with open(last_provision_result_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Saved last provision result: %s", result)


def load_last_provision_result() -> dict | None:
    if not os.path.exists(last_provision_result_path):
        return None
    try:
        with open(last_provision_result_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


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

    payload =  {
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


def switch_wifi_only(ssid: str, password: str) -> bool:
    """
    Switch device to the given WiFi (no backend/provisioning).
    Use when in AP mode: drops AP, tries connect; on failure brings AP back.
    """
    global watchdog_enabled
    logger.info("switch_wifi_only: switching to %s", ssid)
    watchdog_enabled = False

    stop_ap_mode()
    wait_for_wlan_state("disconnected", timeout=10)

    current_ssid = get_current_ssid()
    if current_ssid == ssid:
        logger.info("Already connected to %s", ssid)
        watchdog_enabled = True
        return True

    success = connect_to_wifi(ssid, password)
    if not success:
        time.sleep(3)
        success = connect_to_wifi(ssid, password)

    if success:
        logger.info("Connected to WiFi: %s", ssid)
    else:
        logger.error("Failed to connect to WiFi: %s", ssid)
        start_ap_mode(wait_until_up=True)

    watchdog_enabled = True
    return success


def switch_wifi_from_mqtt(ssid: str, password: str) -> bool:
    """
    Switch to another WiFi when device is already on WiFi (e.g. MQTT-triggered).
    No backend call. No AP: on failure reconnects to a saved/known network.
    """
    logger.info("switch_wifi_from_mqtt: switching to %s", ssid)

    current_ssid = get_current_ssid()
    if current_ssid == ssid:
        logger.info("Already connected to %s", ssid)
        return True

    success = connect_to_wifi(ssid, password)
    if not success:
        time.sleep(3)
        success = connect_to_wifi(ssid, password)

    if success:
        logger.info("Connected to WiFi: %s", ssid)
        return True

    logger.warning("MQTT wifi switch failed; reconnecting to saved/known network")
    if try_connect_saved_network(timeout=20):
        logger.info("Reconnected to a saved network")
        return False
    logger.error("Could not reconnect to any saved network")
    return False


def switch_wifi(ssid: str, password: str, pairing_token: str):
    """Switch to WiFi and send device config to backend (provisioning flow)."""
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
        start_ap_mode(wait_until_up=True)

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

    # Scan while AP is still up; if SSID not in range, return failed without dropping AP
    visible = scan_ssids_while_ap()
    if visible is not None and ssid not in visible:
        logger.warning("SSID not found in scan: %s (visible: %s)", ssid, visible)
        return {"status": "failed", "message": "Wifi not found"}

    # SSID is there (or scan unavailable) — clear previous result, then drop AP and try connect
    if os.path.exists(last_provision_result_path):
        try:
            os.remove(last_provision_result_path)
        except OSError:
            pass

    global watchdog_enabled
    watchdog_enabled = False  # temporarily stop watchdog

    stop_ap_mode()
    wait_for_wlan_state("disconnected", timeout=10)

    success = connect_to_wifi(ssid, password)
    if not success:
        logger.warning("First Wi-Fi connection attempt failed — retrying once...")
        time.sleep(3)
        success = connect_to_wifi(ssid, password)

    if not success:
        save_last_provision_result({
            "status": "failed",
            "message": "Failed to connect. Wrong password or network unreachable.",
            "ssid": ssid,
        })
        start_ap_mode(wait_until_up=True)
        watchdog_enabled = True
        # Client is disconnected; they can reconnect to hotspot and GET /provision/result
        return {"status": "failed", "message": f"Failed to connect to Wi-Fi {ssid}"}

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


def _on_mqtt_wifi_set(message: str, topic: str):
    """
    Handle MQTT payload to change WiFi when device is already on WiFi.
    Payload: JSON {"ssid": "...", "password": "..."}
    Only runs when connected to WiFi; on failure reconnects to saved/known network (no AP).
    """
    try:
        if not is_client_wifi_connected():
            logger.info("MQTT wifi/set: ignored (device not on WiFi)")
            return
        data = json.loads(message)
        ssid = data.get("ssid")
        password = data.get("password") or ""
        if not ssid:
            logger.warning("MQTT wifi/set: missing ssid in payload")
            return
        logger.info("MQTT wifi/set: switching to %s", ssid)
        # Run in thread so we don't block MQTT loop
        threading.Thread(target=switch_wifi_from_mqtt, args=(ssid, password), daemon=True).start()
    except json.JSONDecodeError as e:
        logger.warning("MQTT wifi/set: invalid JSON %s", e)
    except Exception as e:
        logger.exception("MQTT wifi/set: %s", e)


@app.get("/provision/result")
async def get_provision_result():
    """
    Result of the last provision attempt. After a failed connect (e.g. wrong password),
    the device brings the hotspot back; reconnect to BIOTECH and call this to get the error.
    """
    result = load_last_provision_result()
    if result is None:
        return {"status": "unknown", "message": "No previous provision attempt."}
    return result


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

    # MQTT subscriber for remote WiFi change (no backend call)
    try:
        from mqtt.mqtt_client import init_mqtt, subscribe as mqtt_subscribe
        if init_mqtt() is not None:
            mqtt_subscribe(MQTT_TOPIC_WIFI_SET, _on_mqtt_wifi_set)
            logger.info("Subscribed to MQTT topic: %s", MQTT_TOPIC_WIFI_SET)
    except Exception as e:
        logger.warning("MQTT wifi subscriber not started: %s", e)

    uvicorn.run(app, host="0.0.0.0", port=5000)

