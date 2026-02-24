# scripts/publisher.py
from .mqtt_client import init_mqtt, publish
from data.data_collector import read_batches
from config import config
import time
import threading
import subprocess

HEARTBEAT_TOPIC = "biotech/{serial}/heartbeat"
WIFI_TOPIC = "biotech/{serial}/wifi"
HEARTBEAT_INTERVAL = 45  # seconds


def _heartbeat_loop(serial_number: str, stop_event: threading.Event):
    """Publish '1' (online) to heartbeat topic every HEARTBEAT_INTERVAL seconds."""
    topic = HEARTBEAT_TOPIC.format(serial=serial_number)
    while not stop_event.wait(timeout=HEARTBEAT_INTERVAL):
        publish(topic, "1", QoS=1)


def get_current_wifi_ssid() -> str | None:
    """
    Return the SSID wlan0 is currently connected to, or None if disconnected.
    Uses NetworkManager via nmcli (Linux target device).
    """
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "device", "status"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split(":")
            if len(parts) >= 3 and parts[0] == "wlan0":
                state, conn = parts[1], parts[2]
                if state == "connected":
                    return conn
        return None
    except Exception:
        return None


def main():
    client = init_mqtt()

    # Give MQTT client time to establish connection
    time.sleep(1)

    serial_number = config.SERIAL_NUMBER
    heartbeat_topic = HEARTBEAT_TOPIC.format(serial=serial_number)
    wifi_topic = WIFI_TOPIC.format(serial=serial_number)

    # Publish online and current WiFi once at startup
    publish(heartbeat_topic, "1", QoS=1)
    publish(wifi_topic, get_current_wifi_ssid() or "", QoS=1)

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
    print(f"✓ Publishing sensor data with QoS 1 (guaranteed delivery)")
    print(f"✓ Heartbeat every {HEARTBEAT_INTERVAL}s → {heartbeat_topic} (1=online, 0=offline)")
    print(f"✓ WiFi name every {HEARTBEAT_INTERVAL}s → {wifi_topic}")
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

