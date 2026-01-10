from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import time
import threading
import logging
import os
import uvicorn

# ---------------- CONFIG ----------------

WIFI_INTERFACE = "wlan0"
AP_CONNECTION_NAME = "AP-setup"
FACTORY_RESET_FLAG = "/boot/factory_reset"
CHECK_INTERVAL = 10  # seconds

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
        if line.endswith(":wifi") and not line.startswith(AP_CONNECTION_NAME):
            return True
    return False

def start_ap():
    logging.info("Starting AP mode")
    subprocess.run(
        ["nmcli", "connection", "up", AP_CONNECTION_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def stop_ap():
    logging.info("Stopping AP mode")
    subprocess.run(
        ["nmcli", "connection", "down", AP_CONNECTION_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def clear_factory_reset_flag():
    if os.path.exists(FACTORY_RESET_FLAG):
        os.remove(FACTORY_RESET_FLAG)
        logging.info("Factory reset flag cleared")

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
    If Wi-Fi drops at runtime, AP is enabled.
    """
    logging.info("Wi-Fi monitor thread started")

    while True:
        try:
            if not is_wifi_connected():
                start_ap()
        except Exception as e:
            logging.error(f"Wi-Fi monitor error: {e}")

        time.sleep(CHECK_INTERVAL)

# ---------------- API ----------------

@app.post("/provision")
def provision_wifi(creds: WifiCredentials):
    """
    Receives Wi-Fi credentials, connects, disables AP.
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

