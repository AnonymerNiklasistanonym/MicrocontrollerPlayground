# Raspberry Pi Zero 2 W

These are instructions on how to setup the Raspberry Pi Zero W to function like a Arduino (e.g. upload a program, start program at boot).

The pins and most of the setup of services are the same as the [Raspberry Pi (3b)](../raspberry_pi_3b/).

## Setup

(Check the [Raspberry Pi (3b)](../raspberry_pi_3b/) instructions for more details)

1. Start `rpi-imager` and select the formatted microSD Card and *Raspberry Pi OS (64-Bit)*
   1. Set user name and password (e.g. `pi` as user name)
   2. Add Wifi network name and password
   3. Set hostname (e.g. `raspberrypi2024.local` for easy SSH access)
   4. Enable SSH using password
2. **MANUAL STEPS** (since apparently it is not done automatically)
   1. Go to the *boot-fs* partition of the microSD card
   2. Create an empty text file called `ssh` to enable SSH functionality
   3. Create a text file called `wpa_supplicant.conf` to auto connect to WLan with the following content (**REPLACE WITH YOUR COUNTRY AND WIFI NETWORK PASSWORD/NAME**)

      ```text
      country=DE
      ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
      update_config=1
      network={
      scan_ssid=1
      ssid="YOUR_WIFI_NAME"
      psk="YOUR_WIFI_PASSWORD"
      }
      ```

3. Plug the microSD Card into the Raspberry Pi Zero 2 W and connect it to a power supply
4. Connect to the Raspberry Pi via SSH (**be aware that the Raspberry Pi needs a minute to power up and connect the network/WLan before you can connect to it!**)
   1. Hostname:
      1. When a custom hostname was set in the `rpi-imager` step running `ssh [username]@[hostname].local` will connect to the Raspberry Pi without knowing it's IP address (e.g. `ssh pi@raspberrypi2024.local`)
   2. IP address:
      1. Check your router to determine the IP address of it (e.g. `192.168.2.157`)
      2. Then run `ssh [username]@[IP address]` on your computer to connect to it using the previously set password (e.g. `ssh pi@192.168.2.157`)
5. Disable features for only headless use
   1. Graphic user interface
      1. `sudo raspi-config`
      2. Select `1 System options`
      3. Select `5) Boot / Auto Login`
      4. Select `B1 console`
      5. Optionally remove the graphical user interface: `sudo apt remove --purge pi-greeter lightdm && sudo apt autoremove`
   2. Disable printer service
      1. `sudo systemctl stop cups`
      2. `sudo systemctl disable cups`
   3. Disable color service
      1. `sudo systemctl stop colord`
      2. `sudo systemctl disable colord`
   4. Disable Bluetooth
      1. `sudo systemctl stop bluetooth`
      2. `sudo systemctl disable bluetooth`
