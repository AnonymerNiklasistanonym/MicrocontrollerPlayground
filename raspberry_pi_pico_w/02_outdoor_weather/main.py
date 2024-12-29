import network
import socket
import time
import os
import ntptime
import ujson
from machine import I2C, SPI, Pin, Timer, reset, WDT
from dht import DHT22

# Local libraries

from bmp280 import *
from sdcard import SDCard

# Constants

from pins_config import (
    GPIO_PIN_INPUT_DHT22,
    GPIO_PIN_I2C_BMP280_SDA,
    GPIO_PIN_I2C_BMP280_SCL,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_CS,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_SCK,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MOSI,
    GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MISO,
)
from wifi_config import SSID, PASSWORD
from http_helper import (
    HTTP_CONTENT_TYPE_CSS,
    HTTP_CONTENT_TYPE_JS,
    HTTP_CONTENT_TYPE_JSON,
    HTTP_CONTENT_TYPE_TEXT,
    HTTP_STATUS_NOT_MODIFIED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_FOUND,
)

# Local files

from csv_helper import append_to_csv
from free_storage import df, ramf, sdf, convert_to_human_readable_str
from timestamp import get_iso_timestamp
from time_difference import get_time_difference
from log_helper import (
    Logger,
    LogHandlerConsole,
    LogHandlerFile,
)
from print_history import PrintHistory, PrintHistoryLogHandler
from html_helper import (
    generate_html,
    generate_html_list,
    generate_html_table,
    generate_html_button,
)
from i2c_scan import i2c_scan
from http_helper import (
    generate_http_response,
    generate_etag,
)

# Script constants

# IMPORTANT: IF THIS IS FALSE THE DEVICE AUTO RESTARTS!
DEBUG = const(False)

PROGRAM_NAME = const("outdoor_weather")
PROGRAM_VERSION = const("v0.2.6")
MICROSD_CARD_FILESYSTEM_PREFIX = const("/sd")
AUTOMATIC_DEVICE_RESTART = const(not DEBUG)

BMP280_FREQUENCY_I2C = const(100000)  # Hertz (default 100kHz higher, fast mode 400kHz)
BMP280_FREQUENCY = const(157)  # Hertz (WARNING: every 6.4ms!)
BMP280_TOLERANCE_AIR_PRESSURE = const(1 * 100)  # Pascal (Pascal * 100 to convert from Hectopascal)
_BMP280_RANGE_AIR_PRESSURE_MIN = const(300 * 100)
_BMP280_RANGE_AIR_PRESSURE_MAX = const(1100 * 100)
BMP280_RANGE_AIR_PRESSURE = (_BMP280_RANGE_AIR_PRESSURE_MIN, _BMP280_RANGE_AIR_PRESSURE_MAX)
BMP280_TOLERANCE_TEMPERATURE = const(0.5)  # Degrees Celsius
_BMP280_RANGE_TEMPERATURE_MIN = const(-40)
_BMP280_RANGE_TEMPERATURE_MAX = const(85)
BMP280_RANGE_TEMPERATURE = (_BMP280_RANGE_TEMPERATURE_MIN, _BMP280_RANGE_TEMPERATURE_MAX)

DHT22_FREQUENCY = const(0.5)  # Hertz
DHT22_TOLERANCE_TEMPERATURE = const(0.5)  # Degrees Celsius
_DHT22_RANGE_TEMPERATURE_MIN = const(-40)
_DHT22_RANGE_TEMPERATURE_MAX = const(80)
DHT22_RANGE_TEMPERATURE = (_DHT22_RANGE_TEMPERATURE_MIN, _DHT22_RANGE_TEMPERATURE_MAX)
DHT22_TOLERANCE_RELATIVE_HUMIDITY = const(2.0)  # Percent
_DHT22_RANGE_RELATIVE_HUMIDITY_MIN = const(0)
_DHT22_RANGE_RELATIVE_HUMIDITY_MAX = const(100)
DHT22_RANGE_RELATIVE_HUMIDITY = (_DHT22_RANGE_RELATIVE_HUMIDITY_MIN, _DHT22_RANGE_RELATIVE_HUMIDITY_MAX)

SENSOR_ID_BMP280 = const("bmp280")
SENSOR_ID_DHT22 = const("dht22")

MEASUREMENT_ID_BMP280_TEMPERATURE = const("bmp280_temperature_celsius")
MEASUREMENT_ID_BMP280_AIR_PRESSURE = const("bmp280_air_pressure_pa")

MEASUREMENT_ID_DHT22_TEMPERATURE = const("dht22_temperature_celsius")
MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY = const("dht22_relative_humidity_percent")

UNIT_TEMPERATURE_CELSIUS = const("°C")
UNIT_RELATIVE_HUMIDITY_PERCENT = const("%")
UNIT_AIR_PRESSURE_PA = const("Pa")

WEB_SERVER_HEALTH_CHECK_TIME_DIFF_S = const(10)

# The amount of values until a sensor is stabilized
SENSOR_STABILIZE_COUNT = const(100)
# The amount of values to keep in the buffers
BUFFER_COUNT = const(10)

# Script global variables

# Sensor stabilization
sensor_stabilized = {  # Stabilized
    SENSOR_ID_BMP280: False,
    SENSOR_ID_DHT22: False,
}
sensor_last_values = {  # Last value, # of no changes
    MEASUREMENT_ID_DHT22_TEMPERATURE: (None, SENSOR_STABILIZE_COUNT),
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: (None, SENSOR_STABILIZE_COUNT),
    MEASUREMENT_ID_BMP280_TEMPERATURE: (None, SENSOR_STABILIZE_COUNT),
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: (None, SENSOR_STABILIZE_COUNT),
}

# Sensor information
sensor_unit = {  # Name of measured value unit
    MEASUREMENT_ID_DHT22_TEMPERATURE: UNIT_TEMPERATURE_CELSIUS,
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: UNIT_RELATIVE_HUMIDITY_PERCENT,
    MEASUREMENT_ID_BMP280_TEMPERATURE: UNIT_TEMPERATURE_CELSIUS,
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: UNIT_AIR_PRESSURE_PA,
}
sensor_tolerances = {  # min, max
    MEASUREMENT_ID_DHT22_TEMPERATURE: DHT22_TOLERANCE_TEMPERATURE,
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: DHT22_TOLERANCE_RELATIVE_HUMIDITY,
    MEASUREMENT_ID_BMP280_TEMPERATURE: BMP280_TOLERANCE_TEMPERATURE,
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: BMP280_TOLERANCE_AIR_PRESSURE,
}
sensor_ranges = {  # min, max
    MEASUREMENT_ID_DHT22_TEMPERATURE: DHT22_RANGE_TEMPERATURE,
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: DHT22_RANGE_RELATIVE_HUMIDITY,
    MEASUREMENT_ID_BMP280_TEMPERATURE: BMP280_RANGE_TEMPERATURE,
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: BMP280_RANGE_AIR_PRESSURE,
}

# Store measurements as separate lists for temperature and humidity
buffer_readings = {  # (value: number, iso timestamp: str)
    MEASUREMENT_ID_DHT22_TEMPERATURE: [],
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: [],
    MEASUREMENT_ID_BMP280_TEMPERATURE: [],
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: [],
}
counter_readings = {  # good readings, bad readings
    MEASUREMENT_ID_DHT22_TEMPERATURE: {"good": 0, "bad": 0},
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: {"good": 0, "bad": 0},
    MEASUREMENT_ID_BMP280_TEMPERATURE: {"good": 0, "bad": 0},
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: {"good": 0, "bad": 0},
    SENSOR_ID_DHT22: {"good": 0},
    SENSOR_ID_BMP280: {"good": 0},
}

# Track recent logs
print_history_instance = PrintHistory(max_size=BUFFER_COUNT)
print_history_handler = PrintHistoryLogHandler(print_history_instance)

# Configure the logger
logger = Logger(name=PROGRAM_NAME, level="DEBUG")
if DEBUG:
    console_handler = LogHandlerConsole()
    logger.addHandler(console_handler)
file_handler = LogHandlerFile(f"{MICROSD_CARD_FILESYSTEM_PREFIX}/logs.log")
logger.addHandler(file_handler)
logger.addHandler(print_history_handler)
    

# Track uptime
time_init = time.time()

# Optimize Etag calculation
current_etag = None
update_etag = True

# Track the last time the server was active
last_server_activity = time.ticks_ms()


# SENSORS/DEVICES SHOULD BE INITIALIZED OUTSIDE OF THE MAIN METHOD!

# MicroSD Card Adapter
microsd_card_adapter_spi = SPI(
    0,
    sck=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_SCK),
    mosi=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MOSI),
    miso=Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_MISO),
)

def mount_sdcard():
    try:
        os.unmount(MICROSD_CARD_FILESYSTEM_PREFIX)
    except Exception as e:
        logger.warning("Could not unmount MicroSD Card on", MICROSD_CARD_FILESYSTEM_PREFIX)
    try:
        sd = SDCard(microsd_card_adapter_spi, Pin(GPIO_PIN_SPI_MICROSD_CARD_ADAPTER_CS))
        os.mount(sd, MICROSD_CARD_FILESYSTEM_PREFIX)
        logger.info("Successfully initialized/mounted MicroSD Card to", MICROSD_CARD_FILESYSTEM_PREFIX)
    except Exception as e:
        logger.error("Failed to initialize/mount SD card:", e)

mount_sdcard()

# Onboard-LED
led_onboard = Pin("LED", Pin.OUT)

# DHT22
dht22_sensor = DHT22(Pin(GPIO_PIN_INPUT_DHT22))

# BMP280
bmp280_sensor_i2c = I2C(
    0,
    sda=Pin(GPIO_PIN_I2C_BMP280_SDA),
    scl=Pin(GPIO_PIN_I2C_BMP280_SCL),
    freq=BMP280_FREQUENCY_I2C,
)
i2c_scan(bmp280_sensor_i2c, logger.debug)
bmp280_sensor = BMP280(bmp280_sensor_i2c)


# Watchdog timer that restarts the device if it's not getting fed when the timeout is reached
if AUTOMATIC_DEVICE_RESTART:
    wdt = WDT(timeout=1000 * 8)  # in milliseconds


def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    logger.info("Connecting to WiFi...")
    while not wlan.isconnected():
        logger.debug("...")
        led_onboard.on()
        time.sleep(0.5)
        led_onboard.off()
        time.sleep(0.5)
    logger.info("Connected to WiFi:", wlan.ifconfig())
    # TODO Doesn't work
    # try:
    #    wlan.config("raspberrypicow2024")
    #    logger.info(f"hostname set to '{hostname}.local'")
    # except Exception as e:
    #    logger.error(f"Failed to set hostname: {e}")
    return wlan.ifconfig()[0]


def sync_time():
    while True:
        try:
            previous_time = time.localtime()
            ntptime.settime()
            logger.info(
                f"Time synchronized with NTP server. Previous time: {previous_time}, New time: {time.localtime()}"
            )
            break
        except Exception as e:
            # Log the error
            logger.error(f"Failed to sync time: {e}")
            # Wait for 5 seconds before retrying
            time.sleep(5)


def read_sensor(timer, sensor_id):
    global sensor_stabilized
    global sensor_last_values
    global buffer_readings
    global counter_readings
    global update_etag

    try:
        sensor_measurements = []
        timestamp = get_iso_timestamp()

        if sensor_id == SENSOR_ID_BMP280 and bmp280_sensor is not None:
            temp = bmp280_sensor.temperature
            pressure = bmp280_sensor.pressure

            sensor_measurements = [
                (temp, MEASUREMENT_ID_BMP280_TEMPERATURE),
                (pressure, MEASUREMENT_ID_BMP280_AIR_PRESSURE),
            ]
        elif sensor_id == SENSOR_ID_DHT22 and dht22_sensor is not None:
            dht22_sensor.measure()
            temp = dht22_sensor.temperature()
            humidity = dht22_sensor.humidity()

            sensor_measurements = [
                (temp, MEASUREMENT_ID_DHT22_TEMPERATURE),
                (humidity, MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY),
            ]
        else:
            raise RuntimeError(
                "Unknown {sensor_id=} or sensor not found {dht22=}/{bmp280=}"
            )

        counter_readings[sensor_id]["good"] += 1

        if not sensor_stabilized[sensor_id]:
            changes_detected = False
            for value, measurement_id in sensor_measurements:
                sensor_last_value, count = sensor_last_values[measurement_id]
                sensor_tolerance = sensor_tolerances[measurement_id]
                if sensor_last_value is None:
                    sensor_last_values[measurement_id] = value, count
                    changes_detected = True
                    logger.debug(
                        f"[{measurement_id}] sensor not stabilized: missing last_value"
                    )
                elif abs(value - sensor_last_value) > sensor_tolerance:
                    sensor_last_values[measurement_id] = (
                        value,
                        SENSOR_STABILIZE_COUNT,
                    )
                    changes_detected = True
                    logger.debug(
                        f"[{measurement_id}] sensor not stabilized: detected change outside of tolerances"
                    )
                elif count != 0:
                    changes_detected = True
                    logger.debug(
                        f"[{measurement_id}] sensor not stabilized: detected no change but wait {count} more times"
                    )
                    sensor_last_values[measurement_id] = value, count - 1
                else:
                    logger.info(
                        f"[{measurement_id}] sensor partly stabilized: detected no change"
                    )
            if not changes_detected:
                logger.info(f"[{sensor_id}] sensor stabilized: no changes detected")
                sensor_stabilized[sensor_id] = True

        for value, measurement_id in sensor_measurements:
            unit = sensor_unit[measurement_id]
            buffer = buffer_readings[measurement_id]
            sensor_last_values[measurement_id] = (
                value,
                sensor_last_values[measurement_id][1],
            )
            last_value = buffer[-1][0] if len(buffer) > 0 else None
            sensor_tolerance = sensor_tolerances[measurement_id]
            change_detected = (
                abs(value - last_value) > sensor_tolerance
                if last_value is not None
                else True
            )
            min_value, max_value = sensor_ranges[measurement_id]
            within_range = value >= min_value and value <= max_value

            try:
                if (
                    abs(value - last_value) > 0
                    if last_value is not None
                    else True
                ):
                    append_to_csv(
                        f"data_raw_{measurement_id}.csv",
                        [unit, "Timestamp"],
                        [[value, timestamp]],
                        file_path_prefix=MICROSD_CARD_FILESYSTEM_PREFIX
                    )
            except OSError as e:
                logger.error(
                    f"[{measurement_id}] Unable to write data to CSV file: data_raw_{measurement_id}.csv ({e})"
                )

            if change_detected and within_range and sensor_stabilized[sensor_id]:
                logger.debug(
                    f"[{measurement_id}] Recorded: {value}{unit} at {timestamp}"
                )
                buffer.append([value, timestamp])
                if len(buffer) > BUFFER_COUNT:
                    buffer.pop(0)
                update_etag = True

                try:
                    append_to_csv(
                        f"data_{measurement_id}.csv",
                        [unit, "Timestamp"],
                        [[value, timestamp]],
                        file_path_prefix=MICROSD_CARD_FILESYSTEM_PREFIX
                    )
                except OSError as e:
                    logger.error(
                        f"[{measurement_id}] Unable to write data to CSV file: data_{measurement_id}.csv ({e})"
                    )
            else:
                reason = f"not within tolerance {sensor_tolerance}{unit}"
                if not within_range:
                    reason = (
                        f"value not within range [{min_value}{unit},{max_value}{unit}]"
                    )
                    counter_readings[measurement_id]["bad"] += 1
                elif not sensor_stabilized[sensor_id]:
                    reason = f"sensor stabilization ongoing"

                logger.debug(
                    f"[{measurement_id}] Skipped: current {value}{unit} ({reason})"
                )

            if within_range and sensor_stabilized[sensor_id]:
                counter_readings[measurement_id]["good"] += 1

    except Exception as e:
        logger.error(f"[{sensor_id}] Error reading sensor:", e)
        if e in counter_readings[sensor_id]:
            counter_readings[sensor_id][e] += 1
        else:
            counter_readings[sensor_id][e] = 1


def read_dht22(timer):
    read_sensor(timer, SENSOR_ID_DHT22)


def read_bmp280(timer):
    read_sensor(timer, SENSOR_ID_BMP280)


def restart_bmp280(timer):
    global bmp280_sensor_i2c
    global bmp280_sensor

    logger.debug("Restart BMP280")
    bmp280_sensor_i2c = I2C(
        0,
        sda=Pin(GPIO_PIN_I2C_BMP280_SDA),
        scl=Pin(GPIO_PIN_I2C_BMP280_SCL),
        freq=BMP280_FREQUENCY_I2C,
    )
    i2c_scan(bmp280_sensor_i2c, logger.debug)
    bmp280_sensor = BMP280(bmp280_sensor_i2c)


def render_dashboard_html():
    api = [
        ("Measurements", "/json_measurements"),
    ]
    routes = [
        ("Info", "/info"),
        ("Data", "/data"),
        ("Logs", "/logs"),
        ("Readings", "/readings"),
    ]
    actions = [
        ("Reset", "/reset"),
        ("Time sync", "/sync_time"),
        ("Remount SDCard", "/remount_sdcard"),
        ("Restart BMP280 sensor", "/restart_bmp280"),
    ]

    html = f"<h1>Dashboard</h1>"
    html += f"<h2>API</h2>"
    for name, url in api:
        html += generate_html_button(name, url)
    html += f"<h2>Routes</h2>"
    for name, url in routes:
        html += generate_html_button(name, url)
    html += f"<h2>Actions</h2>"
    for name, url in actions:
        html += generate_html_button(name, url)

    return generate_html(
        "Dashboard",
        html,
        css_files=["/content_html"],
    )


def render_dynamic_data_html() -> str:
    return generate_html(
        "Loading...",
        '<h1 id="title">Loading...</h1><button id="loadButton" disabled>Loading...</button><button id="refreshButton" disabled>Refresh</button><div id="content"></div>',
        css_files=["/content_html"],
        js_files=["/content_html_dynamic_data"],
    )


def generate_json_logs():
    return ujson.dumps(
        {
            "title": "Logs",
            "sections": [
                {
                    "title": "Recent Logs",
                    "data": [["Message", "Timestamp"]] + [[message, timestamp] for message, timestamp in print_history_instance.get_history()]
                }
            ],
        }
    )


def generate_json_data():
    return ujson.dumps(
        {
            "title": "Data",
            "sections": [
                {
                    "title": f"{measurement_id} ({sensor_last_values[measurement_id][0]}{sensor_unit[measurement_id]})",
                    "data": [[sensor_unit[measurement_id], "Timestamp"]] + [[value, timestamp] for value, timestamp in values]
                }
                for measurement_id, values in buffer_readings.items()
            ],
        }
    )


def generate_json_readings():
    return ujson.dumps(
        {
            "title": "Readings",
            "sections": [
                {
                    "title": title,
                    "data": values
                }
                for title, values in counter_readings.items()
            ],
        }
    )


def generate_json_info():

    file_space_f, file_space_t = df()

    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    
    return ujson.dumps(
        {
            "title": "Info",
            "sections": [
                {
                    "title": "Free Storage",
                    "data": {
                        "Free file space": convert_to_human_readable_str(file_space_f, T=848 * 1024, unit_name="KB"),
                        "Free RAM space": convert_to_human_readable_str(*ramf(), unit_name="KB"),
                        "Free MicroSD storage space": convert_to_human_readable_str(*sdf(MICROSD_CARD_FILESYSTEM_PREFIX), unit_name="GB"), 
                    }
                },
                {
                    "title": "Network",
                    "data": {
                        "Device name in network": ap.config('essid'),
                        "Network name": sta.config('essid'),
                    }
                },
                {
                    "title": "Misc",
                    "data": {
                        "Version": PROGRAM_VERSION,
                        "OS information":  dict(zip(['sysname', 'nodename', 'release', 'version', 'machine'], os.uname())),
                        "Uptime": dict(zip(['days', 'hours', 'minutes', 'seconds'], get_time_difference(time_init))),
                        "Current time": get_iso_timestamp(),
                    }
                }
            ],
        }
    )


def handle_web_request(socket):
    global time_init
    global update_etag
    global current_etag
    global last_server_activity

    cl, addr = socket.accept()
    logger.debug(
        "Client connected from",
        addr,
        convert_to_human_readable_str(*ramf(), unit_name="KB", name="Free RAM space"),
    )
    try:
        start_time = time.ticks_ms()
        request = cl.recv(1024).decode("utf-8")
        logger.debug(request)
        send_file_contents = []
        if not request:
            # Client has closed the connection
            return
        elif "GET /json_measurements" in request:
            if update_etag:
                current_etag = generate_etag(buffer_readings)
                update_etag = False
            serve_data = True
            # Catch ETag entries from the request header if request is conditional
            if "If-None-Match" in request:
                etag_header = (
                    request.split("If-None-Match: ")[1]
                    .split("\r\n")[0]
                    .strip()
                    .strip('"')
                )
                logger.debug(
                    f"Found {etag_header=} ({current_etag=}, {etag_header == current_etag=})"
                )
                # If no etag change exist send not modified
                if etag_header == current_etag:
                    response = generate_http_response(
                        None, status=HTTP_STATUS_NOT_MODIFIED
                    )
                    serve_data = False
            if serve_data:
                # Create JSON response with separate temperature and humidity lists
                json_str = ujson.dumps(
                    {
                        sensor: [
                            {"value": value, "timestamp": timestamp}
                            for value, timestamp in readings
                        ]
                        for sensor, readings in buffer_readings.items()
                    }
                )
                response = generate_http_response(
                    json_str, content_type=HTTP_CONTENT_TYPE_JSON, etag=current_etag
                )
        elif "GET /dashboard" in request:
            response = generate_http_response(render_dashboard_html(), maxAge=60 * 60 * 24)
        elif "GET /dynamic_data" in request:
            response = generate_http_response(render_dynamic_data_html(), maxAge=60 * 60 * 24)
        elif "GET /content_html_dynamic_data.js" in request:
            response = generate_http_response("", content_type=HTTP_CONTENT_TYPE_JS, maxAge=60 * 60 * 24)
            send_file_contents.append("/content_html_dynamic_data.js")
        elif "GET /content_html.css" in request:
            response = generate_http_response("", content_type=HTTP_CONTENT_TYPE_CSS, maxAge=60 * 60 * 24)
            send_file_contents.append("/content_html.css")
        elif "GET /info" in request:
            response = generate_http_response(None, status=HTTP_STATUS_FOUND, location=f"/dynamic_data?endpoint=json_info")
        elif "GET /json_info" in request:
            response = generate_http_response(generate_json_info(), content_type=HTTP_CONTENT_TYPE_JSON)
        elif "GET /data" in request:
            response = generate_http_response(None, status=HTTP_STATUS_FOUND, location=f"/dynamic_data?endpoint=json_data")
        elif "GET /json_data" in request:
            response = generate_http_response(generate_json_data(), content_type=HTTP_CONTENT_TYPE_JSON)
        elif "GET /logs" in request:
            response = generate_http_response(None, status=HTTP_STATUS_FOUND, location=f"/dynamic_data?endpoint=json_logs")
        elif "GET /json_logs" in request:
            response = generate_http_response(generate_json_logs(), content_type=HTTP_CONTENT_TYPE_JSON)
        elif "GET /readings" in request:
            response = generate_http_response(None, status=HTTP_STATUS_FOUND, location=f"/dynamic_data?endpoint=json_readings")
        elif "GET /json_readings" in request:
            response = generate_http_response(generate_json_readings(), content_type=HTTP_CONTENT_TYPE_JSON)
        elif "GET /restart_bmp280" in request:
            restart_bmp280(None)
            response = generate_http_response(
                "Restarted BMP280 sensor", content_type=HTTP_CONTENT_TYPE_TEXT
            )
        elif "GET /remount_sdcard" in request:
            mount_sdcard()
            response = generate_http_response(
                "Remount SDCard", content_type=HTTP_CONTENT_TYPE_TEXT
            )
        elif "GET /sync_time" in request:
            sync_time()
            time_init = time.time()
            response = generate_http_response(
                f"Time sync completed: {get_iso_timestamp()}",
                content_type=HTTP_CONTENT_TYPE_TEXT,
            )
        elif "GET /reset" in request:
            reset()
        else:
            response = generate_http_response(
                "Page not found",
                content_type=HTTP_CONTENT_TYPE_TEXT,
                status=HTTP_STATUS_NOT_FOUND,
            )
        # print("response:", repr(response), send_file_contents)
        cl.sendall(response)
        for send_file_content in send_file_contents:
            with open(send_file_content, "r") as f:
                for line in f:
                    cl.sendall(line)
        end_time = time.ticks_ms()
        logger.debug(
            f"Responded in {time.ticks_diff(end_time, start_time)}ms",
            convert_to_human_readable_str(*ramf(), unit_name="KB", name="Free RAM space"),
        )
    except Exception as e:
        logger.error("Error handling request:", e)
    finally:
        cl.close()
        # Track the server activity time
        last_server_activity = time.ticks_ms()


def web_server(ip, port=80):
    s = socket.socket()
    try:
        addr = socket.getaddrinfo(ip, port)[0][-1]
        s.bind(addr)
        logger.info(f"Successfully bound to {ip}:{port}")
        s.listen(1)
        logger.info("Listening on", addr)
        
        while True:
            handle_web_request(s)

    except OSError as e:
        logger.error("Error connecting to socket:", e)
        raise RuntimeError(e)
    finally:
        s.close()


def web_server_health_check(timer):
    if (
        time.ticks_diff(time.ticks_ms(), last_server_activity) > WEB_SERVER_HEALTH_CHECK_TIME_DIFF_S * 60 * 1000
    ):  # If no activity in the last 5 minutes
        logger.warning(f"No server activity detected in the last {WEB_SERVER_HEALTH_CHECK_TIME_DIFF_S} min")
    elif AUTOMATIC_DEVICE_RESTART:
        # Feed the watchdog timer even if no activity
        wdt.feed()


def main():
    global time_init

    # Connect to wifi
    led_onboard.off()
    ip = connect_to_wifi()
    led_onboard.on()
    if AUTOMATIC_DEVICE_RESTART:
        wdt.feed()

    # Sync time
    sync_time()
    time_init = time.time()
    if AUTOMATIC_DEVICE_RESTART:
        wdt.feed()

    try:
        # Start the periodic sensor reading
        read_dht22_timer = Timer(-1)
        read_dht22_timer.init(
            freq=DHT22_FREQUENCY, mode=Timer.PERIODIC, callback=read_dht22
        )
        # WARNING: Default frequency of BMP280 is too fast (use 2s instead)
        read_bmp280_timer = Timer(-1)
        read_bmp280_timer.init(period=2000, mode=Timer.PERIODIC, callback=read_bmp280)
        # Since the BMP280 timer is crashing all the time restart it periodically
        restart_bmp280_timer = Timer(-1)
        restart_bmp280_timer.init(
            period=60 * 60 * 1000, mode=Timer.PERIODIC, callback=restart_bmp280
        )
        
        # Since the SD card sometimes breaks or can be taken out remount it periodically
        sdcard_remount_timer = machine.Timer(-1)
        sdcard_remount_timer.init(
            period=20 * 60 * 1000,
            mode=machine.Timer.PERIODIC,
            callback=lambda timer: mount_sdcard(),
        )

        # If the webserver is not being used for some time (e.g. crashes automatically restart the device)
        health_timer = machine.Timer(-1)
        health_timer.init(
            period=4 * 1000,
            mode=machine.Timer.PERIODIC,
            callback=web_server_health_check,
        )

        # Start the web server
        web_server(ip)
    except Exception as e:
        logger.error("Error occurred in main:", e)
    finally:
        # Ensure that all timers are stopped if there's an error
        read_dht22_timer.deinit()
        read_bmp280_timer.deinit()
        restart_bmp280_timer.deinit()
        logger.info("Timers have been stopped")


if __name__ == "__main__":
    try:
        logger.info("start main()...")
        main()
        logger.info("main() finished, restarting...")
        # Restart the machine in case the main function terminates
        reset()
    except KeyboardInterrupt:
        print("Program stopped.")
    except MemoryError:
        print("Memory error detected, restarting...")
        reset()
    except Exception as e:
        print(f"Unexpected error: {e}, restarting...")
        reset()
