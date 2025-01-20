import asyncio
import os
import sys
from pathlib import Path
from datetime import timedelta, datetime
import logging

# requires 'gpiozero'
from gpiozero import Button, RGBLED

from lib.simulated_electronic_components.simulated_button import SimulatedButton
from lib.simulated_electronic_components.simulated_led_rgb import SimulatedRGBLED

# make systemd journal logging integration optional (makes code runnable on more linux distros and windows)
try:
    # requires 'systemd-python' (or in a venv: sudo apt install libsystemd-dev, pip install systemd-python)
    import journal
    has_journal_systemd_library = True
except ImportError:
    has_journal_systemd_library = False

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import pins
from lib.render.render import render_display_bw
from lib.plugins.plugin_manager import PluginManager
from lib.is_raspberry_pi.is_raspberry_pi import is_raspberry_pi
detected_raspberry_pi = is_raspberry_pi()
if detected_raspberry_pi:
    # when running on a raspberry pi it loads the e-paper display library
    from lib.waveshare_epd import epd7in5_V2
    from lib.waveshare_epd.epd_auto_sleep_manager import EPaperDisplayManager
else:
    # when running on a dev pc it loads tkinter to simulate the e-paper display
    import tkinter as tk
    from PIL import ImageTk


# Global variables
# > Logging
logger_id = "room_buddy"
logging.basicConfig()
logger = logging.getLogger(logger_id)
logger.setLevel(logging.DEBUG)
logger.debug(f"{has_journal_systemd_library=}")
if has_journal_systemd_library:
    from systemd import journal
    logger.addHandler(journal.JournalHandler(SYSLOG_IDENTIFIER=logger_id))
# > Debugging
timedelta_offset = timedelta(days=0)


async def main():
    global detected_raspberry_pi
    if detected_raspberry_pi:
        epd = epd7in5_V2.EPD()
        epd_manager = EPaperDisplayManager(epd)
        display_resolution = epd.width, epd.height
        button_red = Button(pins.gpio_pin_input_pullup_button_red)
        button_black = Button(pins.gpio_pin_input_pullup_button_black)
        led_rgb_main = RGBLED(*pins.gpio_pins_output_pwm_led_rgb_main)
        led_rgb_info = RGBLED(*pins.gpio_pins_output_pwm_led_rgb_info)

        def turn_on():
            logger.debug(f"turn led on", led_rgb_main.color)
            led_rgb_main.color = (0, 0, 0) if led_rgb_main.color == (1, 0, 0) else (1, 0, 0)

        button_red.when_pressed = turn_on

        def turn_off():
            logger.debug(f"turn led off")
            led_rgb_main.color = 0, 0, 0

        button_black.when_pressed = turn_off
    else:
        # Simulate hardware for debugging on a PC that is not a Raspberry Pi (and has no GPIO connections)
        display_resolution = 800, 480
        button_red = SimulatedButton(pins.gpio_pin_input_pullup_button_red)
        button_black = SimulatedButton(pins.gpio_pin_input_pullup_button_black)
        led_rgb_main = SimulatedRGBLED(pins.gpio_pins_output_pwm_led_rgb_main)
        led_rgb_info = SimulatedRGBLED(pins.gpio_pins_output_pwm_led_rgb_info)

        root = tk.Tk()
        root.title("Debug render")
        root.geometry(f"{display_resolution[0]}x{display_resolution[1] + 120}")
        root.resizable(False, False)
        label = tk.Label(root)
        label.pack(fill=tk.BOTH, expand=True)

        async def update_tk_window():
            while True:
                root.update_idletasks()
                root.update()
                # Adjust this delay for responsiveness
                await asyncio.sleep(0.05)

        led_frame = tk.Frame(root)
        led_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        label_frame = tk.Frame(root)
        label_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        label = tk.Label(label_frame)
        label.pack(fill=tk.BOTH, expand=True)

        # Create a Canvas to draw the LEDs (colored rectangles) in the LED frame
        led_size = 50
        canvas = tk.Canvas(led_frame, width=display_resolution[0],
                           height=led_size)  # Adjusted for button space
        canvas.pack(fill=tk.BOTH, expand=True)

        # Function to draw LEDs as 100x100 colored rectangles
        def draw_leds(num_leds=10):
            # Calculate rows and columns of LEDs
            leds = []

            for col in range(num_leds):
                x1 = col * led_size
                y1 = 0
                x2 = x1 + led_size
                y2 = y1 + led_size

                def rgb_to_hex(rgb: tuple[float, float, float]):
                    """Convert RGB values to a hexadecimal color string."""
                    r, g, b = rgb
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)
                    return f'#{r:02x}{g:02x}{b:02x}'

                # Choose a random color for the LED (can be customized)
                if col == 0:
                    color = rgb_to_hex(led_rgb_main.color)
                elif col == 1:
                    color = rgb_to_hex(led_rgb_info.color)
                else:
                    color = f"#{hex((col * 1000) % 0xFFFFFF)[2:].zfill(6)}"
                led = canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                leds.append(led)

            return leds

        def on_red_button_press():
            button_red.simulate_press()
            led_rgb_main.color = (0, 0, 0) if led_rgb_main.color == (1, 0, 0) else (1, 0, 0)
            print("RED Button pressed")

        def on_black_button_press():
            button_black.simulate_press()
            led_rgb_main.color = (0, 0, 0)
            print("BLACK Button pressed")

        def update_timedelta(hours: int):
            global timedelta_offset
            timedelta_offset += timedelta(hours=hours)
            plugin_manager.debug_set_timedelta_offset(timedelta_offset)

        # Add buttons at the bottom of the window
        button1 = tk.Button(button_frame, text="Red Button", command=lambda: on_red_button_press())
        button1.pack(side=tk.LEFT, padx=10)
        button2 = tk.Button(button_frame, text="Black Button", command=lambda: on_black_button_press())
        button2.pack(side=tk.LEFT, padx=10)
        button3 = tk.Button(button_frame, text="+12h offset", command=lambda: update_timedelta(+12))
        button3.pack(side=tk.LEFT, padx=10)
        button4 = tk.Button(button_frame, text="-12h offset", command=lambda: update_timedelta(-12))
        button4.pack(side=tk.LEFT, padx=10)

        # schedule the Tkinter window update (without awaiting it since it is a forever loop!)
        # noinspection PyAsyncCall
        asyncio.create_task(update_tk_window())

        # Update function to periodically refresh the canvas
        def update_canvas():
            # Redraw LEDs on the canvas
            canvas.delete("all")  # Clear the canvas before redrawing
            draw_leds(num_leds=2)  # Redraw the LEDs
            button3.config(text=f"+12h offset {(datetime.now() + timedelta_offset).strftime('%m.%d %H:%M')}")  # Change button3 text
            button4.config(text=f"-12h offset {(datetime.now() + timedelta_offset).strftime('%m.%d %H:%M')}")  # Change button4 text
            # Call update_canvas again after 50 milliseconds
            root.after(50, update_canvas)

        update_canvas()

    global timedelta_offset
    plugin_manager = PluginManager(Path("plugins"), logger,
                                   led_rgb_main=led_rgb_main, led_rgb_info=led_rgb_info,
                                   button_red=button_red, button_black=button_black,
                                   simulate_circuit=not detected_raspberry_pi, timedelta_offset=timedelta_offset)
    await plugin_manager.load_plugins()
    # schedule to start all plugins (without awaiting it since it is a forever loop!)
    # noinspection PyAsyncCall
    asyncio.create_task(plugin_manager.start_plugins())

    # Periodically update the display
    while True:
        actions, actions_changed = await plugin_manager.request_actions()
        widgets, widgets_changed = await plugin_manager.request_widgets()
        logger.debug(f"{actions=}, {actions_changed=}, {widgets=}, {widgets_changed=}")

        if actions_changed or widgets_changed:
            logger.debug(f"update")
            image = render_display_bw(
                [action for group in actions.values() for action in group],
                [widget for group in widgets.values() for widget in group],
                display_resolution=display_resolution
            )
            if detected_raspberry_pi:
                epd_manager.update_display(image)
            else:
                new_photo = ImageTk.PhotoImage(image)
                label.config(image=new_photo)
                label.image = new_photo
            logger.debug(f"sleep")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Received exit, exiting safely")
