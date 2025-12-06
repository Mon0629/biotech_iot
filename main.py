from scripts.mqtt_client import init_mqtt

def main():
    """Start main.py"""
    init_mqtt()

if __name__ == "__main__":
    # Check if Pi is already on a WiFi network
    main()
