import serial
import time
from config import config

ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)  # adjust port if wrong

def control_device(device_type, number, state):
    """
    device_type = 'V' for valve or 'P'
    number: Valve 1 or valve 2  
    """
    cmd = f"{device_type}{number}={'1' if state else '0'}\n"
    ser.write(cmd.encode())
    time.sleep(0.2)
    response = ser.readline().decode().strip()
    print(f"[Arduino] {response}")

def open_valve(number):
    control_device('V', number, True)

def close_valve(number):
    control_device('V', number, False)

def open_pump(number):
    control_device('P', number, True)

def close_pump(number):
    control_device('P', number, False)
