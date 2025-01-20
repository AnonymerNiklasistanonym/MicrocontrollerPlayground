from datetime import date
from pathlib import Path
from dataclasses import dataclass, field
import os
from typing import Callable, Optional, NewType

# requires 'qrcode'
import qrcode
# requires 'Pillow'
from PIL import Image, ImageDraw, ImageFont
# requires 'cairosvg'
import cairosvg


Width = NewType('Width', int)
Height = NewType('Height', int)
ActionContentDescription = NewType('Action Description', str)
ActionContentText = NewType('Action Text', str)
ActionContentIcon = NewType('Action Icon', str)
ActionContent = tuple[Optional[ActionContentIcon], Optional[ActionContentDescription], ActionContentText]


@dataclass
class Action:
    generate_content: Callable[[], ActionContent] = field(metadata={"description": "A description of the action"})
    date: Optional[date] = field(default=None, metadata={"description": "The date when the action occurs"})
    on_select: Optional[Callable[[], None]] = field(default=None, metadata={"description": "Callback on selection"})
    on_select_alt: Optional[Callable[[], None]] = field(default=None, metadata={"description": "Callback on selection "
                                                                                               "using the alt button"})

@dataclass
class WidgetContent:
    text: str = field()
    description: Optional[str] = field(default=None)
    images: Optional[list[Image]] = field(default=None)

@dataclass
class Widget:
    generate_content: Callable[[], list[WidgetContent]] = field(metadata={"description": "Generates content to render"})


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = SCRIPT_DIR.joinpath('..', '..', 'res')

FONT_TTF_LIST: list[Path] = [
    RES_DIR.joinpath('fonts', 'Roboto-Black.ttf'),
]
FONT_SIZE_BIG_DIVIDER = 14
FONT_SIZE_TEXT_DIVIDER = int(FONT_SIZE_BIG_DIVIDER * 1.4)
FONT_SIZE_UPDATE_DIVIDER = int(FONT_SIZE_BIG_DIVIDER * 3.5)
TEXT_SPACING_DIVIDER = 4

ICON_DIR = RES_DIR.joinpath('icons')
ICON_DIR_CACHED = ICON_DIR.joinpath('cached')
ICON_NAMES: list[str] = [
    'info_white'
]

COLOR_WHITE = 255
COLOR_BLACK = 0
PILLOW_IMAGE_MODE_GRAYSCALE_BINARY = "1"
"""Pillow image mode: Grayscale, Binary image, 1-bit pixels [black (0) and white (255)]"""

ACTION_SPACING = 2
WIDGET_SPACING = 2


def get_text_dimensions(text_string, font) -> tuple[int, int]:
    if text_string == "":
        return 0, 0
    ascent, descent = font.getmetrics()
    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent
    return text_width, text_height


def render_display_bw(actions: list[Action], widgets: list[Widget], display_resolution: tuple[Width, Height]) -> Image:
    """
    Create image (black and white)

    +---------------+---------------+
    | ACTION 1 [OK, ALT]            |
    | ACTION 2 [OK, ALT]            | ACTIONS
    | ...                           |
    +---------------+---------------+
    | WIDGET 1      | WIDGET 4      |
    | WIDGET 2      | ...           | WIDGETS
    | WIDGET 3      |               |
    +---------------+---------------+

    :param actions: The actions to be rendered
    :param widgets: The widgets to be rendered
    :param display_resolution: The resolution of the display (in pixels)
    :return: The generated image
    """
    display_width, display_height = display_resolution

    # setup drawable image object
    image = Image.new(PILLOW_IMAGE_MODE_GRAYSCALE_BINARY, display_resolution, COLOR_WHITE)
    draw = ImageDraw.Draw(image)

    # setup fonts
    existing_font: Optional[ImageFont] = None
    for font in FONT_TTF_LIST:
        if font.exists():
            existing_font = font
            break
    if existing_font is None:
        raise RuntimeError(f"Could not find a supported font ({','.join(str(x) for x in FONT_TTF_LIST)})")
    calculated_font_sizes = {
        "big": int(display_height / FONT_SIZE_BIG_DIVIDER),
        "text": int(display_height / FONT_SIZE_TEXT_DIVIDER),
        "update": int(display_height / FONT_SIZE_UPDATE_DIVIDER),
    }
    calculated_font_spacings = {font_size_name: int(font_size / TEXT_SPACING_DIVIDER) for font_size_name, font_size in calculated_font_sizes.items()}
    loaded_fonts = {font_size_name: ImageFont.truetype(existing_font, font_size) for font_size_name, font_size in calculated_font_sizes.items()}

    # setup images
    loaded_icons: dict[str, dict[str, Path]] = {}
    if not ICON_DIR_CACHED.exists():
        ICON_DIR_CACHED.mkdir()
    for icon_name in ICON_NAMES:
        original_icon_file = ICON_DIR.joinpath(f"{icon_name}.svg")
        for font_size_name, font_size in calculated_font_sizes.items():
            cached_icon_file = ICON_DIR_CACHED.joinpath(f"{icon_name}_{font_size}.png")
            if not original_icon_file.exists():
                raise RuntimeError(f"Could not find {original_icon_file=}")
            if not cached_icon_file.exists():
                with open(original_icon_file, "rb") as svg_file:
                    print(f"cairosvg {original_icon_file=} -> {cached_icon_file=}")
                    cairosvg.svg2png(file_obj=svg_file, write_to=str(cached_icon_file),
                                     output_width=font_size, output_height=font_size)
            if icon_name not in loaded_icons:
                loaded_icons[icon_name] = {}
            loaded_icons[icon_name][font_size_name] = cached_icon_file

    # draw actions
    y_position = 0
    for action in actions:
        action_height = 2 * calculated_font_spacings["big"] + calculated_font_sizes["big"]
        if y_position + action_height + ACTION_SPACING > display_height / 4:
            break
        action_icon, action_description, action_text = action.generate_content()
        # draw action bg
        draw.rectangle((0, y_position, display_width, y_position + action_height),
                       fill=COLOR_BLACK)
        x_position_action_content = calculated_font_spacings["big"]
        y_position_action_content = y_position + calculated_font_spacings["big"]
        # draw action icon
        if action_icon is not None and action_icon in loaded_icons:
            image_action_icon = Image.open(loaded_icons[action_icon]["big"])
            image.paste(image_action_icon, (x_position_action_content, y_position_action_content))
            x_position_action_content += calculated_font_spacings["big"] + calculated_font_sizes["big"]
        # draw action description
        if action_description is not None:
            text_width_big, text_height_big = get_text_dimensions(action_text, loaded_fonts["big"])
            text_width, text_height = get_text_dimensions(action_description, loaded_fonts["text"])
            draw.text((x_position_action_content, y_position_action_content + text_height_big - text_height),
                      text=action_description, fill=COLOR_WHITE, font=loaded_fonts["text"])
            x_position_action_content += (calculated_font_spacings["text"] * 2 + text_width)
        # draw action text
        draw.text((x_position_action_content, y_position_action_content),
                  text=action_text, fill=COLOR_WHITE, font=loaded_fonts["big"])
        y_position += action_height + ACTION_SPACING

    # draw widgets
    y_position = display_height / 4
    column = 0
    for widget in widgets:
        widget_content = widget.generate_content()
        widget_height = ((calculated_font_spacings["big"] * len(widget_content) + 1) +
                         (calculated_font_sizes["big"] * len(widget_content)))
        # todo fix the height calculation
        for content in widget_content:
            if content.images is not None and len(content.images) > 0:
                widget_height += max([img.height for img in content.images])

        if y_position + widget_height + WIDGET_SPACING > display_height:
            if column == 1 or display_height / 2 + widget_height + WIDGET_SPACING > display_height:
                break
            column = 1
            y_position = display_height / 4
        # draw widget content
        x_position_widget_content = calculated_font_spacings["big"] if column == 0 else calculated_font_spacings["big"] + int(display_width / 2)
        y_position_widget_content = y_position + calculated_font_spacings["big"]
        for content in widget_content:
            # draw widget description
            x_position_widget_content_element = x_position_widget_content
            if content.description is not None:
                text_width_big, text_height_big = get_text_dimensions(
                    "A" + content.text, loaded_fonts["big"]
                )
                text_width, text_height = get_text_dimensions(content.description, loaded_fonts["text"])
                draw.text((x_position_widget_content_element, y_position_widget_content + text_height_big - text_height + 4),
                          text=content.description, fill=COLOR_BLACK, font=loaded_fonts["text"])
                x_position_widget_content_element += (calculated_font_spacings["text"] * 2 + text_width)
            # draw widget text
            draw.text((x_position_widget_content_element, y_position_widget_content),
                      text=content.text, fill=COLOR_BLACK, font=loaded_fonts["big"])
            y_position_widget_content += calculated_font_spacings["big"] + calculated_font_sizes["big"]
            if content.images is not None and len(content.images) > 0:
                for content_image in content.images:
                    image.paste(content_image, (x_position_widget_content_element, int(y_position_widget_content)))
                    x_position_widget_content_element += content_image.width
        y_position += widget_height + WIDGET_SPACING

    return image

def create_qr_code(content: str, size: int) -> Image:
    data = content
    desired_size = size
    # Calculate appropriate box_size and border
    box_size = desired_size // 41  # Approximation (maximum QR size is 41x41 for version 1)
    border = 4  # Standard minimum border size
    qr = qrcode.QRCode(
        version=1,  # Size of QR code (higher version = more data capacity)
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border
    )
    # Add data and create image
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    # Ensure exact dimensions
    img = img.resize((desired_size, desired_size))
    new_img = Image.new("RGB", img.size, "white")
    new_img.paste(img, (0, 0))
    return new_img