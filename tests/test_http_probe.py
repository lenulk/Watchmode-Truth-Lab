import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from watchmode_truth_lab.runner import _wait
from watchmode_truth_lab.http_probe import HTTPProbe


class SlowBodyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/large":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"x" * 100)
            return
        self.send_response(200)
        self.send_header("Content-Length", "15")
        self.end_headers()
        try:
            for _ in range(15):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


class HTTPDeadlineTests(unittest.TestCase):
    def test_oversized_body_is_rejected(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBodyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        probe = HTTPProbe()
        try:
            data, error = probe.read(f"http://127.0.0.1:{server.server_port}/large", 2, 32)
            self.assertIsNone(data)
            self.assertEqual(error, "body_too_large")
        finally:
            probe.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_slow_trickle_body_cannot_extend_observation_deadline(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBodyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        oracle = {"type": "http", "url": f"http://127.0.0.1:{server.server_port}/"}
        process = SimpleNamespace(poll=lambda: None)
        try:
            started = time.monotonic()
            result = _wait(b"x" * 15, oracle, Path("."), process, 0.2, 0.02, 0)
            elapsed = time.monotonic() - started
            self.assertEqual(result["status"], "timeout", result)
            self.assertLess(elapsed, 0.8, "A slow HTTP body must not keep the runner blocked")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)
