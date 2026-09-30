import io
import unittest
from collections import deque

from watchmode_truth_lab.runner import _capture


class BoundedStream(io.StringIO):
    def readline(self, size=-1):
        if not 0 < size <= 4096:
            raise AssertionError("Log reads must be bounded before allocating a line")
        return super().readline(size)


class LogTests(unittest.TestCase):
    def test_long_line_is_drained_in_bounded_reads_and_next_line_survives(self):
        lines = deque(maxlen=200)
        source = BoundedStream("x" * (2 * 1024 * 1024) + "\nlast line\n")
        _capture(source, lines)
        self.assertEqual(list(lines), ["x" * 2000, "last line"])
        self.assertTrue(source.closed)
