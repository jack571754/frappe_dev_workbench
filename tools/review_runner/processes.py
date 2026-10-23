import os
import signal
import subprocess
import tempfile
import time


def run_process(args, heartbeat, input_text='', env=None, limit=1_000_000, on_cancel=None):
    """心跳拒绝或超时后终止整个进程组，包括材料读取中的 Git 子进程。"""
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output:
        source.write(input_text.encode('utf-8'))
        source.seek(0)
        process = subprocess.Popen(args, stdin=source, stdout=output, stderr=subprocess.DEVNULL,
                                   env=env, start_new_session=True)
        try:
            while process.poll() is None:
                heartbeat()
                if output.tell() > limit:
                    raise ValueError('invalid_report')
                time.sleep(.05)
            if process.returncode:
                raise RuntimeError('execution')
            output.seek(0)
            data = output.read(limit + 1)
            if len(data) > limit:
                raise ValueError('invalid_report')
            return data.decode('utf-8')
        finally:
            if process.poll() is None:
                try:
                    if on_cancel:
                        try:
                            on_cancel()
                        except Exception:
                            pass
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
