import os
import select
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
end = time.monotonic() + float(sys.argv[2])
(root / 'consuming').touch()
while time.monotonic() < end:
    ready, _, _ = select.select([sys.stdin], [], [], max(0, end-time.monotonic()))
    if ready:
        data = os.read(0, 4096)
        if not data:
            break
        with (root / 'consumed').open('ab') as stream:
            stream.write(data)
