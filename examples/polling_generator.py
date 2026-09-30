"""Tiny example watch process. It is a fixture, not a production watcher."""

import sys
import time
from pathlib import Path

source = Path(sys.argv[1])
output = Path(sys.argv[2])
previous = None
while True:
    content = source.read_bytes()
    if content != previous:
        output.write_bytes(content)
        previous = content
    time.sleep(0.02)
