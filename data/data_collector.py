import serial
import time
from config import config

def read_batches():
    # Try to connect to serial port
    try:
        ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
        print("Serial port connected for data collection")
    except (serial.SerialException, AttributeError, TypeError) as e:
        print(f"No serial port connected: {e}")
        print("Waiting for serial connection...")
        # Keep waiting instead of crashing
        while True:
            time.sleep(5)
            print("Still waiting for serial port... (program continues running)")
            try:
                ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
                print("✓ Serial port reconnected!")
                break
            except Exception:
                continue

    batch = {
        "dirty_water": None,
        "clean_water": None,
        "hydroponics_water": None
    }

    while True:
        try:
            raw = ser.readline().decode().strip()
            if not raw:
                continue

            try:
                parts = raw.split(",")
                stage = parts[0]

                # Store the raw line as-is
                if stage in batch:
                    batch[stage] = raw

            except Exception:
                continue

            # All 3 stages complete → yield as separate lines
            if all(batch.values()):
                combined = "\n".join([
                    batch["dirty_water"],
                    batch["clean_water"],
                    batch["hydroponics_water"]
                ])
                yield combined

                # reset for next cycle
                batch = {
                    "dirty_water": None,
                    "clean_water": None,
                    "hydroponics_water": None
                }
        except serial.SerialException as e:
            print(f"Serial connection lost: {e}")
            print("Attempting to reconnect...")
            time.sleep(2)
            try:
                ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
                print("✓ Serial port reconnected!")
            except Exception:
                continue

def main():
    print("Starting data collector...")
    read_batches()

if __name__ == "__main__":
    main()
