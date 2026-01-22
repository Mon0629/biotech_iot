# scripts/publisher.py
from .mqtt_client import init_mqtt, publish
from data.data_collector import read_batches
from config import config
import time

def main():
    client = init_mqtt()
    
    # Give MQTT client time to establish connection
    time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✓ Publisher running for device: {config.SERIAL_NUMBER}")
    print(f"✓ Publishing sensor data with QoS 1 (guaranteed delivery)")
    print(f"{'='*60}\n")
    
    print("Listening for serial data batches...")

    try:
        for batch_data in read_batches():
            print(f"[{time.strftime('%H:%M:%S')}] Batch received from serial")
            
            # Format: serial number on first line, sensor data on second line
            message = f"device_serial_number:{config.SERIAL_NUMBER}\n{batch_data}"
            
            # Publish with QoS 1 for guaranteed delivery
            publish(f"biotech/{config.SERIAL_NUMBER}/sensor_data", message, QoS=1)
            print(f"[{time.strftime('%H:%M:%S')}] ✓ Batch published to MQTT\n")
    except KeyboardInterrupt:
        print("\nPublisher shutting down...")
    except Exception as e:
        print(f"Error in publisher: {e}")
        raise

if __name__ == "__main__":
    main()

