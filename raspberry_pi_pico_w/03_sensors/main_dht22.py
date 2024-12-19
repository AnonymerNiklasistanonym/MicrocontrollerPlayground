from machine import Pin, Timer
from dht import DHT22

from pins_config import GPIO_PIN_INPUT_DHT22


# DHT22
dht22_sensor = DHT22(Pin(GPIO_PIN_INPUT_DHT22))
DHT22_TOLERANCE_TEMP = 0.5     # Degrees Celsius
DHT22_TOLERANCE_HUMIDITY = 2.0 # Percent
DHT22_FREQUENCY = 0.5          # Hertz


def dht22_read_sensor(timer):
    try:
        dht22_sensor.measure()
        temperatur = dht22_sensor.temperature()
        humidity = dht22_sensor.humidity()
        print(f"Successfully read sensor [DHT22]: {temperatur=},{humidity=}")
    except Exception as e:
        custom_print("Error reading sensor [DHT22]:", e)

def main():
    # Create a timer which compared to sleep does not block the whole processor
    # It executes its callback in the background, allowing the rest of the program to run concurrently
    # sleep on the other hand blocks the entire program execution, pausing all operations for the specified duration
    timer = Timer()
    timer.init(period=int(1 / DHT22_FREQUENCY * 1000), mode=Timer.PERIODIC, callback=dht22_read_sensor)

main()
