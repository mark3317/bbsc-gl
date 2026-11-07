"""Read-only finale inventory/native-site checks. Does not compile or run the mod.
Usage: python tools/test_dream_finale_static.py <game/dvdroot_ps4> <decoded eboot.elf>
"""
import re
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'gamedata'))
from emevd import Emevd
from bbfiles import read_bnd4, read_dcx, read_fmg
from esd import Esd
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
    start, increment, commit = map(int, re.search(rf'\{{{event}, (\d+), (\d+), (\d+)\}}', header).groups())
    assert instructions[:2] == [(2000, 2, bytes(4)), (1003, 6, bytes((0, 1, 0, 0)))]
    assert instructions[start][:2] == ((2003, 2) if ending == 1 else (1001, 0))
    assert instructions[commit] == (2003, 2, struct.pack('<II', 6604, 1))
    assert instructions[increment] == (2003, 21, struct.pack('<I', 1))
    assert start < increment < commit
    assert any((b, i) == (2003, 21) for b, i, _ in instructions[start:])
    assert all(k < commit for k, (b, _, _) in enumerate(instructions) if b == 2002)
elf = Path(sys.argv[2]).read_bytes()
assert elf[0x01CFB405 + 0x4000:0x01CFB405 + 0x4006] == bytes.fromhex('888368010000')
assert elf[0x0131FA88 + 0x4000:0x0131FA88 + 0x4008] == bytes.fromhex('8a80680100002401')
assert elf[0x01334BB0 + 0x4000:0x01334BB0 + 0x4008] == bytes.fromhex('554889e54883ec10')
for offset, expected_bytes in {
    0x0203F165: '41bd010000004d89f4',
    0x01C28261: '8951188990cc010000',
    0x0176C470: '554889e583fe01',
    0x012ECF6B: 'c4c17a104608',
    0x019471B1: 'e8ea955800',
    0x01783590: '4983c620',                       # continue with next member
    0x017835F0: 'ba0d00000041b804000000',         # four-byte channel 13 packet
    0x01783681: '4885c0752bbeb1000000',           # null singleton panic branch
    0x017C0FD2: '8b506831c989d6ffc6897068',       # live cycle increment
    0x01944C79: '4189b18c000000',                 # old summon cycle can replace +8C
    0x01944C92: '48b90800000002000000',           # new-cycle load type/subtype
    0x01937D51: '894168',                         # native load commits the descriptor's cycle
    0x01937600: '8b41084189442458',               # descriptor map -> task +58
    0x01938F65: '418b85a4000000',                 # spawn step reads R13 task's load type
    0x0193948E: '83bf8400000003',                 # player creation tests summon phase
    0x013CDDF5: 'e8a629b00084c0741b',             # native stage helper's Stop and success branch
    0x013CDE12: '418986f0000000',                 # native Stop records the selected load type
    0x0178B298: '498b0424483b45d8',               # departure banner's native early exit
}.items():
    expected_bytes = bytes.fromhex(expected_bytes)
    assert elf[offset + 0x4000:offset + 0x4000 + len(expected_bytes)] == expected_bytes, hex(offset)
game = Path(sys.argv[1])
talk = read_bnd4(read_dcx(game / 'script/talk/m21_00_00_00.talkesdbnd.dcx'))
gehrman = Esd(talk['t210305.esd'][1])
assert any(c['eval'][0] == 'f56(6003)' for s in gehrman.groups[0x7FFFFFF2]['states'].values()
           for c in s['conditions'])
workshop = read_bnd4(read_dcx(game / 'script/talk/m21_01_00_00.talkesdbnd.dcx'))
native_dialog = Esd(workshop['t211000.esd'][1])
assert any(bank == 1 and opcode == 17 and [arg[0] for arg in args] == ['2', '10010713', '3', '4', '2']
           for s in native_dialog.groups[0x7FFFFFFB]['states'].values()
           for bank, opcode, args in s['entry'])
assert any('сон охотника' in (read_fmg(data).get(10010713) or '').lower()
           for path in (game / 'msg/rusru').glob('*menu*')
           for _, data in read_bnd4(read_dcx(path)).values())
assert 'bbsc_progress_was_guest) return;' in source
assert source.index('RestoreBbscOwnWorld("before shared ending / NG+")') < source.index('WriteValue<s32>(game_data, 0x68, bbsc_dream_ng_target)')
assert 'BbscQuitInProgress() || BbscDreamFinaleHolding()' in source
assert 'packet.reserved' in source and 'EndingNumber(scene)' in source
assert 'SendBbscSessionLeave' not in source[source.index('void TickBbscDreamFinale() {'):
                                             source.index('bool BbscCutscenesEnabled() {')]
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
