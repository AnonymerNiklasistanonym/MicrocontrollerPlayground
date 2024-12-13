import time
from threading import Thread, Event


class SimulatedButton:
    """Simulates a button."""
    def __init__(self, pin):
        self.pin = pin
        self._when_pressed = None
        self._when_released = None
        self._is_pressed = False
        print(f"Simulated Button initialized on pin {pin}")

    @property
    def is_pressed(self):
        return self._is_pressed

    @is_pressed.setter
    def is_pressed(self, value):
        self._is_pressed = value
        if value and self._when_pressed:
            self._when_pressed()
        elif not value and self._when_released:
            self._when_released()

    def when_pressed(self, callback):
        self._when_pressed = callback

    def when_released(self, callback):
        self._when_released = callback

    def simulate_press(self):
        """Simulate a button press."""
        print("Simulated button press.")
        self.is_pressed = True
        time.sleep(0.1)  # Simulate press duration
        self.is_pressed = False
