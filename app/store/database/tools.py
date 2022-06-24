from typing import Optional
import enum
import math


def row_to_dict(row) -> Optional[dict]:
    if row:
        (obj,) = row
        out = dict(obj.__dict__)
        del out['_sa_instance_state']
        return out
    else:
        return None


def rows_to_list(rows) -> list[dict]:
    out = []
    if rows:
        for row in rows:
            out.append(row_to_dict(row))
    return out


class SizeUnit(enum.Enum):
    B = 1
    KB = 2
    MB = 3
    GB = 4
    TB = 5


def size_unit(size_in_bytes, unit):
    if unit == SizeUnit.KB:
        return size_in_bytes / 1024
    elif unit == SizeUnit.MB:
        return size_in_bytes / (1024 * 1024)
    elif unit == SizeUnit.GB:
        return size_in_bytes / (1024 * 1024 * 1024)
    elif unit == SizeUnit.TB:
        return size_in_bytes / (1024 * 1024 * 1024 * 1024)
    else:
        return size_in_bytes


def human_size(size_in_bytes, unit=None):
    if unit is None:
        if size_unit(size_in_bytes, SizeUnit.KB) < 1:
            unit = SizeUnit.B
        elif size_unit(size_in_bytes, SizeUnit.MB) < 1:
            unit = SizeUnit.KB
        elif size_unit(size_in_bytes, SizeUnit.GB) < 1:
            unit = SizeUnit.MB
        elif size_unit(size_in_bytes, SizeUnit.TB) < 1:
            unit = SizeUnit.GB
        else:
            unit = SizeUnit.TB
    return f'{math.ceil(size_unit(size_in_bytes, unit))} {str(unit).split(".")[1]}'
