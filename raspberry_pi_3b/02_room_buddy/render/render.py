from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict, Optional, NewType, NotRequired
import os
# 'pip install Pillow'
from PIL import Image, ImageDraw, ImageFont
# 'pip install cairosvg'
import cairosvg

XCoordinate = NewType('XCoordinate', int)
YCoordinate = NewType('YCoordinate', int)
Width = NewType('Width', int)
Height = NewType('Height', int)
TrashDate = NewType('TrashDate', date)
TrashType = NewType('TrashType', str)
Celsius = NewType('Celsius', float)
Percent = NewType('Percent', float)
PartsPerMillion = NewType('PartsPerMillion', float)

UpdatedImagePosition = tuple[XCoordinate, YCoordinate]
UpdatedImageArea = dict[Width, Height]
UpdatedImageAreas = list[tuple[UpdatedImagePosition, UpdatedImageArea]]


class DisplayData(TypedDict):
    trash_dates: Optional[dict[TrashDate, TrashType]]
    # [-40,+80]°C
    temperature: Optional[Celsius]
    # [0,100]%
    humidity: Optional[Percent]
    # correlates with the concentration of air pollutants such as ammonia, nitrogen, alcohol, and smoke
    # (higher resistance indicating lower gas concentration, 10 to 1.000ppm)
    air_pollution: Optional[PartsPerMillion]
    # correlates with the concentration of gases like smoke, methane, and alcohol
    # (higher resistance indicating lower gas concentration, 300 to 10.000ppm)
    gas_concentration: Optional[PartsPerMillion]


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = SCRIPT_DIR.joinpath('..', 'res')

FONT_TTF_LIST: list[Path] = [
    RES_DIR.joinpath('fonts', 'Roboto-Black.ttf'),
]
FONT_SIZE_BIG_DIVIDER = 10
FONT_SIZE_TEXT_DIVIDER = int(FONT_SIZE_BIG_DIVIDER * 1.5)
FONT_SIZE_UPDATE_DIVIDER = int(FONT_SIZE_BIG_DIVIDER * 3.5)
TEXT_SPACING_DIVIDER = int(FONT_SIZE_BIG_DIVIDER * 4)

ICON_DIR = RES_DIR.joinpath('icons')
ICON_DIR_CACHED = ICON_DIR.joinpath('cached')
ICON_NAMES: list[str] = [
    'info_white'
]

# The previous display data for comparisons
previousDisplayData: Optional[DisplayData] = None


def render_display(data: DisplayData, display_size: tuple[Width, Height]) -> tuple[Image, UpdatedImageAreas]:
    updated_areas: UpdatedImageAreas = []
    display_width, display_height = display_size
    # Create image to be displayed
    # mode "1": Grayscale, Binary image, 1-bit pixels [black (0) and white (255)]
    image = Image.new('1', display_size, 255)
    draw = ImageDraw.Draw(image)
    # setup sensor data
    sensor_data = [
        (data['temperature'], "Innentemperatur", lambda x: f"{x}°C"),
        (data['humidity'], "Luftfeuchtigkeit", lambda x: f"{x}%"),
        (data['air_pollution'], "Luftverschmutzung", lambda x: f"{x}ppm"),
        (data['gas_concentration'], "Rauch", lambda x: f"{x}ppm"),
    ]
    # setup fonts
    existing_font: Optional[ImageFont] = None
    for font in FONT_TTF_LIST:
        if font.exists():
            existing_font = font
            break
    if existing_font is None:
        raise RuntimeError(f"Could not find a supported font ({",".join(str(x) for x in FONT_TTF_LIST)})")
    font_size_big = int(display_height / FONT_SIZE_BIG_DIVIDER)
    font_size_text = int(display_height / FONT_SIZE_TEXT_DIVIDER)
    font_size_update = int(display_height / FONT_SIZE_UPDATE_DIVIDER)
    text_spacing = int(display_height / TEXT_SPACING_DIVIDER)
    font_text = ImageFont.truetype(existing_font, font_size_text)
    font_big = ImageFont.truetype(existing_font, font_size_big)
    font_update = ImageFont.truetype(existing_font, font_size_update)
    # setup images
    loaded_icons: dict[str, Path] = {}
    for icon_name in ICON_NAMES:
        original_file = ICON_DIR.joinpath(f"{icon_name}.svg")
        cached_files = [
            ICON_DIR_CACHED.joinpath(f"{icon_name}_big_{font_size_big}.png"),
        ]
        if not ICON_DIR_CACHED.exists():
            ICON_DIR_CACHED.mkdir()
        for cached_file in cached_files:
            if not original_file.exists():
                raise RuntimeError(f"Unable to find icon file {original_file}")
            if not cached_file.exists():
                with open(original_file, "rb") as svg_file:
                    print(f"cairosvg {original_file} -> {cached_file}")
                    cairosvg.svg2png(file_obj=svg_file, write_to=str(cached_file),
                                     output_width=font_size_big, output_height=font_size_big)
                if not cached_file.exists():
                    raise RuntimeError(f"File was not created {cached_file}", cached_file)

            loaded_icons[icon_name] = cached_file
    # setup other
    sorted_trash_dates = dict(sorted(data['trash_dates'].items(), key=lambda x: x[0]))
    sorted_trash_dates_grouped = {trashType: sorted([trashDate for trashDate, trashType_ in data['trash_dates'].items() if trashType_ == trashType])
                                  for trashType in set(data['trash_dates'].values())}

    # Next trash type header (black bg, white text)
    draw.rectangle((0, 0, display_width, 2 * text_spacing + font_size_big), fill=0)
    y_position_text = text_spacing
    for trash_date, trash_type in sorted_trash_dates.items():
        time_text = trash_date.strftime('%d.%m')
        if trash_date == datetime.now().date():
            time_text = "Heute"
        elif trash_date == datetime.now().date() + timedelta(days=1):
            time_text = "Morgen"
        text = f"{trash_type} ({time_text})"
        draw.text((text_spacing * 2 + font_size_big, y_position_text), text, font=font_big, fill=255)
        break

    image_to_paste = Image.open(loaded_icons['info_white'])
    image.paste(image_to_paste, (y_position_text, y_position_text))

    y_position_text += font_size_big + 2 * text_spacing
    y_position_below_header = y_position_text

    # Next trash date
    first = True
    for trash_date, trash_type in sorted_trash_dates.items():
        if first:
            first = False
            continue
        text = f"{trash_date.strftime('%d.%m')} {trash_type}"
        if y_position_text + font_size_text + 2 * text_spacing + font_size_update > display_height:
            break  # Stop, no vertical space available
        draw.text((text_spacing, y_position_text), text, font=font_text, fill=0)
        y_position_text += font_size_text + text_spacing

    # Sensors
    y_position_text = y_position_below_header
    for sensor_value, sensor_name, sensor_text_func in sensor_data:
        if sensor_value is None:
            continue
        draw.text((int(display_width * 0.5) - text_spacing, y_position_text),
                  sensor_name, font=font_text, fill=0)
        draw.text((int(display_width * 0.85) - text_spacing, y_position_text),
                  sensor_text_func(sensor_value), font=font_big, fill=0)
        y_position_text += font_size_big + text_spacing

    # Add current time as indicator of the last update
    last_update_text = datetime.now().strftime('last update: %Y-%m-%d %H:%M:%S')
    draw.text((display_width - font_size_update * (len(last_update_text) / 2),
               display_height - text_spacing - font_size_update),
              last_update_text, font=font_update, fill=0)

    return image, updated_areas
