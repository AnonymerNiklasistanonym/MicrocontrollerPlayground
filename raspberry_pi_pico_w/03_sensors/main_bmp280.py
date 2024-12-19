from machine import I2C, Pin, Timer

from bmp280 import *

from pins_config import GPIO_PIN_I2C_BMP280_SDA, GPIO_PIN_I2C_BMP280_SCL


BMP280_FREQUENCY_I2C = const(100000)                # Hertz (default 100kHz higher, fast mode 400kHz)
BMP280_FREQUENCY = const(157)                       # Hertz (WARNING: every 6.4ms!)
BMP280_TOLERANCE_AIR_PRESSURE = const(1 * 100)      # Pascal (Pascal * 100 to convert from Hectopascal)
BMP280_RANGE_AIR_PRESSURE = (300 * 100, 1100 * 100)
BMP280_TOLERANCE_TEMPERATURE = const(0.5)           # Degrees Celsius
BMP280_RANGE_TEMPERATURE = (-40, 85)

# BMP280
bmp280_sensor_i2c = I2C(0, sda=Pin(GPIO_PIN_I2C_BMP280_SDA), scl=Pin(GPIO_PIN_I2C_BMP280_SCL), freq=BMP280_FREQUENCY_I2C)
bmp280_sensor = BMP280(bmp280_sensor_i2c)


def calculate_altitude(pressure, sea_level_pressure=1013.25):
    """
    Calculate altitude based on the barometric formula (formula used is an approximation).

    :param pressure: Measured pressure in hPa
    :param sea_level_pressure: Sea-level pressure in hPa (global average: 1013.25hPa)
    :return: Altitude in meters
    """
    return 44330 * (1 - (pressure / sea_level_pressure) ** 0.1903)


def bmp280_read_sensor(timer):
    try:
        # Read temperature and pressure
        temperature = bmp280_sensor.temperature
        pressure = bmp280_sensor.pressure
        pressure_hpa = pressure / 100
         
        # OPTIONAL: Calculate altitude (requires local sea level pressure to be correct)
        calculated_altitude = calculate_altitude(pressure_hpa)

        print(f"Successfully read sensor [BMP280]: {temperature=}°C, {pressure=}Pa/{pressure_hpa:.2f}hPa [{calculated_altitude=}m]")
    except Exception as e:
        print("Error reading sensor [BMP280]:", e)


def main():
    # OPTIONAL: Set the use case
    #bmp280_sensor.use_case(BMP280_CASE_WEATHER)
    bmp280_sensor.use_case(BMP280_CASE_INDOOR)

    # Create a timer which compared to sleep does not block the whole processor
    # It executes its callback in the background, allowing the rest of the program to run concurrently
    # sleep on the other hand blocks the entire program execution, pausing all operations for the specified duration
    timer = Timer()
    # Since the possible frequency is very high use instead a much slower one (e.g. 2s)
    # WARNING: It will crash the pico connection when trying to print a message every 6ms! 
    timer.init(period=2000, mode=Timer.PERIODIC, callback=bmp280_read_sensor)


main()
