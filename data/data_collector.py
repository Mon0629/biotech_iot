import serial
from config import config

def read_batches():
    ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)

    batch = {
        "dirty_water": None,
        "clean_water": None,
        "hydroponics_water": None
    }

    while True:
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

def main():
    print("Starting data collector...")
    read_batches()

if __name__ == "__main__":
    main()
