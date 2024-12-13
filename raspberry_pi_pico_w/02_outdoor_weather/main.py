import network
import socket
import time
import machine
import ntptime
from dht import DHT22
from wifi_config import SSID, PASSWORD
from pins_config import GPIO_PIN_INPUT_DHT22
from free_storage import df, ramf, convert_to_human_readable_str
from timestamp import get_iso_timestamp

# DHT22
dht_sensor = DHT22(machine.Pin(GPIO_PIN_INPUT_DHT22))
DHT22_TOLERANCE_TEMP = 0.5     # Degrees Celsius
DHT22_TOLERANCE_HUMIDITY = 2.0 # Percent
DHT22_FREQUENCY = 0.5          # Hertz
stabelized_counter = 10
# Onboard-LED
led_onboard = machine.Pin("LED", machine.Pin.OUT)

# Store measurements as separate lists for temperature and humidity
temperature_timestamps = []
humidity_timestamps = []
# The amount of temperature/humidity timestamps to keep in the buffer
BUFFER_COUNT = 32

# Store logs
class PrintHistory:
    def __init__(self, max_size=20):
        self.history = []  # List to store the print statements
        self.max_size = max_size  # Maximum size of the history

    def add(self, message):
        """
        Add a message to the history, keeping the size within the max_size.
        """
        if len(self.history) >= self.max_size:
            self.history.pop(0)
        self.history.append((message,get_iso_timestamp()))

    def get_history(self):
        """
        Get the full history of stored messages.
        """
        return self.history


# Create an instance of PrintHistory
print_history = PrintHistory()

def custom_print(*args):
    """
    Custom print function for MicroPython that logs the message to history
    and prints it to the console.
    """
    # Convert all arguments to strings and join them with spaces
    message = " ".join(str(arg) for arg in args)
    print_history.add(message)  # Add to the history
    print(message)  # Print to the console

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    custom_print("Connecting to WiFi...")
    while not wlan.isconnected():
        led_onboard.on()
        time.sleep(0.5)
        led_onboard.off()
        time.sleep(0.5)
    custom_print("Connected to WiFi:", wlan.ifconfig())
    try:
        wlan.config("raspberrypicow2024")
        custom_print(f"hostname set to '{hostname}.local'")
    except Exception as e:
        custom_print(f"Failed to set hostname: {e}")
    return wlan.ifconfig()[0]

def sync_time():
    try:
        print("Previous time:", time.localtime())
        ntptime.settime()  # Sync time from NTP server
        custom_print("Time synchronized with NTP server.")
        print("Current time:", time.localtime())
    except Exception as e:
        custom_print("Failed to sync time:", e)

def take_measurement():
    global stabelized_counter
    try:
        # Check if stabilization delay has elapsed
        if stabelized_counter != 0:
            custom_print(f"Waiting for sensor stabilization... {stabelized_counter}")
            stabelized_counter -= 1
            if stabelized_counter == 0:
                custom_print("Sensor stabilized. Starting measurements.")
            else:
                return

        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        timestamp = get_iso_timestamp()
        
        temp_changed = True
        humidity_changed = True

        # Check if the temperature or humidity is outside tolerance ranges
        if len(temperature_timestamps) > 0 or len(humidity_timestamps) > 0:
            last_temp = temperature_timestamps[-1][0] if len(temperature_timestamps) > 0 else None
            last_humidity = humidity_timestamps[-1][0] if len(humidity_timestamps) > 0 else None

            temp_changed = abs(temp - last_temp) > DHT22_TOLERANCE_TEMP if last_temp is not None else True
            humidity_changed = abs(humidity - last_humidity) > DHT22_TOLERANCE_HUMIDITY if last_humidity is not None else True

        # Record temperature with timestamp if it changed significantly
        if temp_changed:
            custom_print(f"Recorded: {temp}°C at {timestamp}")
            temperature_timestamps.append([temp, timestamp])
            if len(temperature_timestamps) > BUFFER_COUNT:
                temperature_timestamps.pop(0)
        else:
            custom_print(f"Skipped: current {temp}°C not within tolerances")

        # Record humidity with timestamp if it changed significantly
        if humidity_changed:
            custom_print(f"Recorded: {humidity}% at {timestamp}")
            humidity_timestamps.append([humidity, timestamp])
            if len(humidity_timestamps) > BUFFER_COUNT:
                humidity_timestamps.pop(0)
        else:
            custom_print(f"Skipped: current {humidity}% not within tolerances")
            
    except Exception as e:
        custom_print("Error reading sensor:", e)

def render_html():
    """
    Renders the HTML page displaying the temperature and humidity records in tables.
    """
    html = """
    <html>
        <head>
            <title>Outdoor Weather</title>
            <style>
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
            </style>
        </head>
        <body>
            <h1>Sensor Data</h1>
            <h2>Temperature Records</h2>
            <table>
                <tr><th>Temperature (°C)</th><th>Timestamp</th></tr>
    """
    
    # Add temperature rows to the table
    for temp, timestamp in temperature_timestamps:
        html += f"<tr><td>{temp:.2f}</td><td>{timestamp}</td></tr>"

    html += """
            </table>
            <h2>Humidity Records</h2>
            <table>
                <tr><th>Humidity (%)</th><th>Timestamp</th></tr>
    """
    
    # Add humidity rows to the table
    for humidity, timestamp in humidity_timestamps:
        html += f"<tr><td>{humidity:.2f}</td><td>{timestamp}</td></tr>"

    html += """
            </table>
            <h1>Device Stats</h1>
            <h2>Logs</h2>
            <table>
                <tr><th>Log Message</th><th>Timestamp</th></tr>
    """
    
    # Add logs to the table
    for message, timestamp in print_history.get_history():
        html += f"<tr><td>{message}</td><td>{timestamp}</td></tr>"
        
    html += """
            </table>
            <h2>Free space:</h2>
            <ul>
    """
    
    html += f"<li><p>{convert_to_human_readable_str('Free file space', *df(), 'MB')}</p></li>"
    html += f"<li><p>{convert_to_human_readable_str('Free RAM space', *ramf(), 'KB')}</p></li>"
    
    # TODO
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    html += f"<li><p>Device name in network: {ap.config('essid')}</p></li>"
    html += f"<li><p>Network name: {sta.config('essid')}</p></li>"

    html += """
            </ul>
        </body>
    </html>
    """
    
    return html

def web_server(ip):
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    custom_print("Listening on", addr)

    while True:
        cl, addr = s.accept()
        custom_print("Client connected from", addr)
        try:
            request = cl.recv(1024).decode('utf-8')
            custom_print(request)
            if "GET /measurements" in request:
                # Return the HTML page rendering the tables
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                response += render_html()
            elif "GET /json_measurements" in request:
                # Create JSON response with separate temperature and humidity lists
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
                response += '{"temperature_timestamps": ' + str(temperature_timestamps).replace("'", '"') + ', '
                response += '"humidity_timestamps": ' + str(humidity_timestamps).replace("'", '"') + '}'
            else:
                response = "HTTP/1.1 404 Not Found\r\n\r\nPage not found"
            cl.sendall(response)
        except Exception as e:
            custom_print("Error handling request:", e)
        finally:
            cl.close()

def main():
    led_onboard.off()
    ip = connect_to_wifi()
    sync_time()
    led_onboard.on()

    # Start the periodic sensor reading
    sensor_timer = machine.Timer(-1)
    sensor_timer.init(period=int(1 / DHT22_FREQUENCY * 1000), mode=machine.Timer.PERIODIC, callback=lambda t: take_measurement())

    # Start the web server
    web_server(ip)

main()
