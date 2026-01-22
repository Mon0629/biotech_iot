from .mqtt_client import init_mqtt, subscribe
from controls.controls import open_valve, close_valve, open_pump, close_pump
from config import config

SERIAL_NUMBER = config.SERIAL_NUMBER  # loaded from device_config.json


def valve_callback(message, valve_number):
    import time
    print(f"[{time.strftime('%H:%M:%S')}] valve/{valve_number} received: {message}")
    try:
        if message.upper() == "OPEN":
            open_valve(valve_number)
            print(f"✓ Valve {valve_number} opened")
        elif message.upper() == "CLOSE":
            close_valve(valve_number)
            print(f"✓ Valve {valve_number} closed")
        else:
            print(f"⚠ Unknown valve command: {message}")
    except Exception as e:
        print(f"✗ Error controlling valve {valve_number}: {e}")


def pump_callback(message, pump_number):
    import time
    print(f"[{time.strftime('%H:%M:%S')}] pump/{pump_number} received: {message}")
    try:
        if message.upper() == "OPEN":
            open_pump(pump_number)
            print(f"✓ Pump {pump_number} opened")
        elif message.upper() == "CLOSE":
            close_pump(pump_number)
            print(f"✓ Pump {pump_number} closed")
        else:
            print(f"⚠ Unknown pump command: {message}")
    except Exception as e:
        print(f"✗ Error controlling pump {pump_number}: {e}")


def message_callback(message, topic):
    """
    Parses topic like hydroponics/<serial>/pump/1 or hydroponics/<serial>/valve/2
    Calls correct callback dynamically
    """
    import time
    
    parts = topic.split("/")
    if len(parts) != 4:
        print(f"⚠ Malformed topic: {topic} (expected format: prefix/serial/type/number)")
        return

    _, serial, device_type, number = parts

    # Only process messages for this device
    if serial != SERIAL_NUMBER:
        print(f"⏩ Ignoring message for {serial}, this device is {SERIAL_NUMBER}")
        return

    try:
        device_number = int(number)
    except ValueError:
        print(f"⚠ Invalid device number in topic: {topic}")
        return

    print(f"[{time.strftime('%H:%M:%S')}] Processing {device_type}/{device_number}: {message}")
    
    if device_type.lower() == "pump":
        pump_callback(message, device_number)
    elif device_type.lower() == "valve":
        valve_callback(message, device_number)
    else:
        print(f"⚠ Unknown device type '{device_type}' in topic: {topic}")


def main():
    import time
    
    client = init_mqtt()

    # Give the client a moment to establish connection
    time.sleep(1)

    # Subscribe to all pumps and valves for this device
    subscribe(f"mfc/{SERIAL_NUMBER}/pump/+", message_callback)
    subscribe(f"hydroponics/{SERIAL_NUMBER}/pump/+", message_callback)
    subscribe(f"reservoir_fallback/{SERIAL_NUMBER}/pump/+", message_callback)  # Fixed: added missing /
    subscribe(f"mfc/{SERIAL_NUMBER}/valve/+", message_callback)
    subscribe(f"mfc_fallback/{SERIAL_NUMBER}/valve/+", message_callback)

    print(f"\n{'='*60}")
    print(f"✓ Subscriber running for device: {SERIAL_NUMBER}")
    print(f"✓ Listening for messages with QoS 1 (guaranteed delivery)")
    print(f"{'='*60}\n")
    
    # Keep the main thread alive (loop_start already handles message processing)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down subscriber...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

