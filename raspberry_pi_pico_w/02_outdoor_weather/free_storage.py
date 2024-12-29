# Based on: https://forum.micropython.org/viewtopic.php?t=3499

import gc
import os
import sys


def df():
    """Free file space"""
    s = os.statvfs('//') # File system statistics for the directory '//' (the root directory)
    T = s[0]             # The total number of blocks
    F = s[3]             # The number of free blocks
    BLOCK_SIZE = s[1]    # The size of each block in bytes
    return F * BLOCK_SIZE, T * BLOCK_SIZE


def ramf():
    """Free RAM space"""
    F = gc.mem_free()   # Free memory in bytes
    A = gc.mem_alloc()  # Allocated memory in bytes
    return F, F + A


def sdf(mount_point, file_path_prefix="/"):
    """Free storage space on the SD card in bytes"""
    try:
        file_exists = mount_point[len(file_path_prefix):] in os.listdir(file_path_prefix)
        if not file_exists:
            return -1, -1
        
        statvfs = os.statvfs(mount_point)
        BLOCK_SIZE = statvfs[0]    # Block size
        F = statvfs[3]             # The number of free blocks
        T = statvfs[2]             # Total number of blocks
        return BLOCK_SIZE * F, BLOCK_SIZE * T
    except OSError as e:
        return -1, -1


def convert_to_human_readable_str(F, T=None, name=None, unit_name="B"):
    name_str = f"{name}: " if name is not None else ""
    unit = 1024 * 1024 * 1024 if unit_name == "GB" else 1024 * 1024 if unit_name == "MB" else 1024 if unit_name == "KB" else 1
    if F == -1:
        return f"{name_str}None"
    F_unit = F / unit
    if T is None:
        return f"{name_str}{F_unit:.3f} {unit_name}"
    T_unit = T / unit
    P = F / T * 100
    return f"{name_str}{F_unit:.3f}/{T_unit:.3f} {unit_name} ({P:.2f} %)"