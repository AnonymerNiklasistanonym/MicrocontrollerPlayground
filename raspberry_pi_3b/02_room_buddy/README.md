# 02_room_buddy

General purpose program that revolves around an e-paper display, 2 LEDs (status + info) and 2 buttons (red + black).
It has a plugin interface which is able to dynamically created static widgets and big actions on the display.

![Visualization breadboard (TODO)](./res/breadboard_02_room_buddy.svg)

![Visualization schema (TODO)](./res/schema_02_room_buddy.svg)

For debugging purposes the whole program can be run on another PC with a simulated display/LED output and onscreen buttons that simulate the button inputs.

```sh
# Start
CALENDAR_URL="https://api.abfall.io/?key=INSERT_CUSTOM&mode=export&idhousenumber=INSERT_CUSTOM&wastetypes=INSERT_CUSTOM&showinactive=false&type=ics" python new_main.py
# Get journal logs
journalctl SYSLOG_IDENTIFIER=room_buddy -f
```

`systemd` service description: [`.config/systemd/user/room_buddy.service`](./room_buddy.service)
