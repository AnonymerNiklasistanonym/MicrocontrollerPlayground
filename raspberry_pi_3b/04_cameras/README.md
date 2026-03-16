# Cameras

## Hardware

- CSI Camera Module: [Raspberry Pi Camera Module 3](https://www.amazon.de/dp/B0BRY6MVXL) 30€
  - **DO NOT HOT SWAP THIS CAMERA!** Turn the Pi off and connect it, then turn it on again
- USB UVC Camera: [InnoMaker USB 2.0 UVC Camera Module](https://www.amazon.de/dp/B0FLXGJNKT) 25€

## Software

> Copy Images via SFTP:
>
> ```sh
> sftp -o PubkeyAuthentication=no -o PreferredAuthentications=password niklas@192.168.5.91
> sftp> get image.jpg 
> Fetching /home/niklas/image.jpg to image.jpg
> sftp> get photo.jpg
> Fetching /home/niklas/photo.jpg to photo.jpg
> ```

### CSI Camera Module

```sh
rpicam-still -o image.jpg -t 1
```

### USB UVC Camera

```sh
# Confirm its connected
lsusb
# Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
# Bus 001 Device 002: ID 0424:9514 Microchip Technology, Inc. (formerly SMSC) SMC9514 Hub
# Bus 001 Device 003: ID 0424:ec00 Microchip Technology, Inc. (formerly SMSC) SMSC9512/9514 Fast Ethernet Adapter
# Bus 001 Device 004: ID 0bda:5856 Realtek Semiconductor Corp. Innomaker-U20CAM-1080PD&N-S1 <-------- Perfect

# Find out where the camera is connected
v4l2-ctl --list-devices
# unicam (platform:3f801000.csi):
#         /dev/video0
#         /dev/video1
#         /dev/media3
# ...
# Innomaker-U20CAM-1080PD&N-S1: I (usb-3f980000.usb-1.4):
#         /dev/video2  <-------- Perfect
#         /dev/video3
#         /dev/media4
# ...

# Make a photo
ffmpeg -f video4linux2 -i /dev/video2 -vframes 1 photo.jpg

# Find out the resolutions/modes
v4l2-ctl --list-formats-ext -d /dev/video2
# ioctl: VIDIOC_ENUM_FMT
#         Type: Video Capture
# 
#         [0]: 'MJPG' (Motion-JPEG, compressed)
#                 Size: Discrete 640x480
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 1920x1080
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 320x240
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 352x288
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 640x480
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 800x600
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 848x480
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 960x540
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 1280x720
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 1280x800
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 640x480
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#                         Interval: Discrete 0.033s (30.000 fps)
#         [1]: 'YUYV' (YUYV 4:2:2)
#                 Size: Discrete 1280x720
#                         Interval: Discrete 0.100s (10.000 fps)
#                         Interval: Discrete 0.100s (10.000 fps)
#                 Size: Discrete 640x480
#                         Interval: Discrete 0.033s (30.000 fps)
#                 Size: Discrete 800x600
#                         Interval: Discrete 0.050s (20.000 fps)
#                 Size: Discrete 848x480
#                         Interval: Discrete 0.050s (20.000 fps)
#                 Size: Discrete 960x540
#                         Interval: Discrete 0.067s (15.000 fps)
#                 Size: Discrete 1280x720
#                         Interval: Discrete 0.100s (10.000 fps)
#                         Interval: Discrete 0.100s (10.000 fps)
#                 Size: Discrete 1280x800
#                         Interval: Discrete 0.200s (5.000 fps)
#                 Size: Discrete 1920x1080
#                         Interval: Discrete 0.200s (5.000 fps)

# Specify specific mode when capturing an image
ffmpeg -f video4linux2 -video_size 1920x1080 -i /dev/video2 -vframes 1 photo_high_res.jpg
```
