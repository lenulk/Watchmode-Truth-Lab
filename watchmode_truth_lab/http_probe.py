"""Isolate blocking network reads so a scenario can enforce its deadline."""

import multiprocessing
import urllib.error
import urllib.request


def _worker(connection):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        while True:
            item = connection.recv()
            if item is None:
                return
            url, limit = item
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            try:
                with opener.open(request, timeout=0.5) as response:
                    data = response.read(limit + 1)
                result = (None, "body_too_large") if len(data) > limit else (data, None)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                result = (None, type(exc).__name__)
            connection.send(result)
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        connection.close()


class HTTPProbe:
    def __init__(self):
        self.process = None
        self.connection = None

    def _start(self):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        self.process = context.Process(target=_worker, args=(child,), daemon=True)
        self.process.start()
        child.close()
        self.connection = parent

    def read(self, url, timeout, limit):
        if timeout <= 0:
            return None, "probe_deadline_exceeded"
        if self.process is None:
            self._start()
        try:
            self.connection.send((url, limit))
            if self.connection.poll(timeout):
                return self.connection.recv()
        except (EOFError, BrokenPipeError, OSError):
            self.close()
            return None, "probe_process_exited"
        self.close()
        return None, "probe_deadline_exceeded"

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.2)
            self.process.close()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
