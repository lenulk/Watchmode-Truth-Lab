"""Controlled Windows Python3.10 signal delivery comparison before runner repair."""
import json
import os
import subprocess
import sys
import unittest
import uuid

from test_cycle import ROOT


class WaitSignalProof(unittest.TestCase):
    def test_native_handle_wait_vs_interruptible_sleep(self):
        code = '''import json,signal,subprocess,sys,threading,time
p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(4)'])
started=time.monotonic();caught=None
def interrupt():
 time.sleep(0.2);signal.raise_signal(signal.SIGINT)
threading.Thread(target=interrupt,daemon=True).start()
try:
 while time.monotonic()-started<2:
  if sys.argv[1]=='wait':
   try:p.wait(timeout=0.1)
   except subprocess.TimeoutExpired:pass
  else:time.sleep(0.05)
except KeyboardInterrupt:caught=time.monotonic()-started
finally:
 p.kill();p.wait(timeout=3)
print(json.dumps({'caught_after_seconds':caught}))
'''
        results = {}
        for mode in ('wait', 'sleep'):
            result = subprocess.run([sys.executable, '-c', code, mode], capture_output=True,
                                    text=True, encoding='utf-8', timeout=8)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            results[mode] = json.loads(result.stdout)
        (ROOT / 'evidence' / ('python310-wait-signal-comparison-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
        self.assertGreater(results['wait']['caught_after_seconds'], 2)
        self.assertLess(results['sleep']['caught_after_seconds'], 1)
