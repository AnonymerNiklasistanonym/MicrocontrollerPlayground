from typing import NewType

FrequencyHertz = NewType('FrequencyHertz', float)
TemperatureCelsius = NewType('TemperatureCelsius', float)
RelativeHumidityPercent = NewType('RelativeHumidityPercent', float)

DHT22_UPDATE_FREQUENCY = FrequencyHertz(0.5)
DHT22_TOLERANCE_TEMPERATURE = TemperatureCelsius(0.5)
DHT22_TOLERANCE_HUMIDITY = RelativeHumidityPercent(2)
