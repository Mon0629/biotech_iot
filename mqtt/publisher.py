# scripts/publisher.py
from .mqtt_client import init_mqtt, publish
from data.data_collector import read_batches
from config import config
import time
import threading
import subprocess

HEARTBEAT_TOPIC = "biotech/{serial}/heartbeat"
HEARTBEAT_INTERVAL = 45  # seconds
HOTSPOT_NAME = "BIOTECH"


def is_ap_active() -> bool:
    """True if the BIOTECH hotspot is active (device in AP mode, no internet)."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
            capture_output=True,
            text=True,
        )
        return any(
            line.startswith(HOTSPOT_NAME + ":")
            for line in result.stdout.splitlines()
        )
    except Exception:
        return False


def _heartbeat_loop(serial_number: str, stop_event: threading.Event):
    """Publish '1' (online) to heartbeat topic every 45 seconds when not in AP mode."""
    topic = HEARTBEAT_TOPIC.format(serial=serial_number)
    while not stop_event.wait(timeout=HEARTBEAT_INTERVAL):
        if not is_ap_active():
            publish(topic, "1", QoS=1)


def main():
    client = init_mqtt()

    # Give MQTT client time to establish connection
    time.sleep(1)

    serial_number = config.SERIAL_NUMBER
    heartbeat_topic = HEARTBEAT_TOPIC.format(serial=serial_number)

    stop_heartbeat = threading.Event()
    heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(serial_number, stop_heartbeat),
        daemon=True,
        name="Heartbeat",
    )
    heartbeat_thread.start()

    print(f"\n{'='*60}")
    print(f"✓ Publisher running for device: {serial_number}")
    print(f"✓ Heartbeat every {HEARTBEAT_INTERVAL}s → {heartbeat_topic}")
    print(f"✓ Publishing sensor data with QoS 1 (guaranteed delivery)")
    print(f"{'='*60}\n")

    print("Listening for serial data batches...")

    try:
        for batch_data in read_batches():
            print(f"[{time.strftime('%H:%M:%S')}] Batch received from serial")

            # Format: serial number on first line, sensor data on second line
            message = f"device_serial_number:{serial_number}\n{batch_data}"

            # Publish with QoS 1 for guaranteed delivery
            publish("hydronew/ai/classification", message, QoS=1)
            print(f"[{time.strftime('%H:%M:%S')}] ✓ Batch published to MQTT\n")
    except KeyboardInterrupt:
        print("\nPublisher shutting down...")
    except Exception as e:
        print(f"Error in publisher: {e}")
        raise
    finally:
        stop_heartbeat.set()
        publish(heartbeat_topic, "0", QoS=1)
        print("✓ Heartbeat published 0 (offline)")

if __name__ == "__main__":
    main()

