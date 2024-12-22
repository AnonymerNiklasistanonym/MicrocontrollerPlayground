import network
import socket
import time
import os
import ntptime
import ujson
from machine import I2C, Pin, Timer, reset
from dht import DHT22

from bmp280 import *

from wifi_config import SSID, PASSWORD
from pins_config import (
    GPIO_PIN_INPUT_DHT22,
    GPIO_PIN_I2C_BMP280_SDA,
    GPIO_PIN_I2C_BMP280_SCL,
)
from free_storage import df, ramf, convert_to_human_readable_str
from timestamp import get_iso_timestamp
from time_difference import get_time_difference
from print_history import (
    Logger,
    PrintHistory,
    PrintHistoryLoggingHandler,
    ConsoleHandler,
)
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
    HTTP_CONTENT_TYPE_JSON,
    HTTP_CONTENT_TYPE_TEXT,
    HTTP_STATUS_NOT_MODIFIED,
    HTTP_STATUS_NOT_FOUND,
)


PROGRAM_VERSION = const("v0.1")

BMP280_FREQUENCY_I2C = const(100000)  # Hertz (default 100kHz higher, fast mode 400kHz)
BMP280_FREQUENCY = const(157)  # Hertz (WARNING: every 6.4ms!)
BMP280_TOLERANCE_AIR_PRESSURE = const(
    1 * 100
)  # Pascal (Pascal * 100 to convert from Hectopascal)
BMP280_RANGE_AIR_PRESSURE = (300 * 100, 1100 * 100)
BMP280_TOLERANCE_TEMPERATURE = const(0.5)  # Degrees Celsius
BMP280_RANGE_TEMPERATURE = (-40, 85)

DHT22_FREQUENCY = const(0.5)  # Hertz
DHT22_TOLERANCE_TEMPERATURE = const(0.5)  # Degrees Celsius
DHT22_RANGE_TEMPERATURE = (-40, 80)
DHT22_TOLERANCE_RELATIVE_HUMIDITY = const(2.0)  # Percent
DHT22_RANGE_RELATIVE_HUMIDITY = (0, 100)

SENSOR_ID_BMP280 = const("bmp280")
SENSOR_ID_DHT22 = const("dht22")

MEASUREMENT_ID_BMP280_TEMPERATURE = f"{SENSOR_ID_BMP280}_temperature_celsius"
MEASUREMENT_ID_BMP280_AIR_PRESSURE = f"{SENSOR_ID_BMP280}_air_pressure_pa"

MEASUREMENT_ID_DHT22_TEMPERATURE = f"{SENSOR_ID_DHT22}_temperature_celsius"
MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY = f"{SENSOR_ID_DHT22}_relative_humidity_percent"

HTML_CSS_DEFAULT = const(
    """
    table {
        width: 50%;
        margin: 20px;
        border-collapse: collapse;
    }
    th, td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    th {
        background-color: #f2f2f2;
    }
    h2 {
        color: #333;
    }
"""
)

# The amount of values until a sensor is stabilized
SENSOR_STABILIZE_COUNT = const(100)
# The amount of values to keep in the buffers
BUFFER_COUNT = const(20)

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
    MEASUREMENT_ID_DHT22_TEMPERATURE: "°C",
    MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY: "%",
    MEASUREMENT_ID_BMP280_TEMPERATURE: "°C",
    MEASUREMENT_ID_BMP280_AIR_PRESSURE: "Pa",
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
print_history_instance = PrintHistory()
# console_handler = ConsoleHandler()
history_handler = PrintHistoryLoggingHandler(print_history_instance)

# Configure the logger
logger = Logger(name="outdoor_weather", level="DEBUG")
logger.addHandler(history_handler)

# Track uptime
time_init = time.time()

# Optimize Etag calculation
current_etag = None
update_etag = True

# SENSORS SHOULD BE INITALIZED OUTSIDE OF THE MAIN METHOD!

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
            logger.info(f"Time synchronized with NTP server. Previous time: {previous_time}, New time: {time.localtime()}")
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
            sensor_last_values[measurement_id] = value, sensor_last_values[measurement_id][1] 
            last_value = buffer[-1][0] if len(buffer) > 0 else None
            sensor_tolerance = sensor_tolerances[measurement_id]
            change_detected = (
                abs(value - last_value) > sensor_tolerance
                if last_value is not None
                else True
            )
            min_value, max_value = sensor_ranges[measurement_id]
            within_range = value >= min_value and value <= max_value

            if change_detected and within_range and sensor_stabilized[sensor_id]:
                logger.debug(
                    f"[{measurement_id}] Recorded: {value}{unit} at {timestamp}"
                )
                buffer.append([value, timestamp])
                if len(buffer) > BUFFER_COUNT:
                    buffer.pop(0)
                update_etag = True
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


def render_html_data():
    """
    Renders the HTML page displaying the temperature and humidity records in tables.
    """
    html = "<h1>Measurements</h1>"

    html += generate_html_button("View Measurements as JSON", "/json_measurements")
    html += generate_html_button("View Info", "/info")
    html += generate_html_button("View Logs", "/logs")

    for name, measurement_id in [
        ("DHT22 Temperature", MEASUREMENT_ID_DHT22_TEMPERATURE),
        ("DHT22 Relative Humidity", MEASUREMENT_ID_DHT22_RELATIVE_HUMIDITY),
        ("BMP280 Temperature", MEASUREMENT_ID_BMP280_TEMPERATURE),
        ("BMP280 Air Pressure", MEASUREMENT_ID_BMP280_AIR_PRESSURE),
    ]:
        unit = sensor_unit[measurement_id]
        buffer = buffer_readings[measurement_id][::-1]
        
        html += f"<h2>{name} Records ({sensor_last_values[measurement_id][0]}{unit})</h2>"
        html += generate_html_table([unit, "Timestamp"], buffer)

    return generate_html(
        "Measurements",
        html,
        css=HTML_CSS_DEFAULT,
    )


def render_html_logs():
    html = "<h1>Logs</h1>"
    html += "<h2>Recent Logs:</h2>"

    html += generate_html_table(
        ["Message", "Timestamp"], print_history_instance.get_history()
    )

    return generate_html(
        "Logs",
        html,
        css=HTML_CSS_DEFAULT,
    )


def render_html_info():
    html = "<h1>Info</h1>"
    html += "<h2>Free Storage:</h2>"

    file_space_f, file_space_t = df()

    html += generate_html_list(
        [
            convert_to_human_readable_str(
                "Free file space", file_space_f, T=848 * 1024, unit_name="KB"
            ),
            convert_to_human_readable_str("Free RAM space", *ramf(), unit_name="KB"),
        ]
    )

    html += "<h2>Network:</h2>"

    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)

    html += generate_html_list(
        [
            f"Device name in network: {ap.config('essid')}",
            f"Network name: {sta.config('essid')}",
        ]
    )

    html += "<h2>Misc:</h2>"

    uptime_days, uptime_hours, uptime_minutes, uptime_seconds = get_time_difference(
        time_init
    )

    html += generate_html_list(
        [
            f"Version: {PROGRAM_VERSION}",
            f"OS information: {os.uname()}",
            f"Uptime: {uptime_days}d {uptime_hours:02}:{uptime_minutes:02}:{uptime_seconds:02}",
            f"Current time: {get_iso_timestamp()}",
            f"Readings: {counter_readings}",
        ]
    )

    return generate_html(
        "Info",
        html,
        css=HTML_CSS_DEFAULT,
    )


def handle_web_request(socket):
    global time_init
    global update_etag
    global current_etag

    cl, addr = socket.accept()
    logger.debug(
        "Client connected from",
        addr,
        convert_to_human_readable_str("Free RAM space", *ramf(), unit_name="KB"),
    )
    try:
        start_time = time.ticks_ms()
        request = cl.recv(1024).decode("utf-8")
        logger.debug(request)
        if not request:
            # Client has closed the connection
            return
        if "GET /measurements" in request:
            response = generate_http_response(render_html_data())
        elif "GET /info" in request:
            response = generate_http_response(render_html_info())
        elif "GET /logs" in request:
            response = generate_http_response(render_html_logs())
        elif "GET /restart_bmp280" in request:
            restart_bmp280(None)
            response = generate_http_response(
                "Restarted BMP280 sensor", content_type=HTTP_CONTENT_TYPE_TEXT
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
        elif "GET /json_measurements" in request:
            if update_etag:
                current_etag = generate_etag(buffer_readings)
                update_etag = False
            serve_data = True
            # Catch ETag entries from the request header if request is conditional
            if "If-None-Match" in request:
                etag_header = (
                    request.split("If-None-Match: ")[1].split("\r\n")[0].strip().strip('"')
                )
                logger.debug(f"Found {etag_header=} ({current_etag=}, {etag_header == current_etag=})")
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
        else:
            response = generate_http_response(
                "Page not found",
                content_type=HTTP_CONTENT_TYPE_TEXT,
                status=HTTP_STATUS_NOT_FOUND,
            )
        #print("response:", repr(response))
        cl.sendall(response)
        end_time = time.ticks_ms()
        logger.debug(f"Responded in {time.ticks_diff(end_time, start_time)}ms")
    except Exception as e:
        logger.error("Error handling request:", e)
    finally:
        cl.close()


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


def main():
    global time_init

    # Connect to wifi
    led_onboard.off()
    ip = connect_to_wifi()
    led_onboard.on()

    # Sync time
    sync_time()
    time_init = time.time()

    try:
        # Start the periodic sensor reading
        read_dht22_timer = Timer(-1)
        read_dht22_timer.init(freq=DHT22_FREQUENCY, mode=Timer.PERIODIC, callback=read_dht22)
        # WARNING: Default frequency of BMP280 is too fast (use 2s instead)
        read_bmp280_timer = Timer(-1)
        read_bmp280_timer.init(period=2000, mode=Timer.PERIODIC, callback=read_bmp280)
        # Since the BMP280 timer is crashing all the time restart it periodically (every hour)
        restart_bmp280_timer = Timer(-1)
        restart_bmp280_timer.init(
            period=60 * 60 * 1000, mode=Timer.PERIODIC, callback=restart_bmp280
        )

        # Start the web server
        web_server(ip)
    except Exception as e:
        print("Error occurred:", e)
    finally:
        # Ensure that all timers are stopped if there's an error
        read_dht22_timer.deinit()
        read_bmp280_timer.deinit()
        restart_bmp280_timer.deinit()
        print("Timers have been stopped.")


try:
    main()
    # Restart the machine in case the main function terminates
    print("Restarting...")
    reset()
except KeyboardInterrupt:
    print("Program stopped.")
