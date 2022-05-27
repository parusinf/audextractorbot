import os
from typing import Optional
import config.config as config


def read_pid_file() -> Optional[int]:
    if os.path.exists(config.PID_FILE):
        with open(config.PID_FILE) as file:
            return int(file.read())
    else:
        return None


def write_pid_file() -> int:
    pid = os.getpid()
    with open(config.PID_FILE, 'w') as file:
        file.write(f'{pid}\n')
    return pid


def remove_pid_file() -> Optional[int]:
    pid = read_pid_file()
    if pid:
        os.remove(config.PID_FILE)
    return pid
