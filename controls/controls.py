from mqtt.serial_manager import serial_manager

def control_device(device_type, number, state):
    """
    device_type = 'V' for valve or 'P'
    number: Valve 1 or valve 2  
    Returns True if command was sent to Arduino, False otherwise.
    """
    if not serial_manager.connected:
        print(f"⚠ Cannot control {device_type}{number}: No serial connection")
        return False
    
    # Format command for Arduino: P1=1, V2=0, etc.
    cmd = f"{device_type}{number}={'1' if state else '0'}"
    success = serial_manager.write_command(cmd)
    
    if not success:
        print(f"✗ Failed to send command {cmd}")
    return success

def open_valve(number):
    return control_device('V', number, True)

def close_valve(number):
    return control_device('V', number, False)

def open_pump(number):
    return control_device('P', number, True)

def close_pump(number):
    return control_device('P', number, False)
