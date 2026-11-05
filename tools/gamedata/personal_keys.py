"""Read-only audit of all 22 former host-shared goods in original CUSA03173 data.

BB_GAME=dvdroot_ps4 python -B tools/gamedata/personal_keys.py --check
Checks original acquisition paths and production guest permissions, not gameplay.
"""
import argparse
import os
from pathlib import Path
import re
import struct

import bbfiles
import emevd
import esd
import param
from msb import Msb
from quest_reward_rules import variants

ROOT = Path(__file__).resolve().parents[2]
# goods: (route, native lot, map, event if any). Reviewed primary obtainable path.
SOURCES = {
    4000: ('boss', 31000, 'm24_01_00_00', 12411800),
    4006: ('event', 2420900, 'm24_02_00_00', 12420700),
    4009: ('treasure', 2600610, 'm26_00_00_00', 0),
    4010: ('treasure', 2800290, 'm28_00_00_00', 0),
    4012: ('treasure', 3200720, 'm32_00_00_00', 0),
    4013: ('pickup', 3200810, 'm32_00_00_00', 13200400),
    4015: ('treasure', 43221, 'm36_00_00_00', 0),
    4018: ('treasure', 3500800, 'm35_00_00_00', 0),
    4019: ('event', 43010, 'm35_00_00_00', 13501920),
    4020: ('boss', 3501850, 'm35_00_00_00', 13501850),
    4110: ('treasure', 2410290, 'm24_01_00_00', 0),
    4113: ('boss', 15000, 'm21_00_00_00', 12101800),
    4114: ('boss', 50000010, 'm24_01_00_00', 12411700),
    4115: ('treasure', 2400480, 'm24_00_00_00', 0),
    4117: ('covenant', 17001, 'common', 9040),
    4118: ('boss', 50800000, 'm23_00_00_00', 12301700),
    4119: ('treasure', 2420270, 'm24_02_00_00', 0),
    4120: ('event', 43800, 'm34_00_00_00', 13400995),
    4102: ('treasure', 80309020, 'm29_30_90_00/m29_30_90_00', 0),
    4103: ('treasure', 2411000, 'm24_01_00_00', 0),
    4104: ('treasure', 2200360, 'm22_00_00_00', 0),
    4105: ('shop', 80319010, 'm21_00_00_00', 0),
}


def numbers(source, name):
    body = source.split(name + '{', 1)[1].split('};', 1)[0]
    return set(map(int, re.findall(r'\b\d+\b', body)))


def audit():
    bbfiles.GAME = os.environ['BB_GAME']
    game = Path(bbfiles.GAME)
    source = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    assert set(SOURCES) == numbers(source, 'BbscPermanentKeyReceipts') - {4111, 4112, 4116}
    assert len(SOURCES) == 22
    assert 'TickBbscSharedKeyItems' not in source and 'bbsc_keys_admission' not in source
    assert 'TickBbscPermanentKeyReceipts' not in source
    assert 'void TickBbscHostGiftWatch() {' in source
    assert 'TickBbscHostGiftWatch(); }' in source
    for path in ('emulator/mod/bbsc_relay.cpp', 'emulator/src/core/bbsc_relay_client.cpp'):
        dispatcher = (ROOT / path).read_text(encoding='utf-8')
        assert 'OnBbscKeyItemsPacket' not in dispatcher and 'OnBbscKeyItemsRequest' not in dispatcher

    names_bnd = bbfiles.read_bnd4(bbfiles.read_dcx(game / 'msg/rusru/item.msgbnd.dcx'))
    names = bbfiles.read_fmg(names_bnd['アイテム名.fmg'][1])
    layout, _, data, rows = param.load('ItemLotParam')
    shops_l, _, shops_d, shops_rows = param.load('ShopLineupParam')
    boss = source.split('BbscBossRewards{{', 1)[1].split('}};', 1)[0]
    gifts = numbers(source, 'BbscGuestGiftEvents')
    own_flags = numbers(source, 'BbscNpcQuestFlags')
    pickups = source.split('BbscScriptedPickups{{', 1)[1].split('}};', 1)[0]
    evidence = []
    for goods, (route, lot, map_name, event) in SOURCES.items():
        v = param.row_values(layout, data, rows[lot])
        assert any(v[f'lotItemCategory0{j}'] == 4 and v[f'lotItemId0{j}'] == goods and
                   v[f'lotItemNum0{j}'] == 1 and v[f'lotItemBasePoint0{j}'] > 0
                   for j in range(1, 9)), (goods, lot)
        assert names[goods]
        if route == 'treasure':
            msb = Msb(game / 'map/MapStudio' / (map_name + '.msb.dcx'))
            found = []
            for entry, offset in zip(msb.events, msb.lists['EVENT_PARAM_ST']):
                if entry['type'] != 'Treasure':
                    continue
                type_offset = struct.unpack_from('<q', msb.data, offset + 0x20)[0]
                native_lot = struct.unpack_from('<i', msb.data, offset + type_offset + 0x10)[0]
                if native_lot == lot:
                    # The native treasure has an actual item part, not an orphan lot row.
                    item_part = struct.unpack_from('<i', msb.data, offset + type_offset + 8)[0]
                    assert 0 <= item_part < len(msb.parts)
                    found.append(entry['name'])
            assert found, (goods, map_name, lot)
        elif route == 'shop':
            offers = [param.row_values(shops_l, shops_d, offset) for offset in shops_rows.values()]
            offers = [row for row in offers if row['equipType'] == 3 and row['equipId'] == goods]
            assert len(offers) == 5 and all(row['value'] == 10 and row['sellQuantity'] == 1 and
                                           row['eventFlag'] == 6660 for row in offers)
        else:
            file = game / 'event' / (map_name + '.emevd.dcx')
            resolved = [ins for eid, ins in variants(file) if eid == event]
            award_lot = 17000 if route == 'covenant' else lot
            matching = [ins for ins in resolved if any(b == 2003 and n in (4, 36, 43) and
                         a == struct.pack('<i', award_lot) for b, n, a in ins)]
            assert matching, (goods, event, lot)
            if route == 'boss':
                assert re.search(r'\{' + str(event) + r', \d+, ' + str(lot) + r',', boss)
                assert 'bool IsBbscNativeRewardLot(s32 lot)' in source
                assert 'GiveBbscBossGoods' not in source
            else:
                assert event in gifts or str(event) in pickups
                if route == 'pickup':
                    assert event in own_flags
                if route == 'covenant':
                    # Native award of 17000 also processes contiguous lot 17001.
                    assert lot == award_lot + 1 and 9042 in own_flags
                    talk = bbfiles.read_bnd4(bbfiles.read_dcx(
                        game / 'script/talk/m25_00_00_00.talkesdbnd.dcx'))
                    commands = esd.Esd(talk['t250307.esd'][1]).all_commands()
                    assert any(row[2:] == (6, 2147483642, ['72500336', '9042']) for row in commands)
        evidence.append((goods, names[goods], route, lot, map_name, event))

    # The discovered badge blocker: exact native client gate, original death
    # trigger and first/repeat reward remain intact; no world-changing actions.
    f = game / 'event/m34_00_00_00.emevd.dcx'
    ins = next(ins for eid, ins in variants(f) if eid == 13400995)
    assert ins[1] == (1003, 6, struct.pack('<I', 256))
    assert ins[2] == (3, 0, struct.pack('<ii', 256, 13400970))
    assert ins[4] == (2003, 4, struct.pack('<i', 43800))
    assert ins[6] == (2003, 4, struct.pack('<i', 43802))
    assert {(b, n) for b, n, _ in ins if b >= 2000} == {(2003, 4)}
    evd = emevd.Emevd(f)
    count, start = struct.unpack_from('<qq', evd.data, 0x10)
    params = struct.unpack_from('<q', evd.data, 0x58)[0]
    for k in range(count):
        eid, _, _, n, off = struct.unpack_from('<qqqqq', evd.data, start + k * 0x30)
        if eid == 13400995:
            assert all(struct.unpack_from('<q', evd.data, params + off + j * 0x20)[0] != 1
                       for j in range(n)), 'client gate must never receive parameter substitutions'
    assert {6671, 13400995} <= own_flags and '13400995, true' in pickups
    for row in evidence:
        print(' | '.join(map(str, row)))
    print('PASS: 22 original personal sources; retired host packets; native badge blocker reviewed')


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.parse_args()
    audit()
