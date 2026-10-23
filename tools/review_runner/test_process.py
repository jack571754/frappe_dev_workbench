import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from processes import run_process


@unittest.skipUnless(os.name == 'posix', '执行器运行于 WSL')
class ProcessTests(unittest.TestCase):
    def test_cancel_stops_material_worker_and_next_task_can_run(self):
        with tempfile.TemporaryDirectory() as root:
            marker = str(Path(root, 'should-not-exist'))
            started = time.monotonic()
            def cancelled():
                if time.monotonic() - started > .15:
                    raise TimeoutError('cancelled')
            with self.assertRaises(TimeoutError):
                run_process([sys.executable, '-c',
                    "import time; from pathlib import Path; time.sleep(1); Path(%r).write_text('bad')" % marker], cancelled)
            self.assertLess(time.monotonic() - started, 1)
            time.sleep(1)
            self.assertFalse(Path(marker).exists())
            self.assertEqual(run_process([sys.executable, '-c', 'print("next")'], lambda: None).strip(), 'next')

    def test_cleanup_still_reaps_process_when_container_removal_fails(self):
        def cancelled():
            raise TimeoutError()
        def cleanup_failure():
            raise RuntimeError('Docker unavailable')
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            run_process([sys.executable, '-c', 'import time; time.sleep(20)'], cancelled,
                        on_cancel=cleanup_failure)
        self.assertLess(time.monotonic() - started, 2)
