"""Ordered, bounded multipart traffic over independent faulted clients."""
import time,unittest
from test_processes import Tests
class PipelineTests(Tests):
    def test_windowed_chunks_with_latency_reorder_and_recipient_gaps(self):
        a,b=self.group(2,{'seed':442,'delay':.15,'duplicate':.2,'loss':.05})
        self.assertNotIn('error',a.op('acquire'));self.settled()
        frames=[f'WorldFlags:part:{i}' for i in range(64)]
        started=time.monotonic()
        for raw in frames:a.call('relay',data=raw)
        actual=[];end=started+8
        while len(actual)<len(frames) and time.monotonic()<end:
            actual.extend(b.call('received')['frames']);time.sleep(.02)
        self.assertEqual(actual,frames)
        self.assertLess(time.monotonic()-started,8)
        self.assertIsNone(a.state()['relay_error'])

    def test_recipient_gaps_and_new_connection_stream(self):
        a,b,c=self.group(3)
        self.assertNotIn('error',a.op('acquire'));self.settled()
        a.call('relay',data='B-only',recipients=['B'])
        a.call('relay',data='C-only',recipients=['C'])
        a.call('relay',data='both',recipients=['B','C'])
        actual_b=[];actual_c=[];end=time.monotonic()+3
        while time.monotonic()<end and (len(actual_b)<2 or len(actual_c)<2):
            actual_b.extend(b.call('received')['frames']);actual_c.extend(c.call('received')['frames']);time.sleep(.02)
        self.assertEqual(actual_b,['B-only','both']);self.assertEqual(actual_c,['C-only','both'])
        a.call('reset_relay');a.call('relay',data='new-connection',recipients=['B'])
        actual=[];end=time.monotonic()+3
        while time.monotonic()<end and not actual:actual.extend(b.call('received')['frames']);time.sleep(.02)
        self.assertEqual(actual,['new-connection'])
