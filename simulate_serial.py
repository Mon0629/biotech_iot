#!/usr/bin/env python3
"""
Serial Data Simulator for Testing MQTT Publisher
Mimics Arduino sensor data output without requiring physical hardware
"""
import time
import random
from mqtt.mqtt_client import init_mqtt, publish
from config import config

def generate_sensor_data():
    """Generate realistic sensor data for all three water stages"""
    
    # Dirty water: higher TDS, turbidity, lower pH
    dirty_water = (
        f"dirty_water,"
        f"ph:{random.uniform(5, 9.0):.2f},"
        f"tds:{random.uniform(250, 350):.2f},"
        f"turbidity:{random.uniform(10, 15):.2f},"
        f"water_level:{random.uniform(50, 60):.2f}"
    )
    
    # Clean water: lower TDS, turbidity, neutral pH
    clean_water = (
        f"clean_water,"
        f"ph:{random.uniform(5.0, 9.0):.2f},"
        f"tds:{random.uniform(100, 150):.2f},"
        f"turbidity:{random.uniform(2, 5):.2f},"
        f"water_level:{random.uniform(75, 85):.2f}"
    )
    
    # Hydroponics water: high TDS (nutrients), slightly acidic pH
    hydroponics_water = (
        f"hydroponics_water,"
        f"ph:{random.uniform(6.0, 6.5):.2f},"
        f"tds:{random.uniform(800, 900):.2f},"
        f"humidity:{random.uniform(55, 65):.2f},"
        f"ec:{random.uniform(950, 1100):.2f}"
    )
    
    return dirty_water, clean_water, hydroponics_water


def main():
    # Initialize MQTT client
    client = init_mqtt()
    time.sleep(1)
    
    print(f"\n{'='*70}")
    print(f"  IoT Serial Data Simulator")
    print(f"  Device: {config.SERIAL_NUMBER}")
    print(f"  Topic: hydronew/ai/classification")
    print(f"  Publishing every 5 seconds...")
    print(f"{'='*70}\n")
    
    batch_count = 0
    
    try:
        while True:
            batch_count += 1
            
            # Generate sensor data for all three stages
            dirty, clean, hydro = generate_sensor_data()
            
            # Format as expected by AI classifier
            batch_data = f"{dirty}\n{clean}\n{hydro}"
            message = f"device_serial_number:{config.SERIAL_NUMBER}\n{batch_data}"
            
            # Print what we're sending
            print(f"[Batch #{batch_count}] {time.strftime('%H:%M:%S')}")
            print(f"  • {dirty}")
            print(f"  • {clean}")
            print(f"  • {hydro}")
            
            # Publish to MQTT
            publish("hydronew/ai/classification", message, QoS=1)
            print(f"  ✓ Published to MQTT\n")
            
            # Wait 5 seconds before next batch
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n{'='*70}")
        print(f"  Simulator stopped. Published {batch_count} batches.")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
