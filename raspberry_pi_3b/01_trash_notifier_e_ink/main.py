# python -m venv venv_project
# source venv_project/bin/activate
# python -m pip install requests gpiozero ics lgpio Pillow RPi.GPIO spi spidev / pip install -r requirements.txt

import asyncio
from datetime import datetime, timedelta, date
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
import logging

# requires 'systemd-python' (or in a venv: sudo apt install libsystemd-dev, pip install systemd-python)
from systemd import journal

# requires external file 'epd1in54.py' (requires 'RPi.GPIO', 'spi', 'spidev')
import epd1in54

# requires 'requests'
import requests
# requires 'Pillow'
from PIL import Image, ImageDraw, ImageFont
# requires 'gpiozero' ('python3-gpiozero')
from gpiozero import LED, Button, RGBLED
# requires 'ics'
from ics import Calendar
from ics.grammar.parse import ParseError
from tatsu.exceptions import FailedToken

# GPIO setup
button_took_out_brought_in = Button(21)
led_rgb_trash_type = RGBLED(5, 6, 13)
led_bring_in = LED(19)
led_take_out = LED(26)

# Trash type colors
TRASH_COLORS: dict[str, tuple[float, float, float]] = {
    "Biomüll": (0, 1, 0),  # Green
    "Papier 120l/240l": (0, 0, 1),  # Blue
    "Restmüll 120l/240l": (1, 1, 0)  # Yellow
}

# Trash fetch constants
DAY_DELTA = 32
FETCH_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}
CACHE_FILE: Path = Path(gettempdir()) / "trash_dates.ics"

# EInk display constants
FONT_TTF: Path = Path('/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf')
FONT_SIZE_BIG = 36
FONT_SIZE_TEXT = 24
FONT_SIZE_UPDATE = 12
TEXT_SPACING = 8

# Updates
UPDATE_DELAY = 20  # 20s
# UPDATE_DELAY = 3600  # 1h
UPDATE_DELAY_BUTTON = 0.2  # 20s

# Debugging
DEBUG_DAY_OFFSET = timedelta(days=0)

# Global variables
# > Logging
logger = logging.getLogger("trash_notifier")
logger.setLevel(logging.DEBUG)
logger.addHandler(journal.JournalHandler(SYSLOG_IDENTIFIER='trash_notifier'))

# State variable to track button press
button_pressed = datetime.now().date() + DEBUG_DAY_OFFSET - timedelta(days=2)
trash_taken_out = False


def print_eink(trash_dates: list[tuple[date, str]]):
    logger.info("Update E-Ink display")
    # Create image to be displayed
    image = Image.new('1', (epd1in54.EPD_WIDTH, epd1in54.EPD_HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    font_text = ImageFont.truetype(FONT_TTF, FONT_SIZE_TEXT)
    font_big = ImageFont.truetype(FONT_TTF, FONT_SIZE_BIG)
    font_update = ImageFont.truetype(FONT_TTF, FONT_SIZE_UPDATE)
    # Next trash type header (black bg, white text)
    draw.rectangle((0, 0, epd1in54.EPD_WIDTH, 2 * TEXT_SPACING + FONT_SIZE_BIG), fill=0)
    y_position_text = TEXT_SPACING
    if len(trash_dates) > 0:
        draw.text((TEXT_SPACING, y_position_text), trash_dates[0][1], font=font_big, fill=255)
    y_position_text += FONT_SIZE_BIG + 2 * TEXT_SPACING
    # Next trash date
    for trash_date, trash_type in trash_dates:
        text = f"{trash_date.strftime('%d.%m')} {trash_type}"
        if y_position_text + FONT_SIZE_TEXT + 2 * TEXT_SPACING + FONT_SIZE_UPDATE > epd1in54.EPD_HEIGHT:
            break  # Stop, no vertical space available
        draw.text((TEXT_SPACING, y_position_text), text, font=font_text, fill=0)
        y_position_text += FONT_SIZE_TEXT + TEXT_SPACING
    # Add current time as indicator of the last update
    draw.text((TEXT_SPACING, epd1in54.EPD_HEIGHT - TEXT_SPACING - FONT_SIZE_UPDATE), datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              font=font_update, fill=0)
    # Initialize display (full update), clear frame memory, set new frame memory, display frame
    epd = epd1in54.EPD()
    epd.init(epd.lut_full_update)
    epd.clear_frame_memory(0xFF)
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()
    logger.debug("Updated E-Ink display")


def parse_ics(cache_file: Path) -> Calendar:
    logger.info("Parse ICS to calendar")
    with open(cache_file, "r") as f:
        calendar_raw = f.read()
        logger.debug("Read ICS file: '%s'", calendar_raw)
        calendar = Calendar(calendar_raw)
        logger.debug(f"Parsed ICS file content: {len(calendar.events)} events")
        return calendar


def get_trash_dates(calendar: Calendar) -> list[tuple[date, str]]:
    today = datetime.now().date() + DEBUG_DAY_OFFSET
    trash_dates: list[tuple[date, str]] = []

    for event in calendar.events:
        event_date = event.begin.date()
        if event_date >= today:
            trash_dates.append((event_date, event.name))

    # Sort by date just to ensure they are in chronological order
    trash_dates.sort(key=lambda x: x[0])

    logger.debug("Found %i trash dates and filtered them to %i dates", len(calendar.events), len(trash_dates))
    for trash_date, trash_type in trash_dates:
        logger.debug("%s - %s %s", trash_date.strftime('%m %d'), trash_type, TRASH_COLORS.get(trash_type))

    return trash_dates


async def fetch_and_parse_ics(cache_file: Path) -> Optional[list[tuple[date, str]]]:
    logger.info("fetch_and_parse_ics")
    """
    Fetches the ICS file from the web and parses it.
    Caches the file locally to reduce web requests.
    """
    # Fetch ICS file if not cached or older than 100 days
    today = datetime.now().date() + DEBUG_DAY_OFFSET
    future_date = today + timedelta(days=DAY_DELTA * 2)
    date_range = f"{today.strftime('%Y%m%d')}-{future_date.strftime('%Y%m%d')}"

    # Read calendar URL from environment variable
    calendar_url = os.getenv('CALENDAR_URL', '')
    if not calendar_url:
        logger.error("CALENDAR_URL environment variable not set.")
        return None

    # Check if the cache file needs to be updated
    if not os.path.exists(cache_file) or \
            datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file)) > timedelta(days=DAY_DELTA):
        calendar_url = f"{calendar_url}&timeperiod={date_range}"
        logger.debug("Requesting '%s'", calendar_url)
        response = requests.get(calendar_url, headers=FETCH_USER_AGENT)
        logger.debug("Fetched '%s'", response.content)
        with open(cache_file, "wb") as f:
            f.write(response.content)
            logger.debug("Cached request in '%s'", cache_file)

    # Parse ICS file
    try:
        calendar = parse_ics(cache_file)
        trash_dates = get_trash_dates(calendar)
        return trash_dates
    except FailedToken as e:
        logger.error(f"Parsing failed: {e}")
    except ParseError as e:
        logger.error(f"Parsing error: {e}")

    # Remove cache file on error
    if os.path.exists(cache_file):
        os.remove(cache_file)
        logger.warning(f"Removed cache file after errors: {cache_file}")
    return None


async def update_leds(trash_dates: list[tuple[date, str]]):
    logger.info("update_leds")
    global button_pressed
    global trash_taken_out

    today = datetime.now().date() + DEBUG_DAY_OFFSET
    tomorrow = today + timedelta(days=1)
    trash_type_tomorrow = None
    trash_type_bring_in = None
    for trash_date, trash_type in trash_dates:
        if trash_date == tomorrow:
            trash_type_tomorrow = trash_type
            break
    for trash_date, trash_type in trash_dates:
        if trash_date == today:
            trash_type_bring_in = trash_type
            break

    if trash_type_tomorrow and button_pressed != today:
        logger.debug(f"Trash tomorrow (take out): {trash_type_tomorrow} ({button_pressed=}!={today=}")

        trash_taken_out = False

        led_rgb_trash_type.color = TRASH_COLORS.get(trash_type_tomorrow, (1, 1, 1))
        led_take_out.on()
    else:
        logger.debug(f"%s (tomorrow) is not in the trash_dates: %s or button was pressed %s (today)",
                     tomorrow.strftime('%Y%m%d'), ",".join(x[0].strftime('%Y%m%d') for x in trash_dates),
                     today.strftime('%Y%m%d'))
        led_rgb_trash_type.off()
        led_take_out.off()

    if trash_taken_out and trash_type_bring_in and button_pressed != today:
        logger.debug(f"Trash today (bring in): {trash_type_bring_in}")

        led_bring_in.on()
    else:
        logger.debug(f"%s (today) is not in the trash_dates: %s or button was pressed %s (today)",
                     today.strftime('%Y%m%d'), ",".join(x[0].strftime('%Y%m%d') for x in trash_dates),
                     today.strftime('%Y%m%d'))
        led_bring_in.off()


async def button_control():
    logger.info("button_control")
    global button_pressed
    global trash_taken_out

    while True:
        if button_took_out_brought_in.is_pressed:
            button_pressed = datetime.now().date() + DEBUG_DAY_OFFSET
            logger.info(f"Button pressed: {button_pressed=}", )
            if led_bring_in.is_active:
                # Turn off bring-in LED
                led_bring_in.off()
                trash_taken_out = False
            if led_take_out.is_active:
                # Turn off bring-in LED
                led_take_out.off()
                led_rgb_trash_type.off()
                trash_taken_out = True
            # Debounce delay
            await asyncio.sleep(0.5)
        # Small delay to prevent busy-waiting
        await asyncio.sleep(UPDATE_DELAY_BUTTON)


async def check_for_tash_updates():

    # Schedule periodic checks and button handling
    retry_delay_ics = 1
    latest_trash_date: Optional[tuple[date, str]] = None

    while True:
        logger.debug("Run loop...")
        trash_dates = await fetch_and_parse_ics(cache_file=CACHE_FILE)
        if trash_dates is None:
            logger.warning(f"Unable to get trash dates ({retry_delay_ics=}s)")
            await asyncio.sleep(retry_delay_ics)
            retry_delay_ics = min(2 * retry_delay_ics, 60 * 60)
            continue
        retry_delay_ics = 1
        # Update display on trash date change
        if latest_trash_date is None or latest_trash_date[0].strftime('%Y%m%d') != trash_dates[0][0].strftime('%Y%m%d'):
            latest_trash_date = trash_dates[0]
            print_eink(trash_dates)

        logger.debug("Update LEDs...")
        await update_leds(trash_dates)
        logger.debug("Loop concluded... wait for delay...")
        await asyncio.sleep(UPDATE_DELAY)  # Check once every hour


async def main():
    await asyncio.gather(
        check_for_tash_updates(),
        button_control(),
    )


if __name__ == '__main__':
    asyncio.run(main())
