"""System exit uses native teardown; HTTP Party readiness cannot replace its ordering."""
from pathlib import Path
import runpy
ns=runpy.run_path(str(Path(__file__).with_name('test_menu_quit.py')))
source=ns['function']('void PS4_SYSV_ABI BbscNativeQuitConfirmHook(u64, const GuestRegisterSnapshot* registers)')
assert 'PartyTitleReady' not in source and 'PartyCancel' not in source
assert 'TickBbscPendingQuit' not in ns['SOURCE']
ns['run']()
print('PASS: Party cancellation observes the native Stop once; no HTTP title gate or custom pending/save/Stop sequence')
