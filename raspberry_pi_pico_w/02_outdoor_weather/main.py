import network
import socket
import time
import os
import ntptime
import ujson
from machine import Pin, Timer
from dht import DHT22

from wifi_config import SSID, PASSWORD
from pins_config import GPIO_PIN_INPUT_DHT22
from free_storage import df, ramf, convert_to_human_readable_str
from timestamp import get_iso_timestamp
from time_difference import get_time_difference
from print_history import PrintHistory
from html_helper import generate_html, generate_html_list, generate_html_table


# DHT22
dht22_sensor = DHT22(Pin(GPIO_PIN_INPUT_DHT22))
MEASUREMENT_ID_DHT22_TEMPERATURE = const("dht22_temperature_celsius")
MEASUREMENT_ID_DHT22_HUMIDITY = const("dht22_relative_humidity_percent")
dht22_sensor_stabalized = False
sensor_unit = {  # Name of measured value unit
    MEASUREMENT_ID_DHT22_TEMPERATURE: "°C",
    MEASUREMENT_ID_DHT22_HUMIDITY: "%",
}
sensor_stabilized_last_values = {  # Last value, # of no changes until sensor stabalized
    MEASUREMENT_ID_DHT22_TEMPERATURE: (None, 5),
    MEASUREMENT_ID_DHT22_HUMIDITY: (None, 5),
}
sensor_tolerances = {  # min, max
    MEASUREMENT_ID_DHT22_TEMPERATURE: 0.5,  # Degrees Celsius
    MEASUREMENT_ID_DHT22_HUMIDITY: 2.0,  # Percent
}
sensor_ranges = {  # min, max
    MEASUREMENT_ID_DHT22_TEMPERATURE: (-40, 80),
    MEASUREMENT_ID_DHT22_HUMIDITY: (0, 100),
}
sensor_frequencies = {"dht22": 0.5}  # Hertz  # (1 / 0.5 Hertz = 2 Seconds)
# Onboard-LED
led_onboard = Pin("LED", Pin.OUT)

# Store measurements as separate lists for temperature and humidity
buffer_readings = {  # (value: number, iso timestamp: str)
    MEASUREMENT_ID_DHT22_TEMPERATURE: [],
    MEASUREMENT_ID_DHT22_HUMIDITY: [],
}
counter_readings = {  # good readings, bad readings
    MEASUREMENT_ID_DHT22_TEMPERATURE: {"good": 0, "bad": 0},
    MEASUREMENT_ID_DHT22_HUMIDITY: {"good": 0, "bad": 0},
    "dht22": {"good": 0},
}
# The amount of values to keep in the buffers
BUFFER_COUNT = const(32)

# Store uptime
time_init = time.time()

# Create an instance of PrintHistory
print_history_instance = PrintHistory()


def print_history(*args):
    """
    Custom print function that logs the message to the print history instance
    """
    # Convert all arguments to strings and join them with spaces
    message = " ".join(str(arg) for arg in args)
    print_history_instance.add(message)
    # Print the message to the console
    print(*args)


def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print_history("Connecting to WiFi...")
    while not wlan.isconnected():
        led_onboard.on()
        time.sleep(0.5)
        led_onboard.off()
        time.sleep(0.5)
    print_history("Connected to WiFi:", wlan.ifconfig())
    # TODO Doesn't work
    # try:
    #    wlan.config("raspberrypicow2024")
    #    print_history(f"hostname set to '{hostname}.local'")
    # except Exception as e:
    #    print_history(f"Failed to set hostname: {e}")
    return wlan.ifconfig()[0]


def sync_time():
    try:
        previous_time = time.localtime()
        ntptime.settime()  # Sync time from NTP server
        print_history(
            "Time synchronized with NTP server.", previous_time, time.localtime()
        )
    except Exception as e:
        print_history("Failed to sync time:", e)


def read_dht22(timer):
    global dht22_sensor_stabalized
    global sensor_stabilized_last_values
    global buffer_readings
    global counter_readings

    try:
        dht22_sensor.measure()
        temp = dht22_sensor.temperature()
        humidity = dht22_sensor.humidity()
        timestamp = get_iso_timestamp()
        counter_readings["dht22"]["good"] += 1

        sensor_measurements = [
            (temp, MEASUREMENT_ID_DHT22_TEMPERATURE),
            (humidity, MEASUREMENT_ID_DHT22_HUMIDITY),
        ]

        if not dht22_sensor_stabalized:
            changes_detected = False
            for value, measurement_id in sensor_measurements:
                dht22_sensor_stabilized_last_value, count = (
                    sensor_stabilized_last_values[measurement_id]
                )
                sensor_tolerance = sensor_tolerances[measurement_id]
                if dht22_sensor_stabilized_last_value is None:
                    sensor_stabilized_last_values[measurement_id] = value, count
                    changes_detected = True
                    print_history(
                        f"[DHT22:{measurement_id}] sensor not stabalized: missing last_value"
                    )
                elif abs(value - dht22_sensor_stabilized_last_value) > sensor_tolerance:
                    changes_detected = True
                    print_history(
                        f"[DHT22:{measurement_id}] sensor not stabalized: detected change outside of tolerances"
                    )
                elif count != 0:
                    changes_detected = True
                    print_history(
                        f"[DHT22:{measurement_id}] sensor not stabalized: detected no change but wait {count} more times"
                    )
                    sensor_stabilized_last_values[measurement_id] = value, count - 1
                else:
                    print_history(
                        f"[DHT22:{measurement_id}] sensor partly stabalized: detected no change"
                    )
            if not changes_detected:
                print_history(f"[DHT22] sensor stabalized: no changes detected")
                dht22_sensor_stabalized = True

        for value, measurement_id in sensor_measurements:
            unit = sensor_unit[measurement_id]
            buffer = buffer_readings[measurement_id]
            last_value = buffer[-1][0] if len(buffer) > 0 else None
            sensor_tolerance = sensor_tolerances[measurement_id]
            change_detected = (
                abs(value - last_value) > sensor_tolerance
                if last_value is not None
                else True
            )
            min_value, max_value = sensor_ranges[measurement_id]
            within_range = value >= min_value and value <= max_value

            if change_detected and within_range and dht22_sensor_stabalized:
                print_history(
                    f"[DHT22:{measurement_id}] Recorded: {value}{unit} at {timestamp}"
                )
                buffer.append([value, timestamp])
                if len(buffer) > BUFFER_COUNT:
                    buffer.pop(0)
            else:
                reason = f"not within tolerance {sensor_tolerance}{unit}"
                if not within_range:
                    reason = (
                        f"value not within range [{min_value}{unit},{max_value}{unit}]"
                    )
                    counter_readings[measurement_id]["bad"] += 1
                elif not dht22_sensor_stabalized:
                    reason = f"sensor stabilization ongoing"

                print_history(
                    f"[DHT22:{measurement_id}] Skipped: current {value}{unit} ({reason})"
                )

            if within_range and dht22_sensor_stabalized:
                counter_readings[measurement_id]["good"] += 1

    except Exception as e:
        print_history("[DHT22] Error reading sensor:", e)
        if e in counter_readings["dht22"]:
            counter_readings["dht22"][e] += 1
        else:
            counter_readings["dht22"][e] = 1


def render_html():
    """
    Renders the HTML page displaying the temperature and humidity records in tables.
    """
    html = "<h1>Sensor Data</h1>"

    for name, measurement_id in [
        ("Temperature", MEASUREMENT_ID_DHT22_TEMPERATURE),
        ("Relative Humidity", MEASUREMENT_ID_DHT22_HUMIDITY),
    ]:
        html += f"<h2>{name} Records</h2>"

        unit = sensor_unit[measurement_id]
        buffer = buffer_readings[measurement_id]

        html += generate_html_table([unit, "Timestamp"], buffer)

    html += "<h1>Device Stats</h1><h2>Recent Logs</h2>"

    html += generate_html_table(
        ["Message", "Timestamp"], print_history_instance.get_history()
    )

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
            f"OS information: {os.uname()}",
            f"Uptime: {uptime_days}d {uptime_hours:02}:{uptime_minutes:02}:{uptime_seconds:02}",
            f"Current time: {get_iso_timestamp()}",
            f"Readings: {counter_readings}",
        ]
    )

    return generate_html(
        "Outdoor Weather",
        html,
        css="""
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
    """,
    )


def web_server(ip):
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print_history("Listening on", addr)

    while True:
        cl, addr = s.accept()
        print_history("Client connected from", addr)
        try:
            request = cl.recv(1024).decode("utf-8")
            print_history(request)
            if "GET /measurements" in request:
                # Return the HTML page rendering the tables
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                response += render_html()
            elif "GET /json_measurements" in request:
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
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
                response += json_str
            else:
                response = "HTTP/1.1 404 Not Found\r\n\r\nPage not found"
            cl.sendall(response)
        except Exception as e:
            print_history("Error handling request:", e)
        finally:
            cl.close()


def main():
    global time_init

    # Connect to wifi
    led_onboard.off()
    ip = connect_to_wifi()
    led_onboard.on()

    # Sync time
    sync_time()
    time_init = time.time()

    # Start the periodic sensor reading
    sensor_timer = Timer()
    sensor_timer.init(
        freq=sensor_frequencies["dht22"], mode=Timer.PERIODIC, callback=read_dht22
    )

    # Start the web server
    web_server(ip)


main()
