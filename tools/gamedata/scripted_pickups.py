"""Read-only survey of every native action-button item award (BB_GAME=dvdroot_ps4).

The allowlist is reviewed, never inferred from the mere presence of an award.
Run with --check to verify production rules, original prerequisites and coverage.
"""
import argparse
import os
from pathlib import Path
import re
import struct

import bbfiles
import emevd
import param
from quest_reward_rules import variants

ROOT = Path(__file__).resolve().parents[2]
# event: (map, lot, receipt, object, action, client-gated)
REVIEWED = {
    12110300: ('m21_01_00_00', 2110800, 52110800, 2111100, 2110010, True),
    12110301: ('m21_01_00_00', 2110810, 52110810, 2111101, 2110011, True),
    12110302: ('m21_01_00_00', 2110000, 52110000, 2111102, 2110012, True),
    12300130: ('m23_00_00_00', 2300170, 52300170, 2301500, 2300000, False),
    12410510: ('m24_01_00_00', 2410990, 52410990, 2411200, 2410060, False),
    12500600: ('m25_00_00_00', 2500910, 52500910, 2500851, 2500040, True),
    12501803: ('m25_00_00_00', 2502000, 52502000, 2500850, 2500030, True),
    12600125: ('m26_00_00_00', 2600570, 52600570, 2601008, 2600030, True),
    13200400: ('m32_00_00_00', 3200810, 53200810, 3201010, 3200010, False),
    13400320: ('m34_00_00_00', 3401810, 9470, 3401500, 3400100, False),
    13501803: ('m35_00_00_00', 3501800, 53501800, 3501801, 3500911, False),
}
FLAG_REWARDS = {13400995}
EXCEPTIONS = {
    12105064: 'Dream messenger accessories: already enabled by Dream rules; not a ground pickup',
    12600180: 'Patches trap/random reward: timed trap, animation and object activation; not a static pickup',
    12700902: 'Gold Ardeo: personal Alfred quest dispatcher/proxy requires a separate quest-chain repair',
    12800920: 'Unused parameterized template: no InitializeEvent caller in original game scripts',
    13501141: 'Laurence skull: also changes shared boss flag13401852 and NPC flags3400..3403; not a pure pickup',
}
ACTION = {5, 13, 18, 19, 24, 27}


def survey():
    bbfiles.GAME = os.environ['BB_GAME']
    source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    table = source.split('BbscScriptedPickups{{', 1)[1].split('}};', 1)[0]
    rules = {int(e): (int(m, 16), c == 'true') for m, e, c in
             re.findall(r'\{(0x[0-9A-Fa-f]+), (\d+), (true|false)\}', table)}
    assert set(rules) == set(REVIEWED) | FLAG_REWARDS
    flags = set(map(int, re.findall(r'\b\d+\b', source.split('BbscNpcQuestFlags{', 1)[1].split('};', 1)[0])))
    layout, _, data, lots = param.load('ItemLotParam')
    files = bbfiles.read_bnd4(bbfiles.read_dcx(Path(bbfiles.GAME) / 'msg/rusru/item.msgbnd.dcx'))
    names = {4: bbfiles.read_fmg(files['アイテム名.fmg'][1]),
             1: bbfiles.read_fmg(files['防具名.fmg'][1])}
    found, resolved, raw, called = set(), {}, {}, set()
    for file in sorted((Path(bbfiles.GAME) / 'event').glob('*.emevd.dcx')):
        evd = emevd.Emevd(file)
        for event, instructions in evd.events:
            for bank, op, args in instructions:
                if bank == 2000 and op in (0, 6) and len(args) >= 8:
                    called.add(struct.unpack_from('<i', args, 4)[0])
            if any(b == 3 and n in ACTION for b, n, _ in instructions) and any(
                    b == 2003 and n in (4, 36, 43) for b, n, _ in instructions):
                found.add(event)
            if event in REVIEWED:
                raw[event] = instructions
                assert file.stem.split('.')[0] == REVIEWED[event][0]
                # A role gate must not use per-instance inline argument substitution.
                count, start = struct.unpack_from('<qq', evd.data, 0x10)
                parameters = struct.unpack_from('<q', evd.data, 0x58)[0]
                for k in range(count):
                    eid, _, _, n, off = struct.unpack_from('<qqqqq', evd.data, start + k * 0x30)
                    if eid == event:
                        for j in range(n):
                            index = struct.unpack_from('<q', evd.data, parameters + off + j * 0x20)[0]
                            assert instructions[index][:2] != (1003, 6)
        for event, instructions in variants(file):
            if event in REVIEWED:
                assert event not in resolved, f'multiple native slots require review: {event}'
                resolved[event] = instructions
    assert found == set(REVIEWED) | set(EXCEPTIONS), f'unreviewed/removed action awards: {found ^ (set(REVIEWED) | set(EXCEPTIONS))}'
    assert set(resolved) == set(REVIEWED)
    assert 12800920 not in called, 'previously unused pickup template now needs review'
    for event, (map_name, lot, receipt, obj, action, client) in REVIEWED.items():
        instructions = resolved[event]
        map_id = int(map_name[1:3]) << 24 | int(map_name[4:6]) << 16
        assert rules[event] == (map_id, client)
        assert event in flags, f'completion must stay personal: {event}'
        assert (2006, 4, struct.pack('<iii', obj, 200, 900201)) in instructions
        assert (3, 24, struct.pack('<iii', 0, action, obj)) in instructions
        assert (2006, 5, struct.pack('<ii', obj, 1)) in instructions
        assert [(n, a) for b, n, a in instructions if b == 2003 and n in (4, 36, 43)] == [(4, struct.pack('<i', lot))]
        assert any(b == 1003 and n == 6 and a == struct.pack('<I', 256) for b, n, a in instructions) == client
        if not client:
            assert any(b == 4 and n == 3 and a[4:] == struct.pack('<ii', 10000, 0) for b, n, a in instructions)
        effects = {(b, n) for b, n, _ in instructions if b >= 2000}
        expected = {(2003, 4), (2006, 4), (2006, 5)}
        if event != 12300130:
            expected.add((2003, 18))  # native pickup animation only
        if event == 12410510:
            expected.add((2003, 2))
            assert (2003, 2, struct.pack('<ii', 12410511, 1)) in instructions
            assert 12410511 in flags
        assert effects == expected, (event, effects)
        v = param.row_values(layout, data, lots[lot])
        assert v['getItemFlagId'] == receipt
        if receipt < 50_000_000:
            assert receipt in flags
        items = [(v[f'lotItemCategory0{k}'], v[f'lotItemId0{k}'], v[f'lotItemNum0{k}'])
                 for k in range(1, 9) if v[f'lotItemId0{k}'] > 0]
        print(event, map_name, '; '.join(f'{names.get(c, {}).get(i, i)} x{n}' for c, i, n in items))
    # Explicit availability prerequisites remain in the native script, never bypassed.
    assert (3, 0, struct.pack('<ii', 256, 12500810)) in raw[12500600]
    assert (3, 0, struct.pack('<ii', 256, 12501800)) in raw[12501803]
    assert (3, 0, struct.pack('<ii', 256, 13501800)) in raw[13501803]
    for event, reason in EXCEPTIONS.items():
        print('REVIEW', event, reason)
    print(f'PASS: all {len(found)} action-award definitions surveyed; {len(REVIEWED)} reviewed pickups')


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='all checks always run; no files are written')
    parser.parse_args()
    survey()
