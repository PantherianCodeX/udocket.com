import subprocess, shlex

def run_cmd(cmd: str, timeout: int):
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return 124, b"", b"timeout"
    return proc.returncode, out, err