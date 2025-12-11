from mqtt.subscriber import main as subscriber_main
import time


def main():
    subscriber_main()
    print("MQTT client initialized, waiting for messages...")

    try:
        while True:
            time.sleep(1)  # keep script alive
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()

