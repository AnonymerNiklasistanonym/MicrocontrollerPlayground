# python -m venv_led_rgb_led_button_async
# source venv_led_rgb_led_button_async/bin/activate
# pip install gpiozero lgpio / pip install -r requirements_led_rgb_led_button_async.txt

import asyncio
# requires 'gpiozero' ('python3-gpiozero')
from gpiozero import LED, Button, RGBLED

button = Button(21)
led = LED(19)
led_rgb = RGBLED(5, 6, 13)


async def led_animation():
    while True:
        for color in [(0, 0, 1), (0, 1, 0), (1, 0, 0), (1, 1, 1)]:
            print("on", color)
            led.on()
            led_rgb.on()
            led_rgb.color = color
            await asyncio.sleep(5)
            print("off")
            led.off()
            led_rgb.off()
            await asyncio.sleep(1)


async def monitor_button():
    while True:
        if button.is_active:
            print("Button pressed")
            # Small delay for button debounce
            await asyncio.sleep(0.5)
        # Small delay to prevent busy-waiting
        await asyncio.sleep(0.1)


async def main():
    await asyncio.gather(
        led_animation(),
        monitor_button(),
    )


if __name__ == '__main__':
    asyncio.run(main())
