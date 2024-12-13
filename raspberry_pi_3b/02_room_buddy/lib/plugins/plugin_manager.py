import asyncio
import importlib
from logging import Logger
from pathlib import Path
from datetime import timedelta

# requires 'gpiozero'
from gpiozero import RGBLED, Button

from .plugin import PluginBase, ChangeDetected
from ..render.render import Action, Widget


# Plugin manager to load and manage plugins
class PluginManager:
    def __init__(self, plugin_dir: Path, logger: Logger,
                 led_rgb_main: RGBLED, led_rgb_info: RGBLED, button_black: Button, button_red: Button,
                 simulate_circuit: bool, timedelta_offset: timedelta):
        self.logger = logger
        self.led_rgb_main = led_rgb_main
        self.led_rgb_info = led_rgb_info
        self.button_red = button_red
        self.button_black = button_black
        self.simulate_circuit = simulate_circuit
        self.timedelta_offset = timedelta_offset

        self.plugin_dir = plugin_dir
        self.plugins = []

    async def load_plugins(self):
        """Dynamically load plugins from the plugin directory"""
        for file in self.plugin_dir.iterdir():
            if file.is_file() and file.suffix == ".py" and file.stem != "__init__":
                print(f"load plugin from {file}", f"{self.plugin_dir.name}.{file.stem}")
                module = importlib.import_module(f"{self.plugin_dir.name}.{file.stem}")
                plugin_class = getattr(module, "Plugin")
                if issubclass(plugin_class, PluginBase):
                    plugin_instance = plugin_class(logger=self.logger,
                                                   led_rgb_main=self.led_rgb_main,
                                                   led_rgb_info=self.led_rgb_info,
                                                   button_black=self.button_black,
                                                   button_red=self.button_red,
                                                   simulate_circuit=self.simulate_circuit,
                                                   timedelta_offset=self.timedelta_offset)
                    self.plugins.append(plugin_instance)

    async def start_plugins(self):
        """Start all loaded plugins"""
        tasks = [plugin.run() for plugin in self.plugins]
        await asyncio.gather(*tasks)

    async def request_actions(self) -> tuple[dict[str, list[Action]], ChangeDetected]:
        results = {}
        change_detected = ChangeDetected(False)
        for plugin in self.plugins:
            plugin_actions, plugin_change_detected = await plugin.request_actions()
            results[plugin.name] = plugin_actions
            if plugin_change_detected:
                change_detected = ChangeDetected(True)
        return results, change_detected

    async def request_widgets(self) -> tuple[dict[str, list[Widget]], ChangeDetected]:
        results = {}
        change_detected = ChangeDetected(False)
        for plugin in self.plugins:
            plugin_widgets, plugin_change_detected = await plugin.request_widgets()
            results[plugin.name] = plugin_widgets
            if plugin_change_detected:
                change_detected = ChangeDetected(True)
        return results, change_detected

    def debug_set_timedelta_offset(self, timedelta_offset: timedelta):
        for plugin in self.plugins:
            plugin.debug_set_timedelta_offset(timedelta_offset)

