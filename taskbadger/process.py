import subprocess
import threading
import time
from datetime import datetime


class ProcessRunner:
    def __init__(self, process_args, env, capture_output: bool, update_frequency: int = 5):
        self.process_args = process_args
        self.env = env
        self.capture_output = capture_output
        self.update_frequency = update_frequency
        self.returncode = None

    def run(self):
        last_update = datetime.utcnow()

        kwargs = {}
        if self.capture_output:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

        process = subprocess.Popen(self.process_args, env=self.env, shell=True, **kwargs)
        if self.capture_output:
            stdout = Reader(process.stdout).start()
            stderr = Reader(process.stderr).start()

        while process.poll() is None:
            time.sleep(0.1)
            if _should_update(last_update, self.update_frequency):
                last_update = datetime.utcnow()
                if self.capture_output:
                    yield {"stdout": stdout.read(), "stderr": stderr.read()}
                else:
                    yield

        self.returncode = process.returncode


class Reader:
    def __init__(self, source):
        self.source = source
        self.data = []
        self._lock = threading.Lock()

    def start(self):
        self._thread = threading.Thread(name="reader-thread", target=self._reader, daemon=True)
        self._thread.start()
        return self

    def _reader(self):
        """Read data from source until EOF, adding it to collector."""
        while True:
            data = self.source.read1().decode()
            self._lock.acquire()
            self.data.append(data)
            self._lock.release()
            if not data:
                break
        return

    def read(self):
        """Read data written by the process to its standard output."""
        self._lock.acquire()
        outdata = "".join(self.data)
        del self.data[:]
        self._lock.release()
        return outdata


def _should_update(last_update: datetime, update_frequency_seconds):
    return (datetime.utcnow() - last_update).total_seconds() >= update_frequency_seconds
