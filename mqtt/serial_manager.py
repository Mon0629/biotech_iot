"""
Serial Manager - Single shared serial connection for Arduino communication
Handles both reading sensor data batches and sending control commands
"""
import serial
import time
import threading
from config import config


class SerialManager:
    """Singleton serial manager to prevent multiple port access conflicts"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.ser = None
        self.connected = False
        self._write_lock = threading.Lock()
        self._initialized = True
        self._connect()
    
    def _connect(self):
        """Establish serial connection with retry logic"""
        try:
            self.ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
            self.connected = True
            print("✓ Serial port connected (SerialManager)")
        except (serial.SerialException, AttributeError, TypeError) as e:
            print(f"⚠ No serial port connected: {e}")
            self.ser = None
            self.connected = False
    
    def reconnect(self):
        """Attempt to reconnect to serial port"""
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        
        print("Attempting to reconnect...")
        time.sleep(2)
        
        try:
            self.ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
            self.connected = True
            print("✓ Serial port reconnected!")
            return True
        except Exception as e:
            print(f"Reconnection failed: {e}")
            self.connected = False
            return False
    
    def wait_for_connection(self):
        """Block until serial connection is established"""
        if self.connected:
            return
        
        print("Waiting for serial connection...")
        while not self.connected:
            time.sleep(5)
            print("Still waiting for serial port... (program continues running)")
            if self.reconnect():
                break
    
    def write_command(self, command):
        """
        Send a command to Arduino with thread safety
        Commands should be formatted as: "P1=1\n" or "V2=0\n"
        Returns: response from Arduino or None if failed
        """
        if not self.connected or self.ser is None:
            print(f"⚠ Cannot send command: No serial connection")
            return None
        
        with self._write_lock:
            try:
                # Ensure command ends with newline
                if not command.endswith('\n'):
                    command += '\n'
                
                self.ser.write(command.encode())
                time.sleep(0.2)  # Give Arduino time to process
                
                # Read response (non-blocking)
                response = self.ser.readline().decode().strip()
                return response
            except serial.SerialException as e:
                print(f"✗ Serial write error: {e}")
                self.connected = False
                return None
            except Exception as e:
                print(f"✗ Unexpected error during write: {e}")
                return None
    
    def read_line(self):
        """
        Read a single line from Arduino
        Returns: decoded string or None if failed
        """
        if not self.connected or self.ser is None:
            return None
        
        try:
            raw = self.ser.readline().decode().strip()
            return raw if raw else None
        except serial.SerialException as e:
            print(f"Serial connection lost: {e}")
            self.connected = False
            return None
        except Exception as e:
            print(f"Read error: {e}")
            return None
    
    def read_batches(self):
        """
        Generator that yields complete sensor data batches
        Handles reconnection automatically
        """
        self.wait_for_connection()
        
        batch = {
            "dirty_water": None,
            "clean_water": None,
            "hydroponics_water": None
        }
        
        while True:
            raw = self.read_line()
            
            # Handle disconnection
            if raw is None and not self.connected:
                self.reconnect()
                continue
            
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
                
                # Reset for next cycle
                batch = {
                    "dirty_water": None,
                    "clean_water": None,
                    "hydroponics_water": None
                }
    
    def close(self):
        """Close serial connection"""
        if self.ser:
            try:
                self.ser.close()
                print("Serial connection closed")
            except Exception:
                pass
            finally:
                self.connected = False
                self.ser = None


# Create singleton instance
serial_manager = SerialManager()
