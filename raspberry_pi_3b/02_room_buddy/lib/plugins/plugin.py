from datetime import timedelta
from logging import Logger, LoggerAdapter
from typing import NewType

# requires 'gpiozero'
from gpiozero import RGBLED, Button

from lib.render.render import Action, Widget


ChangeDetected = NewType('ChangeDetected', bool)


class PluginLoggerPrefixAdapter(LoggerAdapter):
    def process(self, msg, kwargs):
        return f"{self.extra['prefix']} {msg}", kwargs


# Define a plugin interface
class PluginBase:
    def __init__(self, name: str, logger: Logger,
                 led_rgb_main: RGBLED, led_rgb_info: RGBLED, button_black: Button, button_red: Button,
                 simulate_circuit: bool, timedelta_offset: timedelta):
        self.name = name
        self.logger = PluginLoggerPrefixAdapter(logger, {"prefix": f"[Plugin {self.name}]"})
        self.led_rgb_main = led_rgb_main
        self.led_rgb_info = led_rgb_info
        self.button_red = button_red
        self.button_black = button_black
        self.simulate_circuit = simulate_circuit
        self.timedelta_offset = timedelta_offset

        self.logger.debug(f"Created plugin {simulate_circuit=}")

    async def run(self):
        """Start the plugin's async loop (overwrite to provide loop)"""
        self.logger.debug("Has not implemented an async `run` method")

    async def receive_signal(self, signal_id: str, data: dict):
        """Provide a method to get data from the plugin"""
        self.logger.debug("Has not implemented an async `receive_signal` method {signal_id=}")

    async def request_actions(self) -> tuple[list[Action], ChangeDetected]:
        """Provide a method to get request actions derived from this plugin"""
        self.logger.debug("Has not implemented an async `request_actions` method")
        return [], ChangeDetected(False)

    async def request_widgets(self) -> tuple[list[Widget], ChangeDetected]:
        """Provide a method to get request actions derived from this plugin"""
        self.logger.debug(f"Has not implemented an async `request_widgets` method")
        return [], ChangeDetected(False)

    def debug_set_timedelta_offset(self, timedelta_offset: timedelta):
        self.timedelta_offset = timedelta_offset
