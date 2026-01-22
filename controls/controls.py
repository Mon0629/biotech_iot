import serial
import time
from config import config

# Try to open serial port, but don't crash if it's not connected
try:
    ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
    print("✓ Serial port connected")
except (serial.SerialException, AttributeError, TypeError) as e:
    print(f"⚠ No serial port connected: {e}")
    ser = None

def control_device(device_type, number, state):
    """
    device_type = 'V' for valve or 'P'
    number: Valve 1 or valve 2  
    """
    if ser is None:
        print(f"⚠ Cannot control {device_type}{number}: No serial connection")
        return
    
    try:
        cmd = f"{device_type}{number}={'1' if state else '0'}\n"
        ser.write(cmd.encode())
        time.sleep(0.2)
        response = ser.readline().decode().strip()
        print(f"[Arduino] {response}")
    except Exception as e:
        print(f"✗ Serial error: {e}")

def open_valve(number):
    control_device('V', number, True)

def close_valve(number):
    control_device('V', number, False)

def open_pump(number):
    control_device('P', number, True)

def close_pump(number):
    control_device('P', number, False)
