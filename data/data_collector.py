# scripts/serial_reader.py
import serial
import json
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

            values = {}
            for item in parts[1:]:
                key, value = item.split(":")
                values[key] = float(value)

            if stage in batch:
                batch[stage] = values

        except Exception:
            continue

        # All 3 stages complete → yield
        if all(batch.values()):
            full_json = json.dumps(batch, indent=2)
            yield full_json  # <-- send back to caller

            # reset for next cycle
            batch = {
                "dirty_water": None,
                "clean_water": None,
                "hydroponics_water": None
            }

