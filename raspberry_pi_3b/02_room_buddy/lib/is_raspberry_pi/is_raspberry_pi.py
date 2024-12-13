def is_raspberry_pi():
    """Detect if the program is running on a Raspberry Pi or on another (development) machine"""
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read().lower()
        return "raspberry pi" in cpuinfo
    except FileNotFoundError:
        return False
