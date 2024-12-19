from machine import Pin, Timer


led_onboard = Pin("LED", Pin.OUT)


def blink(timer):
    print("toggle LED")
    led_onboard.toggle()


def main():
    # Create a timer which compared to sleep does not block the whole processor
    # It executes its callback in the background, allowing the rest of the program to run concurrently
    # sleep on the other hand blocks the entire program execution, pausing all operations for the specified duration
    timer = Timer()
    # period=milliseconds / freq=hertz
    timer.init(period=1000, mode=Timer.PERIODIC, callback=blink)


main()
