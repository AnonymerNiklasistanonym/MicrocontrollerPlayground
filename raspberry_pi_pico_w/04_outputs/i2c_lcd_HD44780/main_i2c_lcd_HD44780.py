import utime
from machine import I2C, Pin

from pico_i2c_lcd import I2cLcd

from pins_config import GPIO_PIN_I2C_HD44780_SDA, GPIO_PIN_I2C_HD44780_SCL


def i2c_scan(i2c):
    devices = i2c.scan()
    if devices:
        print("I2C devices found at addresses:")
        for device in devices:
            print(hex(device))
    else:
        raise RuntimeError("No I2C devices found!")


HD44780_LCD_I2C_ADDR     = const(0x27)
HD44780_LCD_I2C_NUM_ROWS = const(4)
HD44780_LCD_I2C_NUM_COLS = const(20)
HD44780_LCD_I2C_FREQ = const(400000)

# HD44780 (LCD) [2004A]
i2c = I2C(0, sda=Pin(GPIO_PIN_I2C_HD44780_SDA), scl=Pin(GPIO_PIN_I2C_HD44780_SCL), freq=HD44780_LCD_I2C_FREQ)
i2c_scan(i2c)
lcd = I2cLcd(i2c, HD44780_LCD_I2C_ADDR, HD44780_LCD_I2C_NUM_ROWS, HD44780_LCD_I2C_NUM_COLS)


def scroll_text_horizontal(lcd, text_rows, delay=0.025):
    """Scroll text horizontally"""
    max_length = max([len(text_row) for text_row in text_rows])
    updated_text_rows = []
    for text_row in text_rows:
        updated_text_rows.append(" " * lcd.num_columns + text_row + " " * (lcd.num_columns + max_length - len(text_row)))
    for i in range(max_length + lcd.num_columns):
        for index, text_row in enumerate(updated_text_rows):
            lcd.move_to(0, index)
            lcd.putstr(text_row[i:i + lcd.num_columns])
        utime.sleep(delay)


def scroll_text_zigzag(lcd, text, delay=0.025):
    """Scrolls text across the rows in a zigzag pattern"""
    text = " " * (lcd.num_lines * lcd.num_columns) + text + " " * (lcd.num_lines * lcd.num_columns)
    for i in range(len(text) - (lcd.num_lines * lcd.num_columns) + 1):
        lcd.move_to(0, 0)
        lcd.putstr(text[i:i + (lcd.num_lines * lcd.num_columns)])
        utime.sleep(delay)


def main():
    # Write strings
    lcd.putstr("Hello world!")
    utime.sleep(2)

    # Change backlight
    lcd.backlight_off()
    utime.sleep(2)
    lcd.backlight_on()
    utime.sleep(2)

    # Change display
    lcd.display_off()
    utime.sleep(2)
    lcd.display_on()
    utime.sleep(2)

    # Clear content
    lcd.clear()
    utime.sleep(2)

    # Display all possible characters [0,255]
    char_code = 0
    while char_code <= 255:
        lcd.clear()
        for row in range(HD44780_LCD_I2C_NUM_ROWS):
            for col in range(HD44780_LCD_I2C_NUM_COLS):
                if char_code <= 255:
                    lcd.move_to(col, row)
                    lcd.putchar(chr(char_code))
                    char_code += 1
                else:
                    break
        utime.sleep(2)

    # Show cursor
    lcd.clear()
    lcd.putstr("Hello ")
    lcd.show_cursor()
    utime.sleep(2)
    lcd.putstr("world!")
    utime.sleep(2)
    lcd.hide_cursor()
    utime.sleep(2)
    lcd.move_to(0, 1)
    lcd.putstr("Hello ")
    lcd.show_cursor()
    lcd.blink_cursor_on()
    utime.sleep(2)
    lcd.putstr("world!")
    utime.sleep(2)
    lcd.blink_cursor_off()
    lcd.hide_cursor()

    # Scroll text horizontally (single row(s))
    lcd.clear()
    for _ in range(2):
        scroll_text_horizontal(lcd, ["Hello world!"])
    utime.sleep(2)
    # ONLY WORKS WHEN 4 ROWS OR MORE EXIST!
    scroll_text_horizontal(lcd, [
        "".join([chr(char_code) for char_code in range(0, 255 + 1)]),
        "".join([str(x % 1000 // 100) for x in range(0, 255 + 1)]),
        "".join([str(x % 100 // 10) for x in range(0, 255 + 1)]),
        "".join([str(x % 10) for x in range(0, 255 + 1)]),
    ])
    utime.sleep(2)

    # Scroll text zigzag horizontal (across all rows)
    lcd.clear()
    for _ in range(2):
        scroll_text_zigzag(lcd, "".join([chr(char_code) for char_code in range(0, 255 + 1)]), 0)
    utime.sleep(2)

    # Display custom chars (8 rows x 5 columns of pixels: 0b + 0=off/1=on)
    heart = [
        0b00000,  # Row 1: Empty row
        0b01010,  # Row 2: Two small dots forming the top of the heart
        0b11111,  # Row 3: Full row for the top curve of the heart
        0b11111,  # Row 4: Full row for the bottom curve of the heart
        0b01110,  # Row 5: Middle part of the heart
        0b00100,  # Row 6: Narrowing down to the bottom tip
        0b00000,  # Row 7: Empty row
        0b00000,  # Row 8: Empty row
    ]
    # 8 custom chars can be stored in CGRAM locations at a time
    lcd.custom_char(0, heart)  # Store the heart to CGRAM location 0
    lcd.clear()
    lcd.putstr("Heart: " + chr(0) * (lcd.num_columns - 7))



main()
