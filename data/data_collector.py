from mqtt.serial_manager import serial_manager

def read_batches():
    """
    Generator that yields complete sensor data batches from Arduino
    Uses shared serial manager to prevent port conflicts
    """
    print("Listening for serial data batches...")
    
    # Delegate all batch reading to the serial manager
    for batch in serial_manager.read_batches():
        yield batch

def main():
    print("Starting data collector...")
    read_batches()

if __name__ == "__main__":
    main()
