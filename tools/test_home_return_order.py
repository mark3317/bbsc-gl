"""Source control-flow checks for the shared native/fallback return transaction."""
from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')

def body(name):
    start = SOURCE.index(name)
    start = SOURCE.index('{', start)
    end, depth = start + 1, 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end]

class ReturnOrder(unittest.TestCase):
    def test_native_claims_before_continuing_and_duplicate_returns(self):
        native = body('void PS4_SYSV_ABI BbscSendPhantomHomeHook(')
        duplicate = body('if (bbsc_home_return_claimed)')
        self.assertIn('bbsc_send_home_skip = 1;', duplicate)
        self.assertIn('return;', duplicate)
        self.assertNotIn('bbsc_release_leave_locks = true', duplicate)
        self.assertLess(native.index('if (bbsc_home_return_claimed)'), native.index('bbsc_home_return_claimed = true;'))

    def test_fallback_waits_for_native_and_shares_claim(self):
        fallback = body('void TickBbscStrandedGuest()')
        self.assertIn("constexpr s64 BbscStrandedMs = 15'000;", SOURCE)
        self.assertIn('BbscConfirmedHostLeaveMs : BbscStrandedMs', fallback)
        self.assertIn('if (bbsc_home_return_claimed || now - since_ms < grace)', fallback)
        self.assertLess(fallback.index('bbsc_home_return_claimed = true;'), fallback.index('WriteValue<s32>(event_state'))
        self.assertLess(fallback.index('bbsc_home_return_claimed = true;'), fallback.index('reinterpret_cast<HomePoint>'))

    def test_failed_prerequisites_do_not_claim(self):
        native = body('void PS4_SYSV_ABI BbscSendPhantomHomeHook(')
        claim = native.index('bbsc_home_return_claimed = true;')
        self.assertLess(native.index('!IsSprjLuaEventManReady()'), claim)
        self.assertLess(native.index('GetBbscLocalPlayerHp() <= 0'), claim)
        fallback = body('void TickBbscStrandedGuest()')
        self.assertLess(fallback.index('!IsSprjLuaEventManReady()'), fallback.index('bbsc_home_return_claimed = true;'))

    def test_load_does_not_reset_ownership(self):
        fallback = body('void TickBbscStrandedGuest()')
        reset = fallback[:fallback.index('static s64 last_ms')]
        self.assertIn('BbscOwnWorldNonGuest(current_global)', reset)
        self.assertIn('ReadValue<u8>(current_global, 0x08) == 0', reset)
        self.assertIn('current_state == 6 && bbsc_persistence_restore_at_ms == 0', reset)
        self.assertIn('since_ms = 0;', reset)

if __name__ == '__main__':
    unittest.main()
