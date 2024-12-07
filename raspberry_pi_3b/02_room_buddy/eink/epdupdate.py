from PIL.Image import Image
import epd1in54


def update_full(image: Image, x=0, y=0):
    # initialize display (full update)
    epd = epd1in54.EPD()
    epd.init(epd.lut_full_update if x == 0 and y == 0 else epd.lut_partial_update)
    # clear current (old) frame memory
    epd.clear_frame_memory(0xFF)
    # set new frame memory
    epd.set_frame_memory(image, 0, 0)
    # display frame
    epd.display_frame()


def update_partial(image: Image):
    # initialize display (full update)
    epd = epd1in54.EPD()
    epd.init(epd.lut_partial_update)
    # clear current (old) frame memory
    epd.clear_frame_memory(0xFF)
    # set new frame memory
    epd.set_frame_memory(image, 0, 0)
    # display frame
    epd.display_frame()
