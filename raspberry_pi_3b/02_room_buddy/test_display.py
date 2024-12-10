# python -m venv venv_test_display
# source venv_test_display/bin/activate
# pip install gpiozero lgpio spidev Pillow
# python -m test_display

import sys
import os
from waveshare_epd import epd7in5_V2
# requires 'Pillow'
from PIL import Image, ImageDraw, ImageFont


def main():
    try:
        # Initialize the display
        epd = epd7in5_V2.EPD()
        epd.init()
        epd.Clear()

        # Create a new blank image in 1-bit color mode (Black and White)
        width, height = epd.width, epd.height  # Display dimensions (800x480 for 7.5-inch)
        image = Image.new('1', (width, height), 255)  # 255: white background

        # Use PIL to draw on the image
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)

        # Draw some text
        draw.text((10, 10), "Hello Waveshare e-Paper!", font=font, fill=0)  # Black text

        # Draw a rectangle
        draw.rectangle((50, 50, 250, 150), outline=0)  # Black rectangle border

        # Send the image to the display
        epd.display(epd.getbuffer(image))

        # Put the display to sleep
        epd.sleep()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
