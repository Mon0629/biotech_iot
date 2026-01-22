import threading
from mqtt.subscriber import main as subscriber_main
from mqtt.publisher import main as publisher_main

def main():
    print("Starting IoT device services...")
    
    # Run MQTT subscriber in a separate thread (listens for commands)
    mqtt_thread = threading.Thread(target=subscriber_main, daemon=True, name="MQTT-Subscriber")
    mqtt_thread.start()
    print("✓ MQTT subscriber thread started (listening for commands)")
    
    # Run publisher in main thread (collects & publishes sensor data)
    print("✓ Starting data publisher (reading serial + publishing to MQTT)...")
    try:
        publisher_main()  # This blocks and runs forever
    except KeyboardInterrupt:
        print("\nShutting down IoT device...")
    except Exception as e:
        print(f"Error in publisher: {e}")

if __name__ == "__main__":
    main()

