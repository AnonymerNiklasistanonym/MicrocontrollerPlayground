# python -m venv venv_test_sensors
# source venv_test_sensors/bin/activate
# pip install adafruit-circuitpython-dht --install-option="--force-pi"
# pip install RPi.GPIO
# python -m test_pins

import time
from . import pins

# requires 'RPi.GPIO'
import RPi.GPIO as GPIO
# requires 'adafruit-circuitpython-dht' (pip install adafruit-circuitpython-dht --install-option="--force-pi")
import adafruit_dht
import board

# GPIO pin where the DHT22 is connected (BCM numbering)
DHT22_PIN = board.D6
# GPIO pin where the MQ2 digital output is connected (BCM numbering)
MQ2_PIN = pins.gpio_pin_input_mq2
# GPIO pin where the MQ135 digital output is connected (BCM numbering)
MQ135_PIN = pins.gpio_pin_input_mq135

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(MQ2_PIN, GPIO.IN)
GPIO.setup(MQ135_PIN, GPIO.IN)

def main():
    try:
        print("Reading DHT22, MQ13 and MQ2 sensors...")
        dht_sensor = adafruit_dht.DHT22(DHT22_PIN)
        while True:
            try:
                temperature = dht_sensor.temperature
                humidity = dht_sensor.humidity
                if temperature is not None and humidity is not None:
                    print(f"DHT22 -> Temp: {temperature:.1f}°C  Humidity: {humidity:.1f}%")
                else:
                    print("DHT22 -> Failed to read data.")
            except RuntimeError as e:
                print(f"DHT22 -> Error: {e}")

            mq2_state = GPIO.input(MQ2_PIN)
            if mq2_state == GPIO.LOW:
                print("MQ2 -> Gas detected")
            else:
                print("MQ2 -> Air is clean")

            mq135_state = GPIO.input(MQ135_PIN)
            if mq135_state == GPIO.HIGH:
                print("MQ135 -> Air is clean")
            else:
                print("MQ135 -> Poor air quality detected")

            time.sleep(3)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Reset GPIO settings
        GPIO.cleanup()
        # Clean up the DHT sensor
        dht_sensor.exit()


if __name__ == "__main__":
    main()
