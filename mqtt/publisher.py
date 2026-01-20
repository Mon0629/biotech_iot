# scripts/publisher.py
from .mqtt_client import init_mqtt, publish
from data.data_collector import read_batches
from comfig import config

def main():
    client = init_mqtt()
    print("[MQTT] Initialized")

    print("Listening for batches...")

    for batch_json in read_batches():
        print("[BATCH RECEIVED]")
        print(batch_json)

        publish(f"biotech/{config.SERIAL_NUMBER}/sensor_data", batch_json)
        print("[MQTT] Batch published\n")

if __name__ == "__main__":
    main()

