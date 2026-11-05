"""Generate conservative personal-quest event rules for CUSA03173 1.09.

python -I tools/gamedata/quest_event_rules.py [--check]

Localize personal flag workers and the original personal NPC state dispatchers.
The latter reuse the existing original-data controller review, without adding
runtime stage predicates or changing their character/object instructions.
Separately identify ItemLot get flags written by scripts: their value alone
cannot prove that a player received that item.
"""
import argparse
import os
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bbfiles
import emevd
import param

ROOT = Path(__file__).resolve().parents[2]
CPP = ROOT / 'emulator/src/core/bloodborne_re.cpp'
HEADER = ROOT / 'emulator/src/core/bbsc_quest_event_rules.h'
bbfiles.GAME = os.environ.get('BB_GAME', r'D:\Games\Bloodborne\game\dvdroot_ps4')


def numbers(source, name):
    block = source.split(name + '{', 1)[1].split('};', 1)[0]
    return set(map(int, re.findall(r'\b\d+\b', block)))


def host_gate(instructions):
    return any(b == 4 and n == 3 and len(a) == 12 and
               struct.unpack_from('<ii', a, 4) == (10000, 0)
               for b, n, a in instructions)


def personal_writes(instructions, npc):
    wrote = False
    for b, n, a in instructions:
        if b < 2000:
            continue
        if b == 2000 and n in (2, 5):
            continue
        if b == 2003 and n == 2 and len(a) == 8:
            flag, value = struct.unpack('<II', a)
            if flag not in npc or value not in (0, 1):
                return False
            wrote = True
        elif b == 2003 and n == 22 and len(a) == 12:
            lo, hi, value = struct.unpack('<III', a)
            # Native state changes clear the whole 20-bit NPC family, including
            # unused states absent from the literal talk-flag catalogue.
            if not (0 <= hi - lo < 100 and value in (0, 1) and
                    (all(f in npc for f in range(lo, hi + 1)) or
                     (value == 0 and 1100 <= lo <= hi < 2000 and
                      lo // 20 == hi // 20 and lo in npc))):
                return False
            wrote = True
        else:
            return False  # includes child events, awards, warps and world effects
    return wrote


def generate():
    source = CPP.read_text(encoding='utf-8')
    npc = numbers(source, 'BbscNpcQuestFlags')
    # A personal quest's original visibility dispatcher must be local just like
    # its flag workers. Otherwise native channel31 can move another player's
    # dispatcher past THEIR conditions and replay character state here.
    # Reuse reviewed original controllers, not the reward-allowed predicates:
    # the game's own branches still decide every appearance/disappearance.
    from quest_reward_rules import generate as generate_npc_rules
    _, npc_rules, _ = generate_npc_rules(bbfiles.GAME)
    controllers = {event for event, _ in npc_rules.values()}
    events = {}
    scripted = set()
    ranges = []
    for file in sorted((Path(bbfiles.GAME) / 'event').glob('*.emevd.dcx')):
        for eid, instructions in emevd.Emevd(file).events:
            if eid in controllers:
                # An explicit later SetNetworkSyncState(true) would undo the
                # existing pre-step localization and needs a separate review.
                assert not any(b == 2000 and n == 2 and any(a)
                               for b, n, a in instructions), (file.name, eid)
                events[eid] = file.name
            for b, n, a in instructions:
                if b == 2003 and n == 2 and len(a) == 8:
                    scripted.add(struct.unpack_from('<I', a)[0])
                elif b == 2003 and n == 22 and len(a) == 12:
                    lo, hi = struct.unpack_from('<II', a)
                    if 0 <= hi - lo <= 10000:
                        ranges.append((lo, hi))
            # Already guest-enabled workers also need local network authority.
            # Otherwise a host's synchronized action can bypass the guest's
            # own condition evaluator (including the NPC-death prerequisite).
            if host_gate(instructions) and personal_writes(instructions, npc):
                events[eid] = file.name
            if eid == 12410702:
                # Sister's window proxies and quest corpse, not a shared door/enemy.
                effects = {(b, n) for b, n, _ in instructions if b >= 2000}
                assert effects == {(2003, 2), (2005, 3), (2005, 4), (2005, 8),
                                   (2004, 30), (2004, 12)}
                assert host_gate(instructions)
                assert any(b == 2005 and n == 4 and struct.unpack('<ii', a) == (2410851, 0)
                           for b, n, a in instructions)
                events[eid] = file.name
    assert {12410702, 12410713, 12410748, 12410761, 12410803, 12410804} <= events.keys()
    assert controllers <= events.keys()
    layout, _, data, rows = param.load('ItemLotParam')
    get_flags = set()
    for offset in rows.values():
        v = param.row_values(layout, data, offset)
        get_flags.add(v['getItemFlagId'])
        get_flags.update(v[f'getItemFlagId0{k}'] for k in range(1, 9))
    gates = sorted(f for f in get_flags if f > 0 and
                   (f in scripted or any(lo <= f <= hi for lo, hi in ranges)))
    lines = ['// Generated by tools/gamedata/quest_event_rules.py; CUSA03173 1.09.',
             '#pragma once', '#include <array>', '#include <cstdint>',
             'namespace Core::Bloodborne::QuestRules {']
    lines.append(f'inline constexpr std::array<std::int64_t, {len(events)}> LocalEvents{{')
    lines.extend(f'    {eid}, // {events[eid]}' for eid in sorted(events))
    lines.append('};')
    lines.append(f'inline constexpr std::array<std::uint32_t, {len(gates)}> ScriptedLotFlags{{')
    lines.extend(f'    {f},' for f in gates)
    lines.extend(['};', '} // namespace Core::Bloodborne::QuestRules', ''])
    return '\n'.join(lines), events, gates


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text, events, gates = generate()
    if args.check:
        assert HEADER.read_text(encoding='utf-8') == text, 'quest rules need regeneration'
    else:
        HEADER.write_text(text, encoding='utf-8', newline='\n')
    print(f'{len(events)} personal events; {len(gates)} scripted lot flags; check={args.check}')
