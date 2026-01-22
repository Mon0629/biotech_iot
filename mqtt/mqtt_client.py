# scripts/mqtt_client.py
import paho.mqtt.client as mqtt
from config import config

client = None
_callbacks = set()  # set of callback functions to prevent duplicates


def _on_connect(c, userdata, flags, rc):
    if rc == 0:
        print("✓ MQTT connected successfully")
        # Subscribe to all registered topics with QoS 1 for guaranteed delivery
        for topic in _subscriptions:
            c.subscribe(topic, qos=1)
            print(f"✓ Subscribed to {topic} (QoS 1)")
    else:
        print(f"✗ MQTT connection failed with code {rc}")


def _on_disconnect(c, userdata, rc):
    if rc != 0:
        print(f"⚠ MQTT unexpected disconnect (code {rc}). Reconnecting...")
    else:
        print("MQTT disconnected cleanly")


def _on_message(c, userdata, msg):
    import time
    receive_time = time.time()
    
    topic = msg.topic
    message = msg.payload.decode().strip()
    print(f"[MQTT {time.strftime('%H:%M:%S')}] {topic}: {message}")

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

    # Validate MQTT configuration before attempting connection
    if not config.MQTT_BROKER or config.MQTT_BROKER == "None":
        print("⚠ MQTT broker not configured. Check your .env file.")
        print("⏳ MQTT client not initialized - program will continue without MQTT")
        return None
    
    if not config.MQTT_USER or not config.MQTT_PASSWORD:
        print("⚠ MQTT credentials not configured. Check your .env file.")
        print("⏳ MQTT client not initialized - program will continue without MQTT")
        return None

    try:
        # Create client with clean session for faster reconnects
        client = mqtt.Client(clean_session=True)
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
        client.tls_set()

        client.on_connect = _on_connect
        client.on_message = _on_message
        client.on_disconnect = _on_disconnect
        
        # Reduce keepalive for faster detection of connection issues
        # Default is 60s, reducing to 20s for faster responsiveness
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=20)
        
        # Start network loop immediately to process callbacks
        client.loop_start()
        print("MQTT client started and connecting...")
        return client
    except Exception as e:
        print(f"⚠ Failed to initialize MQTT client: {e}")
        print("⏳ Program will continue without MQTT")
        return None


def subscribe(topic, callback):
    """Subscribe to a topic with wildcard support and QoS 1"""
    global _subscriptions
    if client is None:
        print(f"⚠ MQTT not available - cannot subscribe to {topic}")
        return
    
    if topic not in _subscriptions:
        _subscriptions.add(topic)
        if client.is_connected():
            client.subscribe(topic, qos=1)
            print(f"✓ Subscribed to {topic} (QoS 1)")
        else:
            print(f"⏳ Will subscribe to {topic} on connection")
    
    # Add callback to set (prevents duplicates automatically)
    _callbacks.add(callback)


def publish(topic, message, QoS=0, retain=False):
    if client is None:
        print(f"⚠ MQTT not available - skipping publish to {topic}")
        return
    client.publish(topic, payload=message, qos=QoS, retain=retain)
    print(f"[MQTT] Message published to {topic}: {message}")

