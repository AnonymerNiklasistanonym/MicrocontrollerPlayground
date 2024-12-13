import asyncio
import os

import aiohttp
from datetime import datetime, timedelta
from logging import Logger
from typing import Optional, NewType

from lib.plugins.plugin import PluginBase, ChangeDetected
from lib.render.render import Widget, WidgetContent
from lib.sensors.dht22 import DHT22_TOLERANCE_TEMPERATURE, DHT22_TOLERANCE_HUMIDITY

TemperatureCelsius = NewType('TemperatureCelsius', float)
RelativeHumidityPercent = NewType('RelativeHumidityPercent', float)

REQUEST_INTERVAL_SECONDS = 5  # Fetch data every 5 seconds


class Plugin(PluginBase):
    def __init__(self,  tolerance_temp=DHT22_TOLERANCE_TEMPERATURE, tolerance_humidity=DHT22_TOLERANCE_HUMIDITY,
                 **kwargs):
        super().__init__("OutdoorWeather", **kwargs)
        self.temp: Optional[tuple[TemperatureCelsius, datetime]] = None
        self.humidity: Optional[tuple[RelativeHumidityPercent, datetime]] = None
        self.outdoor_weather_url: Optional[str] = None
        self.tolerance_temp = tolerance_temp
        self.tolerance_humidity = tolerance_humidity
        self.last_temp: Optional[TemperatureCelsius] = None
        self.last_humidity: Optional[RelativeHumidityPercent] = None

    def temp_changed(self, old_temp: TemperatureCelsius | None, new_temp: TemperatureCelsius):
        return old_temp is None or abs(new_temp - old_temp) > self.tolerance_temp

    def humidity_changed(self, old_humidity: RelativeHumidityPercent | None, new_humidity: RelativeHumidityPercent):
        return old_humidity is None or abs(new_humidity - old_humidity) > self.tolerance_humidity

    async def fetch_data(self):
        """Fetch the latest JSON data from the endpoint."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.outdoor_weather_url) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        return json_data
                    else:
                        self.logger.warning(f"Failed to fetch data: HTTP {response.status}")
            except Exception as e:
                self.logger.error(f"Error fetching data: {e}")
        return None

    async def run(self):
        """Periodically fetch data from the JSON endpoint."""
        outdoor_weather_url = os.getenv('OUTDOOR_WEATHER_URL', '')
        if not outdoor_weather_url:
            raise RuntimeError("OUTDOOR_WEATHER_URL environment variable not set.")
        self.outdoor_weather_url = outdoor_weather_url
        while True:
            json_data = await self.fetch_data()
            if json_data:
                try:
                    temperature_timestamps = json_data['temperature_timestamps']
                    humidity_timestamps = json_data['humidity_timestamps']

                    if len(temperature_timestamps) > 0:
                        latest_temp = temperature_timestamps[-1]
                        temp, temp_time = latest_temp
                        temp_time = datetime.fromisoformat(temp_time)
                        if self.temp_changed(None if self.temp is None else self.temp[0], temp):
                            self.logger.info(f"Detected temperature change: {temp=:.1f}")
                            self.temp = temp, temp_time
                    if len(humidity_timestamps) > 0:
                        latest_humidity = humidity_timestamps[-1]
                        humidity, humidity_time = latest_humidity
                        humidity_time = datetime.fromisoformat(humidity_time)
                        if self.humidity_changed(None if self.humidity is None else self.humidity[0], humidity):
                            self.logger.info(f"Detected humidity change: {humidity=:.1f}")
                            self.humidity = humidity, humidity_time

                except KeyError as e:
                    self.logger.error(f"Malformed JSON data: missing key {e}")
                except ValueError as e:
                    self.logger.error(f"Error parsing JSON data: {e}")

            await asyncio.sleep(REQUEST_INTERVAL_SECONDS)

    async def request_widgets(self):
        """Return the widget content based on the latest data."""
        if self.temp is not None and self.humidity is not None:
            change_detected = ChangeDetected(False)
            if self.temp_changed(self.last_temp, self.temp[0]):
                self.last_temp = self.temp[0]
                change_detected = ChangeDetected(True)
            if self.humidity_changed(self.last_humidity, self.humidity[0]):
                self.last_humidity = self.humidity[0]
                change_detected = ChangeDetected(True)

            return [Widget(generate_content=lambda: [
                WidgetContent(("Outdoor:", "")),
                WidgetContent(("Temperature", f"{self.temp[0]}°C")),
                WidgetContent(("Relative humidity", f"{self.humidity[0]}%")),
            ])], change_detected
        else:
            return [], ChangeDetected(False)
