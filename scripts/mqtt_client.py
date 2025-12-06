# scripts/mqtt_client.py
import paho.mqtt.client as mqtt
from threading import Thread

MQTT_BROKER = "960858f8c9cd49548edc44f8b9fac4e9.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "Biotech"
MQTT_PASS = "Momorevillame24"

client = None
_callbacks = {}  # topic -> callback function


def _on_connect(c, userdata, flags, rc):
    print("MQTT connected with code", rc)
    # Subscribe to all registered topics
    for topic in _callbacks.keys():
        c.subscribe(topic)
        print(f"Subscribed to {topic}")


def _on_message(c, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode().strip()
    print(f"[MQTT] {topic}: {message}")
    if topic in _callbacks:
        _callbacks[topic](message)  # Call the registered callback


def init_mqtt():
    """Initialize and run the MQTT client (singleton)."""
    global client
    if client is not None:
        return client

    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()

    client.on_connect = _on_connect
    client.on_message = _on_message

    client.connect(MQTT_BROKER, MQTT_PORT)
    
    # Run loop in background thread
    t = Thread(target=client.loop_forever, daemon=True)
    t.start()
    
    return client


def subscribe(topic, callback):
    """
    Register a topic and a callback function.
    Whenever a message is published to this topic, the callback is called automatically.
    """
    _callbacks[topic] = callback
    if client is not None:
        client.subscribe(topic)
