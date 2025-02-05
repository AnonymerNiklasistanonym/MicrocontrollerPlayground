import asyncio
import os
import re
from datetime import datetime, timedelta, time
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, NewType

# requires 'aiohttp'
import aiohttp
# requires 'ics'
from ics import Calendar
from ics.grammar.parse import ParseError
from tatsu.exceptions import FailedToken

from lib.plugins.plugin import PluginBase, ChangeDetected
from lib.render.render import Widget, WidgetContent, Action, ActionContent

TrashType = NewType('TrashType', str)
TrashEvent = tuple[datetime, TrashType]


# Trash type colors
TRASH_COLORS: dict[str, tuple[float, float, float]] = {
    "Biomüll": (0, 1, 0),  # Green
    "Papier": (0, 0, 1),  # Blue
    "Restmüll": (1, 1, 0)  # Yellow
}

# Trash fetch constants
DAY_DELTA = 32
FETCH_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}
CACHE_FILE: Path = Path(gettempdir()) / "trash_dates.ics"

# Debugging
DEBUG_DAY_OFFSET = timedelta(days=0)


def remove_measurements_ending_with_l(input_string):
    """
    Removes substrings like '120l', '240l', or groups like '120l/240l', but keeps regular words like 'Restmüll'.
    """
    # Match standalone measurements or groups separated by '/'
    filtered_string = re.sub(r'\b\d+\w*l(?:/\d+\w*l)*\b', '', input_string)

    # Remove extra spaces caused by deletion
    return ' '.join(filtered_string.split())


class Plugin(PluginBase):
    def __init__(self, **kwargs):
        super().__init__("TrashNotifier", **kwargs)
        self.calendar_url: Optional[str] = None
        self.current_trash_dates: Optional[list[TrashEvent]] = []
        self.hour_offset_trash_notification: int = 8
        # Keep track if there was an update between the last widget/action request
        self.last_checksum_widgets = ""
        self.last_checksum_actions = ""
        # Store what trash needs to be taken out or brought in
        self.trash_type_take_out: list[TrashType] = []
        self.trash_type_bring_in: list[TrashType] = []
        # Keep track of trash that was already taken out or brought in
        self.trash_taken_out: dict[TrashType, datetime] = dict()
        self.trash_brought_in: dict[TrashType, datetime] = dict()

    def parse_ics(self, cache_file: Path) -> Calendar:
        self.logger.info("Parse ICS to calendar")
        with open(cache_file, "r") as f:
            calendar_raw = f.read()
            self.logger.debug("Read ICS file: '%s'", calendar_raw)
            calendar = Calendar(calendar_raw)
            self.logger.debug(f"Parsed ICS file content: {len(calendar.events)} events")
            return calendar

    def get_trash_dates(self, calendar: Calendar) -> list[TrashEvent]:
        today = datetime.now() + DEBUG_DAY_OFFSET
        trash_dates: list[tuple[datetime, TrashType]] = []

        for event in calendar.events:
            event_date = event.begin.datetime
            if event_date.date() >= today.date():
                trash_dates.append((event_date, TrashType(remove_measurements_ending_with_l(event.name))))

        # Sort by date just to ensure they are in chronological order
        trash_dates.sort(key=lambda x: x[0])

        self.logger.debug("Found %i trash dates and filtered them to %i dates", len(calendar.events), len(trash_dates))
        for trash_date, trash_type in trash_dates:
            self.logger.debug("%s - %s %s", trash_date.strftime('%m %d'), trash_type, TRASH_COLORS.get(trash_type))

        return trash_dates

    async def fetch_and_parse_ics(self, cache_file: Path) -> Optional[list[TrashEvent]]:
        self.logger.info("fetch_and_parse_ics")
        """
        Fetches the ICS file from the web and parses it.
        Caches the file locally to reduce web requests.
        """

        if self.calendar_url is None:
            self.logger.error("calendar_url is None")
            return None

        # Fetch ICS file if not cached or older than 100 days
        today = datetime.now().date() + DEBUG_DAY_OFFSET
        future_date = today + timedelta(days=DAY_DELTA * 2)
        date_range = f"{today.strftime('%Y%m%d')}-{future_date.strftime('%Y%m%d')}"

        # Check if the cache file needs to be updated
        if not os.path.exists(cache_file) or \
                datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file)) > timedelta(days=DAY_DELTA):
            calendar_url = f"{self.calendar_url}&timeperiod={date_range}"
            self.logger.debug("Requesting '%s'", calendar_url)

            try:
                async with aiohttp.ClientSession(headers=FETCH_USER_AGENT) as session:
                    async with session.get(calendar_url) as response:
                        if response.status == 200:
                            content = await response.read()
                            self.logger.debug("Fetched '%s'", content)
                            with open(cache_file, "wb") as f:
                                f.write(content)
                                self.logger.debug("Cached request in '%s'", cache_file)
                        else:
                            self.logger.error(f"HTTP error {response.status} while fetching calendar URL")
                            return None
            except aiohttp.ClientError as e:
                self.logger.error(f"Error fetching calendar URL: {e}")
                return None

        # Parse ICS file
        try:
            calendar = self.parse_ics(cache_file)
            trash_dates = self.get_trash_dates(calendar)
            return trash_dates
        except FailedToken as e:
            self.logger.error(f"Parsing failed: {e}")
        except ParseError as e:
            self.logger.error(f"Parsing error: {e}")

        # Remove cache file on error
        if os.path.exists(cache_file):
            os.remove(cache_file)
            self.logger.warning(f"Removed cache file after errors: {cache_file}")
        return None

    async def run(self):
        calendar_url = os.getenv('CALENDAR_URL', '')
        if not calendar_url:
            raise RuntimeError("CALENDAR_URL environment variable not set.")
        self.calendar_url = calendar_url

        # Schedule periodic checks and button handling
        retry_delay_ics = 1

        while True:
            self.logger.debug("Run loop...")
            trash_dates = await self.fetch_and_parse_ics(CACHE_FILE)
            if trash_dates is None:
                self.logger.warning(f"Unable to get trash dates ({retry_delay_ics=}s)")
                await asyncio.sleep(retry_delay_ics)
                retry_delay_ics = min(2 * retry_delay_ics, 60 * 60)
                continue
            retry_delay_ics = 1
            self.current_trash_dates = trash_dates

            self.trash_type_take_out = []
            self.trash_type_bring_in = []

            if self.current_trash_dates is not None and len(self.current_trash_dates) > 0:
                current_time = datetime.now() + self.timedelta_offset
                tomorrow_time = current_time + timedelta(days=1)
                notification_time_take_out = datetime.combine(tomorrow_time.date(), time(0, 0)) - timedelta(hours=self.hour_offset_trash_notification)
                notification_time_bring_in = datetime.combine(current_time.date(), time(0, 0)) + timedelta(hours=self.hour_offset_trash_notification)

                for trash_date, trash_type in self.current_trash_dates:
                    trash_was_taken_out = trash_type in self.trash_taken_out and trash_date == self.trash_taken_out[trash_type]
                    trash_should_be_taken_out = trash_date.date() == tomorrow_time.date() and current_time >= notification_time_take_out
                    if trash_should_be_taken_out and not trash_was_taken_out:
                        self.trash_type_take_out.append(trash_type)

                        def take_out_trash(current_trash_date: datetime, current_trash_type: TrashType):
                            self.logger.debug(f"clicked black button: take_out_trash")
                            self.led_rgb_main.color = 0, 0, 0
                            self.led_rgb_info.color = 0, 0, 0
                            self.trash_taken_out[current_trash_type] = current_trash_date
                            self.trash_type_take_out = list(filter(lambda x: x != current_trash_type, self.trash_type_take_out))
                            self.logger.debug(f"deregistered when pressed black button: take_out_trash {current_trash_type} ({current_trash_date})")
                            self.button_black.when_pressed = None

                        self.logger.debug(f"registered when pressed black button: take_out_trash")
                        self.button_black.when_pressed = lambda current_trash_date=trash_date, current_trash_type=trash_type: take_out_trash(current_trash_date, current_trash_type)

                    trash_was_brought_in = trash_type in self.trash_brought_in and trash_date == self.trash_brought_in[trash_type]
                    trash_should_be_taken_in = trash_date.date() == current_time.date() and current_time >= notification_time_bring_in
                    if trash_should_be_taken_in and not trash_was_brought_in:
                        self.trash_type_bring_in.append(trash_type)

                        def bring_in_trash(current_trash_date: datetime, current_trash_type: TrashType):
                            self.logger.debug(f"clicked black button: take_out_trash")
                            self.led_rgb_main.color = 0, 0, 0
                            self.led_rgb_info.color = 0, 0, 0
                            self.trash_brought_in[current_trash_type] = current_trash_date
                            self.trash_type_bring_in = list(filter(lambda x: x != current_trash_type, self.trash_type_bring_in))
                            self.logger.debug(f"deregistered when pressed black button: bring_in_trash {current_trash_type} ({current_trash_date})")
                            self.button_black.when_pressed = None

                        self.logger.debug(f"registered when pressed black button: bring_in_trash")
                        self.button_black.when_pressed = lambda current_trash_date=trash_date, current_trash_type=trash_type: bring_in_trash(current_trash_date, current_trash_type)


            #await asyncio.sleep(10)  # For debugging update this to be 1!
            await asyncio.sleep(60 * 60)  # Check once every hour

    async def request_widgets(self):
        if self.current_trash_dates is not None:
            trash_dates: list[WidgetContent] = [WidgetContent(description="Trash Dates", text="")]
            count = 0
            checksum = ""
            for trash_date, trash_type in self.current_trash_dates:
                trash_date_str = trash_date.date().strftime('%d.%m.')
                trash_dates.append(WidgetContent(description=trash_date_str, text=trash_type))
                checksum += trash_date_str + trash_type
                count += 1
                if count == 7:
                    break
            change_detected = ChangeDetected(self.last_checksum_widgets != checksum)
            self.last_checksum_widgets = checksum
            return [Widget(generate_content=lambda: trash_dates)], change_detected
        else:
            return [], ChangeDetected(False)

    async def request_actions(self):
        actions: list[Action] = []
        checksum = ""
        for trash_type_take_out in self.trash_type_take_out:
            self.led_rgb_main.color = 1, 0, 0
            self.led_rgb_info.color = TRASH_COLORS.get(trash_type_take_out, (0, 0, 0))
            actions.append(Action(generate_content=lambda: ActionContent(
                ("info_white", "Take trash out", trash_type_take_out)
            )))
            checksum += trash_type_take_out + datetime.now().strftime('%d.%m')
        for trash_type_bring_in in self.trash_type_bring_in:
            self.led_rgb_main.color = 1, 1, 0
            self.led_rgb_info.color = TRASH_COLORS.get(trash_type_bring_in, (0, 0, 0))
            actions.append(Action(generate_content=lambda: ActionContent(
                ("info_white", "Bring trash in", trash_type_bring_in)
            )))
            checksum += trash_type_bring_in + datetime.now().strftime('%d.%m')
        change_detected = ChangeDetected(self.last_checksum_actions != checksum)
        self.last_checksum_actions = checksum
        return actions, change_detected
