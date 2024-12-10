# python -m venv venv_test_board
# source venv_test_board/bin/activate
# pip install gpiozero lgpio
# python -m test_board

import asyncio
# requires 'gpiozero' ('python3-gpiozero')
from gpiozero import Button, RGBLED

button_red = Button(19)
button_black = Button(26)
led_rgb_1 = RGBLED(23, 24, 25)
led_rgb_2 = RGBLED(16, 20, 21)


async def rgb_led_animation(rgb_led: RGBLED, offset=0, speed=5, name="rgb_led"):
    await asyncio.sleep(offset)
    while True:
        rgb_led.on()
        for color in [(0, 0, 1), (0, 1, 0), (1, 0, 0), (1, 1, 1), (0, 0, 0)]:
            print(f"RGBLED on ({name})", color)
            rgb_led.color = color
            await asyncio.sleep(speed)


async def monitor_button(button: Button, name="button", delay_button_debounce=0.5, delay_busy_waiting=0.1):
    while True:
        if button.is_active:
            print(f"Button pressed ({name})")
            await asyncio.sleep(delay_button_debounce)
        await asyncio.sleep(delay_busy_waiting)


async def main():
    await asyncio.gather(
        rgb_led_animation(led_rgb_1, name="rgb_led_1"),
        rgb_led_animation(led_rgb_2, name="rgb_led_2", offset=5),
        monitor_button(button_red, name="button_red"),
        monitor_button(button_black, name="button_black"),
    )


if __name__ == '__main__':
    asyncio.run(main())
