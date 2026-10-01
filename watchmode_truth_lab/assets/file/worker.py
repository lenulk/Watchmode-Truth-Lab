"""Tiny example watch process. It is a fixture, not a production watcher."""

import sys
import time
import errno
import os
from pathlib import Path

source = Path(sys.argv[1])
output = Path(sys.argv[2])
previous = None
read_retry_deadline = None
while True:
    try:
        content = source.read_bytes()
    except OSError as error:
        # Editors may temporarily remove/replace the input; Windows can deny
        # a read while the replaced name is still pending deletion/sharing.
        transient = isinstance(error, FileNotFoundError) or (
            isinstance(error, PermissionError) and os.name == 'nt' and error.errno == errno.EACCES)
        if not transient:
            raise
        now = time.monotonic()
        if read_retry_deadline is None:
            read_retry_deadline = now + 1.0
        if now >= read_retry_deadline:
            raise
        time.sleep(0.02)
        continue
    read_retry_deadline = None
    if content != previous:
        output.write_bytes(content)
        previous = content
    time.sleep(0.02)
