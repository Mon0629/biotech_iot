from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import time
import threading
import logging
import os
import uvicorn
import json
import requests

# ---------------- CONFIG ----------------

WIFI_INTERFACE = "wlan0"
FACTORY_RESET_FLAG = "/boot/factory_reset"
CHECK_INTERVAL = 10  # seconds
BACKEND_URL = "https://auntlike-karrie-caboshed.ngrok-free.dev/api/v1/provision"  # Replace with your Laravel endpoint

# ---------------- APP ----------------

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------------- MODELS ----------------

class WifiCredentials(BaseModel):
    ssid: str
    password: str
    pairing_token: str

# ---------------- HELPERS ----------------

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def is_wifi_connected() -> bool:
    result = run(["nmcli", "-t", "-f", "DEVICE,STATE", "dev"])
    return any(
        line.startswith(f"{WIFI_INTERFACE}:connected")
        for line in result.stdout.splitlines()
    )

def has_saved_wifi() -> bool:
    """
    Returns True if at least one non-AP Wi-Fi profile exists.
    """
    result = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    for line in result.stdout.splitlines():
        if line.endswith(":wifi"):
            return True
    return False

def start_ap():
    logging.info("Starting AP mode (hostapd)")
    subprocess.run(["sudo", "systemctl", "start", "hostapd"], check=False)

def stop_ap():
    logging.info("Stopping AP mode (hostapd)")
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"], check=False)

def clear_factory_reset_flag():
    if os.path.exists(FACTORY_RESET_FLAG):
        os.remove(FACTORY_RESET_FLAG)
        logging.info("Factory reset flag cleared")

def send_device_config(pairing_token: str):
    """
    Send device_config.json to backend after successful Wi-Fi provisioning
    """
    config_path = os.path.join(os.path.dirname(__file__), "config", "device_config.json")
    if not os.path.exists(config_path):
        logging.error("Device config not found, cannot send to backend")
        return

    with open(config_path, "r") as f:
        device_info = json.load(f)

    payload = {
        "pairing_token": pairing_token,
        "serial_number": device_info["serial_number"],
        "machine_name": device_info.get("machine_name"),
        "model": device_info.get("model"),
        "firmware_version": device_info.get("firmware_version"),
    }

    try:
        response = requests.post(BACKEND_URL, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info("Device info successfully sent to backend")
        else:
            logging.error(f"Failed to send device info: {response.status_code} {response.text}")
    except Exception as e:
        logging.error(f"Error sending device info: {e}")

# ---------------- STARTUP LOGIC ----------------

def startup_logic():
    """
    Decide whether AP should start at boot.
    """
    if os.path.exists(FACTORY_RESET_FLAG):
        logging.info("Factory reset flag detected → AP enabled")
        start_ap()
        return

    if not has_saved_wifi():
        logging.info("No saved Wi-Fi profiles → AP enabled")
        start_ap()
        return

    logging.info("Saved Wi-Fi exists → AP not started")

# ---------------- MONITOR THREAD ----------------

def wifi_monitor():
    """
    Monitors Wi-Fi. If Wi-Fi drops at runtime, starts AP automatically.
    Stops AP when Wi-Fi is restored.
    """
    logging.info("Wi-Fi monitor thread started")

    ap_running = False  # track AP state

    while True:
        try:
            wifi_connected = is_wifi_connected()

            if not wifi_connected and not ap_running:
                logging.info("Wi-Fi down → starting AP")
                start_ap()
                ap_running = True

            elif wifi_connected and ap_running:
                logging.info("Wi-Fi restored → stopping AP")
                stop_ap()
                ap_running = False

        except Exception as e:
            logging.error(f"Wi-Fi monitor error: {e}")

        time.sleep(CHECK_INTERVAL)

# ---------------- API ----------------

@app.post("/provision")
def provision_wifi(req: WifiCredentials):
    """
    Receives Wi-Fi credentials + pairing token, connects, disables AP, 
    and sends device info to backend
    """

    if not req.ssid or not req.password or not req.pairing_token:
        return {"error": "SSID, password, and pairing_token are required"}

    try:
        logging.info(f"Provisioning Wi-Fi: {req.ssid}")

        subprocess.run(
            [
                "nmcli",
                "dev",
                "wifi",
                "connect",
                req.ssid,
                "password",
                req.password,
                "ifname",
                WIFI_INTERFACE
            ],
            check=True
        )

        time.sleep(5)

        if is_wifi_connected():
            stop_ap()
            clear_factory_reset_flag()

            # Send device info to backend asynchronously
            threading.Thread(
                target=send_device_config,
                args=(req.pairing_token,),
                daemon=True
            ).start()

            return {"status": "connected"}

        return {"error": "Wi-Fi connection failed"}

    except subprocess.CalledProcessError:
        return {"error": "Invalid credentials or connection error"}


# ---------------- MAIN ----------------

if __name__ == "__main__":
    startup_logic()

    threading.Thread(
        target=wifi_monitor,
        daemon=True
    ).start()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
