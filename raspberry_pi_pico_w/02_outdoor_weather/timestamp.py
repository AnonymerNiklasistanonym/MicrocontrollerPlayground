from time import localtime

def get_iso_timestamp():
    """
    Get the current time in ISO 8601 format (e.g., "2024-12-15T14:30:00Z").
    """
    t = localtime()
    return f"{t[0]:04}-{t[1]:02}-{t[2]:02}T{t[3]:02}:{t[4]:02}:{t[5]:02}Z"