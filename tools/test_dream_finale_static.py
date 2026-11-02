"""Read-only finale inventory/native-site checks. Does not compile or run the mod.
Usage: python tools/test_dream_finale_static.py <game/dvdroot_ps4> <decoded eboot.elf>
"""
import re
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'gamedata'))
from emevd import Emevd
root = Path(__file__).resolve().parents[1]
source = (root / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf8')
header = (root / 'emulator/src/core/bbsc_dream_finale.h').read_text(encoding='utf8')
events = dict(Emevd(Path(sys.argv[1]) / 'event/m21_00_00_00.emevd.dcx').events)
expected = {12100180: (1, {21000010, 21001010}),
            12100000: (2, {21000020}), 12100002: (3, {21000030, 21001030})}
for event, (ending, scenes) in expected.items():
    instructions = events[event]
    actual = {struct.unpack_from('<I', a)[0] for b, i, a in instructions if b == 2002}
    assert actual == scenes, (event, actual)
    writes = {struct.unpack_from('<I', a)[0] for b, i, a in instructions if (b, i) == (2003, 2)}
    assert {6599 + ending, 6603, 6604, 20 + ending} <= writes
    assert any((b, i) == (2003, 21) for b, i, a in instructions)
    assert all(str(scene) in header for scene in scenes)
elf = Path(sys.argv[2]).read_bytes()
assert elf[0x01CFB405 + 0x4000:0x01CFB405 + 0x4006] == bytes.fromhex('888368010000')
assert elf[0x0131FA88 + 0x4000:0x0131FA88 + 0x4008] == bytes.fromhex('8a80680100002401')
assert elf[0x01334BB0 + 0x4000:0x01334BB0 + 0x4008] == bytes.fromhex('554889e54883ec10')
assert 'bbsc_progress_was_guest) return;' in source
assert source.index('RestoreBbscOwnWorld("before shared ending / NG+")') < source.index('WriteValue<s32>(game_data, 0x68, bbsc_dream_ng_target)')
assert 'BbscQuitInProgress() || BbscDreamFinaleHolding()' in source
assert 'packet.reserved' in source and 'EndingNumber(scene)' in source
assert '12104801,' not in header and '12104851,' not in header
print('PASS: three native endings, five scenes, native Remo/start/NG sites and source ordering')
print('Static checks only; gameplay and complete translation-unit compilation are NOT verified.')

assert 'reinterpret_cast<Increment>' not in source
assert 'record.checksum != BbscFinaleChecksum(record)' in source
assert 'std::filesystem::resize_file(path, valid, ec)' in source
assert 'SaveBbscFinale(2, bbsc_finale_record.packet)' in source
assert 'SaveBbscFinale(4, bbsc_finale_record.packet)' in source
assert 'bbsc_finale_save_result.load() == 0' in source
assert 'slot->user != bbsc_finale_slot->user' in source
assert 'record.packet.reserved < 1 || record.packet.reserved > 7' in source
start = source.index('void CompleteBbscSharedEndingAtHome()')
end = source.index('// Observe the actual native start', start)
body = source[start:end]
assert 'StageTransition>(' not in body and 'HomePoint>(' not in body
assert 'ReadValue<u64>(slots, 8)' in body
print('PASS: journal checksum/torn-tail/character gates, save acknowledgement, absolute cycle and no home warp')
