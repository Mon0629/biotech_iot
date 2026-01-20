# scripts/mqtt_client.py
import paho.mqtt.client as mqtt
from config import config

client = None
_callbacks = []  # list of callback functions


def _on_connect(c, userdata, flags, rc):
    print("MQTT connected with code", rc)
    # Subscribe to all registered topics
    for topic in _subscriptions:
        c.subscribe(topic)
        print(f"Subscribed to {topic}")


def _on_message(c, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode().strip()
    print(f"[MQTT] {topic}: {message}")

    # Call all registered callbacks, passing actual topic
    for callback in _callbacks:
        try:
            callback(message, topic)
        except Exception as e:
            print(f"[MQTT] Callback error: {e}")


_subscriptions = set()


def init_mqtt():
    """Initialize MQTT client singleton"""
    global client
    if client is not None:
        return client

    client = mqtt.Client()
    client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
    client.tls_set()

    client.on_connect = _on_connect
    client.on_message = _on_message

    client.connect(config.MQTT_BROKER, config.MQTT_PORT)
    print("MQTT client started")
    return client


def subscribe(topic, callback):
    """Subscribe to a topic with wildcard support"""
    global _subscriptions
    if topic not in _subscriptions:
        _subscriptions.add(topic)
        if client is not None:
            client.subscribe(topic)
            print(f"Subscribed to {topic}")
    _callbacks.append(callback)


def publish(topic, message, QoS=0, retain=False):
    if client is None:
        raise RuntimeError("MQTT client not initialized")
    client.publish(topic, payload=message, qos=QoS, retain=retain)
    print(f"[MQTT] Message published to {topic}: {message}")

