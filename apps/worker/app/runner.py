import shlex
import subprocess
import time
from typing import Callable, Optional


def run_cmd(cmd: str, timeout: int, cancel_check: Optional[Callable[[], bool]] = None):
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.monotonic()
    poll_window = 1.0

    while True:
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            proc.kill()
            out, err = proc.communicate()
            return 124, out, err or b"timeout"
        wait_for = poll_window if remaining > poll_window else remaining
        try:
            out, err = proc.communicate(timeout=wait_for)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            if cancel_check and cancel_check():
                proc.terminate()
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, err = proc.communicate()
                return 125, out, err or b"cancelled"
            continue
