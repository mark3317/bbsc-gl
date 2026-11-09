"""Diagnostic event output must not touch disk or session state in release mode."""
import io, json, tempfile, threading, unittest
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
            service.file_diagnostics=True
            service.run_log=None
            service.log_lock=threading.Lock()
            service.logfile=Path(tmp)/'events.jsonl'
            service.e=SimpleNamespace(id='A',state={'generation':7})
            service.log('np_reply',command=104)
            event=json.loads(service.logfile.read_text())
            self.assertEqual((event['event'],event['command'],event['generation']),('np_reply',104,7))
            # A diagnostic file that cannot be opened must not fail the RPC.
            service.logfile=Path(tmp)
            service.log('np_reply',command=105)

    def test_one_diagnostic_sink_can_fail_without_stopping_the_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Compatibility.__new__(Compatibility)
            service.diagnostics=service.file_diagnostics=True
            service.log_lock=threading.Lock()
            service.e=SimpleNamespace(id='A',state={'generation':7})
            service.logfile=Path(tmp)
            service.run_log=io.StringIO()
            service.log('relay_fenced',peer='B')
            self.assertIn('"event": "relay_fenced"',service.run_log.getvalue())
            service.run_log.close()
            service.logfile=Path(tmp)/'events.jsonl'
            service.log('relay_recovered',peer='B')
            self.assertEqual(json.loads(service.logfile.read_text())['event'],'relay_recovered')

if __name__=='__main__':unittest.main()
