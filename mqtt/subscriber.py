import os
from .mqtt_client import init_mqtt, subscribe
#from controls.controls import open_valve, close_valve, open_pump, close_pump

def valve_callback(message, valve_number):
    print(f"[MQTT] valve/{valve_number} received: {message}")
    if message.upper() == "OPEN":
       pass
#        open_valve(valve_number)
    elif message.upper() == "CLOSE":
       pass
#        close_valve(valve_number)

def pump_callback(message, pump_number):
    print(f"[MQTT] pump/{pump_number} received: {message}")
    if message.upper() == "OPEN":
        pass
#        open_pump(pump_number)
    elif message.upper() == "CLOSE":
        pass
#        close_pump(pump_number)

def main():
    client = init_mqtt()

    subscribe("valve/1", lambda msg:valve_callback(msg, 1))
    subscribe("valve/2", lambda msg:valve_callback(msg, 2))
    subscribe("pump/1", lambda msg:pump_callback(msg, 1))
    subscribe("pump/2", lambda msg:pump_callback(msg, 2))
    
    print("Subscriber Running...waiting for message")

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting")

if __name__ == "__main__":
    main()
