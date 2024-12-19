import asyncio
import os
import sys
from pathlib import Path

import aiohttp
from datetime import datetime
from typing import Optional, NewType

from lib.plugins.plugin import PluginBase, ChangeDetected
from lib.render.render import Widget, WidgetContent, create_qr_code
from lib.sensors.dht22 import DHT22_TOLERANCE_TEMPERATURE, DHT22_TOLERANCE_HUMIDITY
from .weather_db.weather_db import initialize_database, add_database_entry

TemperatureCelsius = NewType('TemperatureCelsius', float)
RelativeHumidityPercent = NewType('RelativeHumidityPercent', float)
AirPressurePascal = NewType('AirPressurePascal', float)

REQUEST_INTERVAL_SECONDS = 5  # Fetch data every 5 seconds

# database
DB_OUTDOOR_WEATHER = Path(os.path.dirname(os.path.realpath(sys.argv[0]))).joinpath("data", "outdoor_weather.db")


class Plugin(PluginBase):
    def __init__(self, tolerance_temp_dht22=DHT22_TOLERANCE_TEMPERATURE, tolerance_humidity_dht22=DHT22_TOLERANCE_HUMIDITY,
                 tolerance_temp_bmp280=0.5, tolerance_pressure_bmp280=1,
                 **kwargs):
        super().__init__("OutdoorWeather", **kwargs)
        self.temp_dht22: Optional[tuple[TemperatureCelsius, datetime]] = None
        self.humidity_dht22: Optional[tuple[RelativeHumidityPercent, datetime]] = None
        self.temp_bmp280: Optional[tuple[TemperatureCelsius, datetime]] = None
        self.pressure_bmp280: Optional[tuple[AirPressurePascal, datetime]] = None
        self.outdoor_weather_url: Optional[str] = None
        self.tolerance_temp_dht22 = tolerance_temp_dht22
        self.tolerance_humidity_dht22 = tolerance_humidity_dht22
        self.tolerance_temp_bmp280 = tolerance_temp_bmp280
        self.tolerance_pressure_bmp280 = tolerance_pressure_bmp280
        self.last_temp_dht22: Optional[TemperatureCelsius] = None
        self.last_humidity_dht22: Optional[RelativeHumidityPercent] = None
        self.last_temp_bmp280: Optional[TemperatureCelsius] = None
        self.last_pressure_bmp280: Optional[AirPressurePascal] = None
        self.qr_code_data_visualizer_url: Optional[str] = None
        self.qr_code_outdoor_weather_url: Optional[str] = None

    def temp_changed_dht22(self, old_temp: TemperatureCelsius | None, new_temp: TemperatureCelsius):
        return old_temp is None or abs(new_temp - old_temp) > self.tolerance_temp_dht22

    def temp_changed_bmp280(self, old_temp: TemperatureCelsius | None, new_temp: TemperatureCelsius):
        return old_temp is None or abs(new_temp - old_temp) > self.tolerance_temp_bmp280

    def humidity_changed_dht22(self, old_humidity: RelativeHumidityPercent | None, new_humidity: RelativeHumidityPercent):
        return old_humidity is None or abs(new_humidity - old_humidity) > self.tolerance_humidity_dht22

    def pressure_changed(self, old_pressure: AirPressurePascal | None, new_pressure: AirPressurePascal):
        return old_pressure is None or abs(new_pressure - old_pressure) > self.tolerance_pressure_bmp280

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
        self.qr_code_data_visualizer_url = os.getenv('QR_CODE_DATA_VISUALIZER_URL', None)
        self.qr_code_outdoor_weather_url = os.getenv('QR_CODE_OUTDOOR_WEATHER_URL', None)
        outdoor_weather_url = os.getenv('OUTDOOR_WEATHER_URL', '')
        if not outdoor_weather_url:
            raise RuntimeError("OUTDOOR_WEATHER_URL environment variable not set.")
        self.outdoor_weather_url = outdoor_weather_url
        initialize_database(DB_OUTDOOR_WEATHER, [
            ("dht22_temperature_celsius", "temperature_celsius", "REAL"),
            ("dht22_relative_humidity_percent", "relative_humidity_percent", "REAL"),
            ("bmp280_temperature_celsius", "temperature_celsius", "REAL"),
            ("bmp280_air_pressure_pa", "air_pressure_pa", "REAL"),
        ])
        while True:
            json_data = await self.fetch_data()
            if json_data:
                try:
                    temperature_timestamps_dht22 = json_data['dht22_temperature_celsius']
                    humidity_timestamps_dht22 = json_data['dht22_relative_humidity_percent']
                    temperature_timestamps_bmp280 = json_data['bmp280_temperature_celsius']
                    pressure_timestamps_bmp280 = json_data['bmp280_air_pressure_pa']

                    self.logger.error(f"{temperature_timestamps_dht22=}, {humidity_timestamps_dht22=} {temperature_timestamps_bmp280=}, {pressure_timestamps_bmp280=}")
                    for entry in temperature_timestamps_dht22:
                        add_database_entry(DB_OUTDOOR_WEATHER, "dht22_temperature_celsius", "temperature_celsius",
                                           datetime.fromisoformat(entry['timestamp']), entry['value'])
                    for entry in humidity_timestamps_dht22:
                        add_database_entry(DB_OUTDOOR_WEATHER, "dht22_relative_humidity_percent", "relative_humidity_percent",
                                           datetime.fromisoformat(entry['timestamp']), entry['value'])

                    for entry in temperature_timestamps_bmp280:
                        add_database_entry(DB_OUTDOOR_WEATHER, "bmp280_temperature_celsius", "temperature_celsius",
                                           datetime.fromisoformat(entry['timestamp']), entry['value'])
                    for entry in pressure_timestamps_bmp280:
                        add_database_entry(DB_OUTDOOR_WEATHER, "bmp280_air_pressure_pa", "air_pressure_pa",
                                           datetime.fromisoformat(entry['timestamp']), entry['value'])

                    if len(temperature_timestamps_dht22) > 0:
                        latest_temp = temperature_timestamps_dht22[-1]
                        temp, temp_time = latest_temp['value'], datetime.fromisoformat(latest_temp['timestamp'])
                        if self.temp_changed_dht22(None if self.temp_dht22 is None else self.temp_dht22[0], temp):
                            self.logger.info(f"[dht22] Detected temperature change: {temp=:.1f}")
                            self.temp_dht22 = temp, temp_time
                    if len(humidity_timestamps_dht22) > 0:
                        latest_humidity = humidity_timestamps_dht22[-1]
                        humidity, humidity_time = latest_humidity['value'], datetime.fromisoformat(latest_humidity['timestamp'])
                        if self.humidity_changed_dht22(None if self.humidity_dht22 is None else self.humidity_dht22[0], humidity):
                            self.logger.info(f"[dht22] Detected humidity change: {humidity=:.1f}")
                            self.humidity_dht22 = humidity, humidity_time

                    if len(temperature_timestamps_bmp280) > 0:
                        latest_temp = temperature_timestamps_bmp280[-1]
                        temp, temp_time = latest_temp['value'], datetime.fromisoformat(latest_temp['timestamp'])
                        if self.temp_changed_bmp280(None if self.temp_bmp280 is None else self.temp_bmp280[0], temp):
                            self.logger.info(f"[bmp280] Detected temperature change: {temp=:.1f}")
                            self.temp_bmp280 = temp, temp_time
                    if len(pressure_timestamps_bmp280) > 0:
                        latest_pressure = pressure_timestamps_bmp280[-1]
                        pressure, pressure_time = latest_pressure['value'], datetime.fromisoformat(latest_pressure['timestamp'])
                        if self.pressure_changed(None if self.pressure_bmp280 is None else self.pressure_bmp280[0], pressure):
                            self.logger.info(f"[bmp280] Detected pressure change: {pressure=:.1f}")
                            self.pressure_bmp280 = pressure, pressure_time

                except KeyError as e:
                    self.logger.error(f"Malformed JSON data: missing key {e}")
                except ValueError as e:
                    self.logger.error(f"Error parsing JSON data: {e}")

            await asyncio.sleep(REQUEST_INTERVAL_SECONDS)

    async def request_widgets(self):
        """Return the widget content based on the latest data."""
        if self.temp_dht22 is not None and self.humidity_dht22 is not None and self.temp_bmp280 is not None and self.pressure_bmp280 is not None:
            change_detected = ChangeDetected(False)
            if self.temp_changed_dht22(self.last_temp_dht22, self.temp_dht22[0]):
                self.last_temp_dht22 = self.temp_dht22[0]
                change_detected = ChangeDetected(True)
            if self.humidity_changed_dht22(self.last_humidity_dht22, self.humidity_dht22[0]):
                self.last_humidity_dht22 = self.humidity_dht22[0]
                change_detected = ChangeDetected(True)
            if self.temp_changed_bmp280(self.last_temp_bmp280, self.temp_bmp280[0]):
                self.last_temp_bmp280 = self.temp_bmp280[0]
                change_detected = ChangeDetected(True)
            if self.pressure_changed(self.last_pressure_bmp280, self.pressure_bmp280[0]):
                self.last_pressure_bmp280 = self.pressure_bmp280[0]
                change_detected = ChangeDetected(True)

            images = []
            if self.qr_code_data_visualizer_url:
                images.append(create_qr_code(self.qr_code_data_visualizer_url, 100))
            if self.qr_code_outdoor_weather_url:
                images.append(create_qr_code(self.qr_code_outdoor_weather_url, 100))
            return [Widget(generate_content=lambda: [
                WidgetContent(description="Outdoor:", text=""),
                WidgetContent(text=f"{self.temp_dht22[0]:.1f}°C / {self.humidity_dht22[0]:.0f}%"),
                WidgetContent(text=f"{self.temp_bmp280[0]:.1f}°C / {self.pressure_bmp280[0] / 100:.0f}hPa", images=images),
            ])], change_detected
        else:
            return [], ChangeDetected(False)
