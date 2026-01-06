from dotenv import load_dotenv
import os

load_dotenv()


MQTT_BROKER=os.getenv("MQTT_BROKER")
MQTT_PORT=int(os.getenv("MQTT_PORT", 8883))
MQTT_USER=os.getenv("MQTT_USER")
MQTT_PASSWORD=os.getenv("MQTT_PASSWORD")

SERIAL_BAUD=int(os.getenv("SERIAL_BAUD", 9600))
SERIAL_PORT=os.getenv("SERIAL_PORT")

BACKEND_API_URL=os.getenv("BACKEND_API_URL")