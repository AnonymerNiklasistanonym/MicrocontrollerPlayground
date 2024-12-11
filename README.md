# MicrocontrollerPlayground

A collection of scripts used in combination with various micro controllers (and a Raspberry Pi utilizing it's GPIO pins and `systemd`).

## Setup

### Linux (e.g. Arch/Manjaro)

#### Permissions to write to Microcontrollers


```sh
# Find device
ls /dev/ttyACM*
ls /dev/ttyUSB*
# Give user write permissions:
# e.g. /dev/ttyACM0: (Arduino UNO R3)
sudo chmod a+rw /dev/ttyACM0
```

The permissions can also be done permanently by adding the current user to the `uucp` group (provides access to serial ports, USB serial devices, etc.):

```sh 
sudo usermod -a -G uucp $USER
```

## Basics

### Breadboard

A breadboard is a reusable platform for quickly building and testing electronic circuits without soldering, making it ideal for prototyping and experimenting with different circuit designs.

The outer 2 columns are vertically connected while the inner columns are connected horizontally.

![Breadboard underlying connections visualized](./res/breadboard.svg)
