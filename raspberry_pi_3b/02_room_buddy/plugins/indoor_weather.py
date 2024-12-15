import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, NewType


from lib.plugins.plugin import PluginBase, ChangeDetected
from lib.render.render import Widget, WidgetContent
from lib.is_raspberry_pi.is_raspberry_pi import is_raspberry_pi
from lib.sensors.dht22 import DHT22_TOLERANCE_TEMPERATURE, DHT22_TOLERANCE_HUMIDITY, DHT22_UPDATE_FREQUENCY
from .weather_db.weather_db import initialize_database, add_database_entry

detected_raspberry_pi = is_raspberry_pi()
if detected_raspberry_pi:
    # requires 'adafruit-circuitpython-dht'
    import adafruit_dht
    import board


TemperatureCelsius = NewType('TemperatureCelsius', float)
RelativeHumidityPercent = NewType('RelativeHumidityPercent', float)


# GPIO pin where the DHT22 is connected (BCM numbering)
DHT22_PIN = board.D6 if detected_raspberry_pi else None

# database
DB_INDOOR_WEATHER = Path(os.path.dirname(os.path.realpath(sys.argv[0]))).joinpath("data", "indoor_weather.db")


class Plugin(PluginBase):
    def __init__(self, tolerance_temp=DHT22_TOLERANCE_TEMPERATURE, tolerance_humidity=DHT22_TOLERANCE_HUMIDITY,
                 **kwargs):
        super().__init__("IndoorWeather", **kwargs)
        self.temp: Optional[tuple[TemperatureCelsius, datetime]] = None
        self.humidity: Optional[tuple[RelativeHumidityPercent, datetime]] = None
        self.tolerance_temp = tolerance_temp
        self.tolerance_humidity = tolerance_humidity
        self.last_temp: Optional[TemperatureCelsius] = None
        self.last_humidity: Optional[RelativeHumidityPercent] = None
        self.dht_sensor = None if self.simulate_circuit else adafruit_dht.DHT22(DHT22_PIN)

    def temp_changed(self, old_temp: TemperatureCelsius | None, new_temp: TemperatureCelsius):
        return old_temp is None or abs(new_temp - old_temp) > self.tolerance_temp

    def humidity_changed(self, old_humidity: RelativeHumidityPercent | None, new_humidity: RelativeHumidityPercent):
        return old_humidity is None or abs(new_humidity - old_humidity) > self.tolerance_humidity

    async def run(self):
        """Simulate temperature data collection"""
        initialize_database(DB_INDOOR_WEATHER, [
            ("temperature_data", "temperature_celsius", "REAL"),
            ("relative_humidity_data", "relative_humidity_percent", "REAL")
        ])
        while True:
            try:
                current_time = datetime.now()
                if self.dht_sensor is not None:
                    temp, humidity = self.dht_sensor.temperature, self.dht_sensor.humidity
                else:
                    temp, humidity = 23.0, 50.0
                if temp is not None and humidity is not None:
                    self.logger.info(f"Read from DHT22: {temp=:.1f}°C {humidity=:.1f}%")
                    if self.temp_changed(None if self.temp is None else self.temp[0], temp):
                        self.logger.info(f"Detected change: {temp=:.1f}")
                        self.temp = temp, current_time
                        add_database_entry(DB_INDOOR_WEATHER, "temperature_data", "temperature_celsius",
                                           current_time, temp)
                    if self.humidity_changed(None if self.humidity is None else self.humidity[0], humidity):
                        self.logger.info(f"Detected change: {humidity=:.1f}")
                        self.humidity = humidity, current_time
                        add_database_entry(DB_INDOOR_WEATHER, "relative_humidity_data", "relative_humidity_percent",
                                           current_time, humidity)
                else:
                    self.logger.warning(f"Read from DHT22: Failed to read data.")
            except RuntimeError as e:
                self.logger.warning(f"Error from DHT22: {e}")
            await asyncio.sleep(1 / DHT22_UPDATE_FREQUENCY)

    async def request_widgets(self):
        """Return the current list of temperatures"""
        if self.temp is not None and self.humidity is not None:
            change_detected = ChangeDetected(False)
            if self.temp_changed(self.last_temp, self.temp[0]):
                self.last_temp = self.temp[0]
                change_detected = ChangeDetected(True)
            if self.humidity_changed(self.last_humidity, self.humidity[0]):
                self.last_humidity = self.humidity[0]
                change_detected = ChangeDetected(True)
            return [Widget(generate_content=lambda: [
                WidgetContent(("Indoor:", "")),
                WidgetContent(("Temperature", f"{self.temp[0]}°C")),
                WidgetContent(("Relative humidity", f"{self.humidity[0]}%")),
            ])], change_detected
        else:
            return [], ChangeDetected(False)
