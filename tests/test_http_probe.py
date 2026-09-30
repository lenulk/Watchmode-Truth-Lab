import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from watchmode_truth_lab.runner import _wait
from watchmode_truth_lab.http_probe import HTTPProbe
from watchmode_truth_lab.http_probe import _worker as http_worker


def delayed_http_worker(connection):
    time.sleep(0.65)
    http_worker(connection)


class SlowBodyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/large", "/delayed"}:
            if self.path == "/delayed":
                time.sleep(0.65)
            try:
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b"x" * 100)
            except (BrokenPipeError, ConnectionResetError):
                pass
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
    def test_slow_headers_can_complete_within_scenario_budget(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBodyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        oracle = {"type": "http", "url": f"http://127.0.0.1:{server.server_port}/delayed"}
        try:
            result = _wait(b"x" * 100, oracle, Path("."), SimpleNamespace(poll=lambda: None),
                           3, 0.02, 0.05)
            self.assertEqual(result["status"], "pass", result)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_changed_request_discards_pending_response(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBodyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        probe = HTTPProbe()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            self.assertEqual(probe.read(base + "/delayed", 0.1, 1024),
                             (None, "probe_pending"))
            self.assertEqual(probe.read(base + "/large", 3, 32), (None, "body_too_large"))
            self.assertIsNone(probe.pending)
        finally:
            probe.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_delayed_worker_survives_read_slices_within_scenario_budget(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBodyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        oracle = {"type": "http", "url": f"http://127.0.0.1:{server.server_port}/large"}
        try:
            with patch("watchmode_truth_lab.http_probe._worker", delayed_http_worker):
                result = _wait(b"x" * 100, oracle, Path("."), SimpleNamespace(poll=lambda: None),
                               3, 0.02, 0.05)
            self.assertEqual(result["status"], "pass", result)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

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
