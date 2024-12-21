# Raspberry Pi Pico W

![Pinout](./res/pico-w-pinout.svg)

## Tutorials

- Micropython setup and Wifi server tutorial: https://projects.raspberrypi.org/en/projects/get-started-pico-w/0
- Micropython basic GPIO pin programming: https://www.upesy.com/blogs/tutorials/micropython-raspberry-pi-pico-gpio-pins-usage#

## Firmware Setup

1. Activate UF2 bootloader mode (the Raspberry Pi Pico W shows up as a USB drive/mass storage when connecting it to a PC)
   - When getting a Raspberry Pi Pico W (or WH) it initially already starts in this mode
   - It can be manually activated at any time by holding down the visible (BOOTSEL) button down while connecting it to a PC

### Micropython

1. Download
   1. Download the `.uf2` firmware (e.g. from [micropython.org](https://micropython.org/download/RPI_PICO/)) and drag and drop it into the Raspberry Pi Pico W USB drive/mass storage
   2. The USB drive/mass storage entry will quickly disappear and the Raspberry Pi Pico W will automatically reset and be ready to program

To verify/start writing program open Thonny.
The Raspberry Pi Pico W should show up in the right side bar as a directory and in the interpreter shell at the bottom (e.g. `MicroPython v1.24.1 on 2024-11-29; Raspberry Pi Pico with RP2040`).

The text in the bottom right-hand corner of the Thonny editor indicates the Python (Interpreter) that is being used.
If it does not say `MicroPython (Raspberry Pi Pico)` click on the text and select it from the options list (`Configure Interpreter`, `Interpreter`, `Which kind of interpreter should Thonney use for running your code?`).

## TODO

- [ ] What is Micropython
  - [ ] what libraries/code can be used
  - [ ] where are the limits (size, functions, multiple threads, ...)
- [ ] Thonny workflow
- [ ] basic LED/Button example
