import os
import time
from mqtt.mqtt_client import init_mqtt, publish

def publish_data():
    
    publish("valve/1", "OPEN")
    print("[MQTT] Message Published")

def main():
    client = init_mqtt()
    print("MQTT Initialized")
    
    publish_data()


if __name__ == "__main__":
    main()
