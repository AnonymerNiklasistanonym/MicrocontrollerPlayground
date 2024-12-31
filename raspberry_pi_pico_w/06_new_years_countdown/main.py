import utime
import time
from machine import I2C, Pin
import lcd_api
import ustruct
import network
import socket
import time
import os
import ntptime
from time import localtime
from machine import I2C, Pin

# Local libraries

from pico_i2c_lcd import I2cLcd

# Constants

from pins_config import GPIO_PIN_I2C_HD44780_SDA, GPIO_PIN_I2C_HD44780_SCL, GPIO_PIN_LED_ONE, GPIO_PIN_LED_TWO, GPIO_PIN_LED_THREE
from wifi_config import SSID, PASSWORD


def i2c_scan(i2c):
    devices = i2c.scan()
    if devices:
        print("I2C devices found at addresses:")
        for device in devices:
            print(hex(device))
    else:
        raise RuntimeError("No I2C devices found!")


HD44780_LCD_I2C_ADDR     = const(0x27)
HD44780_LCD_I2C_NUM_ROWS = const(2)  # or const(4) if 2004A instead of 1602
HD44780_LCD_I2C_NUM_COLS = const(16) # or const(20)
HD44780_LCD_I2C_FREQ = const(400000)

# HD44780 (LCD) [2004A]
i2c = I2C(1, sda=Pin(GPIO_PIN_I2C_HD44780_SDA), scl=Pin(GPIO_PIN_I2C_HD44780_SCL), freq=HD44780_LCD_I2C_FREQ)
i2c_scan(i2c)
lcd = I2cLcd(i2c, HD44780_LCD_I2C_ADDR, HD44780_LCD_I2C_NUM_ROWS, HD44780_LCD_I2C_NUM_COLS)

# Onboard LED
led_onboard = Pin("LED", Pin.OUT)

# External LEDs
led_1 = Pin(GPIO_PIN_LED_ONE, Pin.OUT)
led_2 = Pin(GPIO_PIN_LED_TWO, Pin.OUT)
led_3 = Pin(GPIO_PIN_LED_THREE, Pin.OUT)


def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Connecting to WiFi...")
    while not wlan.isconnected():
        print("...")
        led_onboard.on()
        time.sleep(0.5)
        led_onboard.off()
        time.sleep(0.5)
    print("Connected to WiFi:", wlan.ifconfig())
    return wlan.ifconfig()[0]


def sync_time():
    while True:
        try:
            previous_time = time.localtime()
            ntptime.settime()
            print(
                f"Time synchronized with NTP server. Previous time: {previous_time}, New time: {time.localtime()}"
            )
            break
        except Exception as e:
            # Log the error
            print(f"Failed to sync time: {e}")
            # Wait for 5 seconds before retrying
            time.sleep(5)
            

# Function to convert time tuple to seconds
def date_to_seconds(time_tuple):
    return time.mktime(time_tuple)

# Function to calculate the difference between two local times (in seconds)
def calculate_time_difference(date1, date2):
    return abs(date_to_seconds(date2) - date_to_seconds(date1))

# Countdown function
def countdown_to_new_year():
    start_time = time.ticks_ms() # Time when current time was set
    current_time = localtime()  # Get current local time
    #new_year_time = (2024, 12, 31, 18, 41, 0, 0, -1)  # Test based on current_time output
    new_year_time = (2025, 1, 1, 0, 0, 0, 0, 0, -1)  # New Year's Eve
    time_zone_offset = 1 * 60 * 60  # UTC+1
    
    # Debugging
    print(f"{current_time=} {new_year_time=} {time_zone_offset=}")
    
    # Calculate the total time difference (in seconds) from current time to new years
    diff_seconds_total = calculate_time_difference(current_time, new_year_time) - time_zone_offset

    while diff_seconds_total > 0:
        # Record the current time at the start of the loop iteration
        loop_start_time = time.ticks_ms()

        # Calculate the remaining time in seconds
        elapsed_time = time.ticks_diff(time.ticks_ms(), start_time) // 1000
        remaining_time = diff_seconds_total - elapsed_time

        # Stop if the remaining time is none
        if remaining_time <= 0:
            break
        # Turn LED 1 on 5 minutes before new years
        if remaining_time <= 60 * 5:
            led_1.on()
        # Turn LED 2 on 1 minute before new years
        if remaining_time <= 60:
            led_2.on()

        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        seconds = remaining_time % 60
        
        lcd.clear()
        lcd.putstr("Countdown: ")
        lcd.move_to(0, 1)
        lcd.putstr("{:02}:{:02}:{:02}".format(hours, minutes, seconds))

        # Measure the loop duration and sleep until the next second
        loop_end_time = time.ticks_ms()
        loop_duration = time.ticks_diff(loop_end_time, loop_start_time)

        time_to_sleep = max(0, 1000 - loop_duration)  # Ensure no negative sleep time
        time.sleep_ms(time_to_sleep)

    led_1.on()
    led_2.on()
    led_3.on()

    # Happy New Year :)
    lcd.clear()
    lcd.putstr("Happy New Year!")
    lcd.move_to(0, 1)
    lcd.putstr("2025!")


def main():
    led_1.on()
    led_2.on()
    led_3.on()
    
    lcd.clear()
    lcd.putstr("Connect to WIFI:")
    lcd.putstr(SSID)
    lcd.move_to(0, 1)

    # Connect to wifi
    led_onboard.off()
    ip = connect_to_wifi()
    led_onboard.on()
    
    lcd.clear()
    lcd.putstr("Synchronize time...")
    lcd.putstr(SSID)
    lcd.move_to(0, 1)

    # Sync time
    sync_time()
    
    led_1.off()
    led_2.off()
    led_3.off()
    
    # Countdown to new year
    countdown_to_new_year()
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program stopped.")
    except MemoryError:
        print("Memory error detected")
    except Exception as e:
        print(f"Unexpected error: {e}")
