import os
import time
from machine import Pin, SPI

from sdcard import SDCard

from pins_config import (
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_CS,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_SCK,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MOSI,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MISO,
)

# On my pico the SPI device needed more voltage than the 3V3(OUT) pin could deliver
# (even though it was listed with 3.3 and 5V support)
spi = SPI(
    0,
    sck=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_SCK),
    mosi=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MOSI),
    miso=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MISO),
)
cs = Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_CS, Pin.OUT)

MICROSD_CARD_FILESYSTEM_PREFIX = const("/sd")


def delete_file(filename, prefix=None):
    try:
        os.remove(filename if prefix is None else f"{prefix}/{filename}")
        print(f"The file '{filename}' has been deleted")
    except OSError as e:
        print(f"Error deleting file '{filename}': {e}")


def file_exists(filename, prefix=None):
    try:
        stats = os.stat(filename if prefix is None else f"{prefix}/{filename}")
        convert_timestamp = lambda ts: "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            *time.localtime(ts)[:6]
        )
        size = stats[6]
        last_modified = convert_timestamp(stats[8])
        print(f"The file '{filename}' does exist ({size=} bytes, {last_modified=})")
        return True
    except OSError as e:
        print(f"The file '{filename}' does not exist: {e}")
        return False


try:
    # Initialize MicroSD card
    sd = SDCard(spi, cs)
    # Mount the filesystem
    os.mount(sd, MICROSD_CARD_FILESYSTEM_PREFIX)
    
    print("MicroSD card initialized successfully!")

    # List files
    print("Files on MicroSD card:", os.listdir(MICROSD_CARD_FILESYSTEM_PREFIX))
    
    # Write to/Create file
    try:
        with open(f"{MICROSD_CARD_FILESYSTEM_PREFIX}/test.txt", "w") as f:
            f.write("Hello, SD card!")
    except OSError:
        print(f"Error creating/writing file 'test.txt': {e}")

    # Append to/Create file
    try:
        with open(f"{MICROSD_CARD_FILESYSTEM_PREFIX}/test2.txt", "a") as f:
            f.write("Hello, SD card!")
    except OSError as e:
        print(f"Error creating/appending file 'test2.txt': {e}")
    
    # Read a file
    if file_exists("does_not_exist.txt", MICROSD_CARD_FILESYSTEM_PREFIX):
        raise RuntimeError("File exists even though it shouldn't")
    
    if file_exists("test.txt", MICROSD_CARD_FILESYSTEM_PREFIX):
        try:
            # Attempt to open the file
            with open(f"{MICROSD_CARD_FILESYSTEM_PREFIX}/test.txt", "r") as f:
                # file exists so we can read it
                content = f.read()
                print("Content of file 'test.txt':", content)
        except OSError as e:
            print(f"Error reading file 'test.txt': {e}")
        
    # Unmount the filesystem
    os.umount("/sd")

except Exception as e:
    print("Failed to initialize/read/write SD card:", e)
    
