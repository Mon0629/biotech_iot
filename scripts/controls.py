import serial
import time

ser = serial.Serial('/dev/arduino', 9600, timeout=1)  # adjust port if wrong

def open_valve():
    ser.write(b'ON\n')
    time.sleep(0.1)
    print(ser.readline().decode().strip())

def close_valve():
    ser.write(b'OFF\n')
    time.sleep(0.1)
    print(ser.readline().decode().strip())

def open_pump():
    ser.write(b'ON\n')
    time.sleep(0.1)
    print(ser.readline().decode().strip())

def close_pump():
    ser.write(b'OFF\n')
    time.sleep(0.1)
    print(ser.readline().decode().strip())
