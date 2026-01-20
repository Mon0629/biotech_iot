from dotenv import load_dotenv
import os
import json

load_dotenv()


MQTT_BROKER=os.getenv("MQTT_BROKER")
MQTT_PORT=int(os.getenv("MQTT_PORT", 8883))
MQTT_USER=os.getenv("MQTT_USER")
MQTT_PASSWORD=os.getenv("MQTT_PASSWORD")

SERIAL_BAUD=int(os.getenv("SERIAL_BAUD", 9600))
SERIAL_PORT=os.getenv("SERIAL_PORT")

BACKEND_API_URL=os.getenv("BACKEND_API_URL")


# Load device info from JSON
DEVICE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "device_config.json")

try:
    with open(DEVICE_CONFIG_PATH, "r") as f:
        device_config = json.load(f)
except FileNotFoundError:
    raise RuntimeError(f"Device config not found at {DEVICE_CONFIG_PATH}")
except json.JSONDecodeError as e:
    raise RuntimeError(f"Invalid JSON in device config: {e}")

# Extract serial number and other device info
SERIAL_NUMBER = device_config.get("serial_number")
MACHINE_NAME = device_config.get("machine_name")
MODEL = device_config.get("model")
FIRMWARE_VERSION = device_config.get("firmware_version")
DESCRIPTION = device_config.get("description")

if not SERIAL_NUMBER:
    raise RuntimeError("Device serial number not found in device_config.json")
