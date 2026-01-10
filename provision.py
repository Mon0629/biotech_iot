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
BACKEND_URL = "https://your-backend-domain.com/api/device-config"  # Replace with your Laravel endpoint

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

def send_device_config():
    """
    Sends device_config.json to backend after Wi-Fi is connected.
    """
    config_path = os.path.join(os.path.dirname(__file__), "config", "device_config.json")
    if not os.path.exists(config_path):
        logging.error("device_config.json not found")
        return

    with open(config_path, "r") as f:
        config_data = json.load(f)

    try:
        logging.info(f"Sending device config to backend at {BACKEND_URL}")
        response = requests.post(BACKEND_URL, json=config_data, timeout=10)
        if response.status_code == 200:
            logging.info("Device config sent successfully")
        else:
            logging.error(f"Backend returned status {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Failed to send device config: {e}")

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
def provision_wifi(creds: WifiCredentials):
    """
    Receives Wi-Fi credentials, connects, disables AP,
    and sends device config to backend.
    """

    if not creds.ssid or not creds.password:
        return {"error": "SSID and password required"}

    try:
        logging.info(f"Provisioning Wi-Fi: {creds.ssid}")

        subprocess.run(
            [
                "nmcli",
                "dev",
                "wifi",
                "connect",
                creds.ssid,
                "password",
                creds.password,
                "ifname",
                WIFI_INTERFACE
            ],
            check=True
        )

        time.sleep(5)

        if is_wifi_connected():
            stop_ap()
            clear_factory_reset_flag()
            send_device_config()  # <-- send device config after Wi-Fi connects
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
