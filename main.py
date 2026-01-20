from mqtt.subscriber import main as subscriber_main
from data.data_collector import read_batches

def main():
    subscriber_main()
    print("MQTT client initialized, waiting for messages...")
    read_batches()
if __name__ == "__main__":
    main()

