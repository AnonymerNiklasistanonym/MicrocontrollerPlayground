class SimulatedRGBLED:
    """Simulates an RGB LED."""
    def __init__(self, rgb_pins: tuple[int, int, int]):
        self.color = (0, 0, 0)  # Initial color (off)
        self.red_pin, self.green_pin, self.blue_pin = rgb_pins
        print(f"Simulated RGBLED initialized on pins: {rgb_pins}")

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        print(f"Simulated RGBLED color set to R:{value[0]:.2f}, G:{value[1]:.2f}, B:{value[2]:.2f}")
