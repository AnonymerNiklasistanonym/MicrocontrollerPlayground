# Based on: https://forum.micropython.org/viewtopic.php?t=3499

import gc
import os
import sys


def df():
    """Free file space"""
    # File system statistics for the directory '//' (the root directory
    s = os.statvfs("//")
    T = s[0]  # The total number of blocks
    F = s[3]  # The number of free blocks
    BLOCK_SIZE = s[1]  # The size of each block in bytes
    return F * BLOCK_SIZE, T * BLOCK_SIZE


def ramf():
    """Free RAM space"""
    F = gc.mem_free()  # Free memory in bytes
    A = gc.mem_alloc()  # Allocated memory in bytes
    return F, F + A


def convert_to_human_readable_str(name, F, T=None, unit_name="B"):
    unit = 1024 * 1024 if unit_name == "MB" else 1024 if unit_name == "KB" else 1
    F_unit = F / unit
    if T is None:
        return f"{name}: {F_unit:.3f} {unit_name}"
    T_unit = T / unit
    P = F / T * 100
    return f"{name}: {F_unit:.3f}/{T_unit:.3f} {unit_name} ({P:.2f} %)"
