# scripts/mqtt_client.py
import paho.mqtt.client as mqtt
from threading import Thread
from config import config


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
    client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
    client.tls_set()

    client.on_connect = _on_connect
    client.on_message = _on_message

    client.connect(config.MQTT_BROKER, config.MQTT_PORT)
    
    # Run loop in background thread
    client.loop_start()
    print("clientstarted")
    
    return client


def subscribe(topic, callback):
    """
    Register a topic and a callback function.
    Whenever a message is published to this topic, the callback is called automatically.
    """
    _callbacks[topic] = callback
    if client is not None:
        client.subscribe(topic)

def publish(topic, message, QoS=0, retain=False):
    """
    params: topic, Message Payload(string), Quality of Service= (0,1,2) retained true or false
    """

    if client is None:
        raise RuntimeError("MQTTclient not initialized")
    client.publish(topic, payload=message, qos=QoS, retain=retain)
    print(f"[MQTT] Message published to {topic}: {message}")
