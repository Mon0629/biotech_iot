# scripts/publisher.py
from .mqtt_client import init_mqtt, publish
from data.data_collector import read_batches
from config import config

def main():
    client = init_mqtt()
    print("[MQTT] Initialized")

    print("Listening for batches...")

    for batch_data in read_batches():
        print("[BATCH RECEIVED]")
        print(batch_data)

        # Format: serial number on first line, sensor data on second line
        message = f"device_serial_number:{config.SERIAL_NUMBER}\n{batch_data}"
        
        publish(f"biotech/{config.SERIAL_NUMBER}/sensor_data", message)
        print("[MQTT] Batch published\n")

if __name__ == "__main__":
    main()

