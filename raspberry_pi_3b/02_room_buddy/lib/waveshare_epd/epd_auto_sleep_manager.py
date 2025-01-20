import threading
from datetime import datetime, timedelta
from typing import Optional

# requires 'Pillow'
from PIL import ImageChops, Image, ImageDraw, ImageFont

from lib.waveshare_epd.epd7in5_V2 import EPD


def add_text_to_image(image: Image, text, font_path=None, font_size=20, text_color=0) -> Image:
    """
    Adds text to the bottom-right corner of a PIL.Image.
    """
    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Load the font
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    # Get the size of the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Calculate the position for the bottom-right corner
    x = image.width - text_width - 10  # 10px padding from the right edge
    y = image.height - text_height - 10  # 10px padding from the bottom edge

    # Add the text to the image
    draw.text((x, y), text, fill=text_color, font=font)

    return image


class EPaperDisplayManager:
    def __init__(self, epd: EPD):
        self.epd = epd
        self.last_displayed_image: Optional[Image] = None
        self.last_update_time = datetime.now()
        self.sleep_timer = None
        self.sleep_delay = timedelta(minutes=1)
        self.sleeping = True

    def _update_display(self, image: Image, status: str):
        """
        Updates the e-paper display if the image is different and resets the sleep timer.
        """
        if image is not None:
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
            status_text = f"{status} {formatted_datetime}"

            image_new = add_text_to_image(image, status_text)

            if self.last_displayed_image is None:
                self.epd.display(self.epd.getbuffer(image_new))
            else:
                self.epd.display_Partial(self.epd.getbuffer(image_new), 0, 0, image_new.width, image_new.height)

    def update_display(self, image: Image):
        """
        Updates the e-paper display if the image is different and resets the sleep timer.
        """
        if not self.images_are_equal(image, self.last_displayed_image):
            if self.sleeping:
                self.sleeping = False
                self.epd.init()

            self._update_display(image.copy(), "waiting")
            self.last_displayed_image = image.copy()
            self.last_update_time = datetime.now()

            # Reset the sleep timer
            if self.sleep_timer:
                self.sleep_timer.cancel()
            self._start_sleep_timer()
        else:
            print("Image unchanged. No update to display.")

    @staticmethod
    def images_are_equal(img1: Image, img2: Optional[Image]):
        """
        Compares two PIL images for equality.
        """
        if img1 is None or img2 is None:
            return False
        if img1.size != img2.size or img1.mode != img2.mode:
            return False
        diff = ImageChops.difference(img1, img2)
        return not diff.getbbox()

    def _start_sleep_timer(self):
        """
        Starts a timer to put the e-paper display to sleep after a delay.
        """
        self.sleep_timer = threading.Timer(self.sleep_delay.total_seconds(), self._put_display_to_sleep)
        self.sleep_timer.start()

    def _put_display_to_sleep(self):
        """
        Puts the e-paper display to sleep if the displayed image has not changed for the sleep delay period.
        """
        if datetime.now() - self.last_update_time >= self.sleep_delay:
            print("Image unchanged for 1 minute. E-paper display is going to sleep.")

            if self.last_displayed_image is not None:
                self._update_display(self.last_displayed_image, "sleeping")

            self.epd.sleep()
            self.sleeping = True

    def cancel_sleep_timer(self):
        """
        Cancels the sleep timer, preventing the display from sleeping.
        """
        if self.sleep_timer:
            self.sleep_timer.cancel()
            self.sleep_timer = None
