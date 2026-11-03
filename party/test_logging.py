"""Diagnostic event output must not touch disk or session state in release mode."""
import json, tempfile, threading, unittest
from pathlib import Path
from types import SimpleNamespace
from compat import Compatibility

class LoggingTests(unittest.TestCase):
    def test_release_skips_io_and_diagnostic_mode_records_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Compatibility.__new__(Compatibility)
            service.diagnostics=False
            # Neither a lock, engine nor output file is needed in release.
            service.log('np_reply',command=104)
            service.diagnostics=True
            service.log_lock=threading.Lock()
            service.logfile=Path(tmp)/'events.jsonl'
            service.e=SimpleNamespace(id='A',state={'generation':7})
            service.log('np_reply',command=104)
            event=json.loads(service.logfile.read_text())
            self.assertEqual((event['event'],event['command'],event['generation']),('np_reply',104,7))

if __name__=='__main__':unittest.main()
