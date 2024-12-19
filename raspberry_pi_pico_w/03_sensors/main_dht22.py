from machine import Pin, Timer
from dht import DHT22

from pins_config import GPIO_PIN_INPUT_DHT22


DHT22_FREQUENCY = const(0.5)                   # Hertz
DHT22_TOLERANCE_TEMPERATURE = const(0.5)       # Degrees Celsius
DHT22_RANGE_TEMPERATURE = (-40, 80)
DHT22_TOLERANCE_RELATIVE_HUMIDITY = const(2.0) # Percent
DHT22_RANGE_RELATIVE_HUMIDITY = (0, 100)

# DHT22
dht22_sensor = DHT22(Pin(GPIO_PIN_INPUT_DHT22))


def dht22_read_sensor(timer):
    try:
        dht22_sensor.measure()
        temperatur = dht22_sensor.temperature()
        relative_humidity = dht22_sensor.humidity()
        print(f"Successfully read sensor [DHT22]: {temperatur=}°C, {relative_humidity=}%")
    except Exception as e:
        custom_print("Error reading sensor [DHT22]:", e)


def main():
    # Create a timer which compared to sleep does not block the whole processor
    # It executes its callback in the background, allowing the rest of the program to run concurrently
    # sleep on the other hand blocks the entire program execution, pausing all operations for the specified duration
    timer = Timer()
    timer.init(freq=DHT22_FREQUENCY, mode=Timer.PERIODIC, callback=dht22_read_sensor)


main()
