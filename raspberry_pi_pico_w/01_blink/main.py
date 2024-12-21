from machine import Pin, Timer

# Onboard LED (Warning this LED can in rare cases die/be dead!)
led_onboard = Pin("LED", Pin.OUT)

# External LED (connected on one side to GPIO PIN 0 with a 220 Ohm resistor in between and to any GND PIN on the other)
led_external = Pin(16, Pin.OUT)


def blink(timer):
    print("toggle LED")
    led_onboard.toggle()
    led_external.toggle()


def main():
    # Create a timer which compared to sleep does not block the whole processor
    # It executes its callback in the background, allowing the rest of the program to run concurrently
    # sleep on the other hand blocks the entire program execution, pausing all operations for the specified duration
    timer = Timer()
    # period=milliseconds / freq=hertz
    timer.init(period=1000, mode=Timer.PERIODIC, callback=blink)


main()
