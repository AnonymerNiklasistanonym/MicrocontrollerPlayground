# python -m venv venv_test_pins
# source venv_test_pins/bin/activate
# pip install RPi.GPIO
# python -m test_pins

# requires 'RPi.GPIO'
import RPi.GPIO as GPIO

BOARD_TO_BCM = {
    3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27, 15: 22,
    16: 23, 18: 24, 19: 10, 21: 9, 22: 25, 23: 11, 24: 8, 26: 7, 29: 5,
    31: 6, 32: 12, 33: 13, 35: 19, 36: 16, 37: 26, 38: 20, 40: 21
}


def read_pin_configuration():
    try:
        GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering

        # List of pins to check (modify based on your Raspberry Pi model)
        pins = [
            3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26,
            29, 31, 32, 33, 35, 36, 37, 38, 40
        ]

        # Dictionary to map function constants to readable names
        function_names = {
            GPIO.IN: "Input",
            GPIO.OUT: "Output",
            GPIO.SPI: "SPI",
            GPIO.I2C: "I2C",
            GPIO.HARD_PWM: "PWM",
            GPIO.SERIAL: "Serial",
            GPIO.UNKNOWN: "Unknown"
        }

        print("Reading GPIO pin configurations:")
        for board_pin, bcm_pin in BOARD_TO_BCM.items():
            try:
                # Get the current function of the pin
                func = GPIO.gpio_function(board_pin)
                func_name = function_names.get(func, "Unknown")
                print(f"Physical Pin {board_pin} (GPIO {bcm_pin}): {func_name}")
            except Exception as e:
                print(f"Error reading physical pin {board_pin}: {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()  # Reset GPIO settings


if __name__ == "__main__":
    read_pin_configuration()
