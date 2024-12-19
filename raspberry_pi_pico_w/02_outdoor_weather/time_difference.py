from time import time


def get_time_difference(start_time):
    time_diff_s = time() - start_time
    minutes, seconds = divmod(time_diff_s, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return days, hours, minutes, seconds
