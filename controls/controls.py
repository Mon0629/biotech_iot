from mqtt.serial_manager import serial_manager

def control_device(device_type, number, state):
    """
    device_type = 'V' for valve or 'P'
    number: Valve 1 or valve 2  
    """
    if not serial_manager.connected:
        print(f"Cannot control {device_type}{number}: No serial connection")
        return
    
    # Format command for Arduino: P1=1, V2=0, etc.
    cmd = f"{device_type}{number}={'1' if state else '0'}"
    response = serial_manager.write_command(cmd)
    
    if response:
        print(f"[Arduino] {response}")

def open_valve(number):
    control_device('V', number, True)

def close_valve(number):
    control_device('V', number, False)

def open_pump(number):
    control_device('P', number, True)

def close_pump(number):
    control_device('P', number, False)
