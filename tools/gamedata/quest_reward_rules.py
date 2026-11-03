"""Extract simple NPC state dispatchers; never infer gates from receipt flags.

BB_GAME points to the read-only dvdroot_ps4. Complex/parameterized dispatchers
are reported for review, not flattened into guessed prerequisites.
"""
import os
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bbfiles
import emevd
import msb
import param

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / 'emulator/src/core/bbsc_quest_reward_rules.h'


def variants(file):
    """Resolve literal local InitializeEvent arguments using the EVD parameter table."""
    evd = emevd.Emevd(file)
    data = evd.data
    event_count, events_off = struct.unpack_from('<qq', data, 0x10)
    parameter_off = struct.unpack_from('<q', data, 0x58)[0]
    parameters = {}
    for k in range(event_count):
        event, _, _, count, offset = struct.unpack_from('<qqqqq', data, events_off + k * 0x30)
        parameters[event] = [struct.unpack_from('<qqqii', data, parameter_off + offset + j * 0x20)
                             for j in range(count)]
    events = dict(evd.events)
    for event, instructions in evd.events:
        if not parameters[event]:
            yield event, instructions
    for _, instructions in evd.events:
        for bank, op, args in instructions:
            if bank != 2000 or op != 0 or len(args) < 8:
                continue
            event = struct.unpack_from('<i', args, 4)[0]
            if event not in events or not parameters[event]:
                continue
            payload = args[8:]
            resolved = [(b, n, bytearray(a)) for b, n, a in events[event]]
            for index, dest, src, length, _ in parameters[event]:
                assert src + length <= len(payload) and dest + length <= len(resolved[index][2])
                resolved[index][2][dest:dest + length] = payload[src:src + length]
            yield event, [(b, n, bytes(a)) for b, n, a in resolved]


def extract(instructions, reviewed_tail=False):
    runs, run = [], []
    for j, (bank, op, args) in enumerate(instructions):
        branch = []
        if bank == 1003 and op == 101 and len(args) == 8:
            label, on, flag = struct.unpack('<BBxxi', args)
            if on == 1 and 1100 <= flag < 2000:
                branch = [(j, label, flag)]
        elif bank == 1003 and op == 103 and len(args) == 12:
            label, mode, lo, hi = struct.unpack('<BBxxii', args)
            # RangeState.AnyOn=2 is an ordered OR of these literal flags.
            if mode == 2 and 1100 <= lo <= hi < 2000 and hi - lo < 100:
                branch = [(j, label, flag) for flag in range(lo, hi + 1)]
        if branch:
            run.extend(branch)
        else:
            if run:
                runs.append(run)
            run = []
    if run:
        runs.append(run)
    branches = max(runs, key=lambda run: len({j for j, _, _ in run}), default=[])
    targets = {struct.unpack('<i', a)[0] for b, n, a in instructions
               if b == 2004 and n == 37 and len(a) == 4}
    if len({j for j, _, _ in branches}) < 2 or not targets or 0 in targets:
        return None
    def label_after(label, pc):
        # EMEVD searches forward; initialization and dispatch may reuse labels.
        return next((j + 1 for j, (b, n, _) in enumerate(instructions)
                     if j > pc and b == 1014 and n == label), len(instructions))
    results = {}
    prefix_backread, prefix_enabled = {}, {}
    prefix_start = max((j + 1 for j, (b, n, a) in enumerate(instructions[:branches[0][0]])
                        if b in (1000, 1003, 1014) or (b == 2000 and n in (0, 6))), default=0)
    for b, n, a in instructions[prefix_start:branches[0][0]]:
        if b == 2004 and n in (5, 29) and len(a) == 8:
            entity, value = struct.unpack('<ii', a)
            (prefix_backread if n == 29 else prefix_enabled)[entity] = bool(value) if n == 5 else not value
    # Preserve branch order, including duplicate flags: the first match wins.
    for flag in [0] + list(dict.fromkeys(x[2] for x in branches)):
        pc = next((label_after(label, j) for j, label, f in branches if f == flag),
                  branches[-1][0] + 1)
        pending = [(pc, dict(prefix_backread), dict(prefix_enabled), set(), frozenset())]
        outcomes = []
        while pending:
            pc, backread, enabled, drops, visited = pending.pop()
            while pc < len(instructions) and pc not in visited:
                visited = visited | {pc}
                bank, op, args = instructions[pc]
                if bank == 1000 and op == 4:
                    break
                if bank == 1000 and op == 103:
                    pc = label_after(struct.unpack('<i', args)[0], pc)
                    continue
                if (bank == 1003 and op in (101, 103)) or (bank == 1000 and op == 101):
                    # Unknown subconditions: explore BOTH paths. A state is
                    # forbidden only when every native path makes it inactive.
                    pending.append((label_after(args[0], pc), dict(backread), dict(enabled), set(drops), visited))
                elif bank in (1000, 1003) and op == 1:
                    pending.append((pc + 1 + args[0], dict(backread), dict(enabled), set(drops), visited))
                elif bank in (1000, 1003) and op in (2, 6):
                    pending.append((len(instructions), dict(backread), dict(enabled), set(drops), visited))
                elif bank == 2000 and op == 0 and reviewed_tail and all(
                        b == 2000 and n == 0 for b, n, _ in instructions[pc:]):
                    break  # child activation invariants are checked below
                elif bank in (1000, 1003) or (bank == 2000 and op in (0, 6)):
                    return None  # unresolved control/callee can affect this actor
                if bank == 2004 and op == 29 and len(args) == 8:
                    entity, disabled = struct.unpack('<ii', args)
                    backread[entity] = not disabled
                if bank == 2004 and op == 5 and len(args) == 8:
                    entity, value = struct.unpack('<ii', args)
                    enabled[entity] = bool(value)
                if bank == 2004 and op == 37 and len(args) == 4:
                    drops.add(struct.unpack('<i', args)[0])
                pc += 1
            if (pc in visited and pc < len(instructions) and instructions[pc][:2] != (1000, 4)
                    and not (reviewed_tail and instructions[pc][:2] == (2000, 0))):
                return None
            outcomes.append({entity: (backread.get(entity, True) and enabled.get(entity, True)) or entity in drops
                             for entity in targets})
            if len(outcomes) + len(pending) > 64:
                return None
        # Unknown actor state preserves native behavior; never guess a denial.
        results[flag] = {entity: any(path[entity] for path in outcomes) for entity in targets}
    if any(results[0].values()):
        return None  # unknown/default state must not be guessed
    return {entity: [(flag, results[flag][entity]) for _, _, flag in branches]
            for entity in sorted(targets)}


def generate(game):
    bbfiles.GAME = str(game)
    rules, skipped, death_sources, forced_sources = {}, [], set(), set()
    production = (ROOT / 'emulator/src/core/bloodborne_re.cpp').read_text(encoding='utf-8')
    import re
    guests = set(map(int, re.findall(r'\b\d+\b', production.split('BbscGuestGiftEvents{', 1)[1].split('};', 1)[0])))
    for file in sorted(Path(game, 'event').glob('*.emevd.dcx')):
        resolved = list(variants(file))
        events = dict(emevd.Emevd(file).events)
        for event, instructions in resolved:
            for b, n, a in instructions:
                if b == 4 and n == 0 and len(a) == 12 and event in guests:
                    _, entity, dead = struct.unpack('<iii', a)
                    if dead == 1:
                        death_sources.add(entity)
                if b == 2004 and n == 37 and len(a) == 4:
                    forced_sources.add(struct.unpack('<i', a)[0])
            if not any(b == 2004 and n == 37 for b, n, a in instructions):
                continue
            found = extract(instructions, event in (12400650, 12410800))
            if found is None:
                skipped.append((file.name, event))
                continue
            for entity, states in found.items():
                assert entity not in rules or rules[entity] == (event, states), (entity, event)
                rules[entity] = (event, states)
            if event in (12400650, 12410800):
                # These two dispatchers start their personal quest workers at
                # their common tail. Every child activation of a parent actor
                # must first select a state that the parent permits.
                for b, n, a in instructions:
                    if b != 2000 or n != 0:
                        continue
                    child = events[struct.unpack_from('<i', a, 4)[0]]
                    selected = None
                    for cb, cn, ca in child:
                        if cb == 2003 and cn == 2 and len(ca) == 8:
                            flag, value = struct.unpack('<ii', ca)
                            if value == 1 and 1100 <= flag < 2000:
                                selected = flag
                        if cb == 2004 and cn == 29 and len(ca) == 8:
                            actor, off = struct.unpack('<ii', ca)
                            if off == 0 and actor in found:
                                assert selected is not None and next(
                                    (ok for f, ok in found[actor] if f == selected), False), (event, actor, selected)
        # Two secondary actors are activated by an explicit positive quest
        # wait, rather than by the main state switch. Derive their terminal
        # states from the corresponding native death handlers.
        secondary = {12400655: (2400901, {1370}, (12400654,)),
                     12410809: (2410901, {1363, 1364, 1365, 1368, 1369}, (12410803, 12410804))}
        for event, (entity, active, deaths) in secondary.items():
            if event not in events:
                continue
            instructions = events[event]
            assert (2004, 29, struct.pack('<ii', entity, 0)) in instructions
            waits = {struct.unpack_from('<i', a, 4)[0] for b, n, a in instructions
                     if b == 3 and n == 0 and len(a) == 8 and a[1] == 1
                     and min(active) // 20 == struct.unpack_from('<i', a, 4)[0] // 20}
            assert waits == active
            terminal = set()
            for death in deaths:
                child = events[death]
                assert any(b == 4 and n == 0 and struct.unpack('<iii', a)[1:] == (entity, 1)
                           for b, n, a in child if len(a) == 12)
                terminal.update(struct.unpack('<ii', a)[0] for b, n, a in child
                    if b == 2003 and n == 2 and len(a) == 8 and struct.unpack('<ii', a)[1] == 1)
            assert all(1100 <= flag < 2000 for flag in terminal)
            rules[entity] = (event, [(flag, True) for flag in sorted(active | terminal)])
    # 2400700 has an ordinary always-present NPC death path; there is no
    # hidden/future quest variant to authorize. Every other identified personal
    # death -> NPC-treasure chain must have a reviewed state prerequisite.
    uncovered = (death_sources & forced_sources) - rules.keys() - {2400700}
    assert not uncovered, f'personal death rewards need state review: {sorted(uncovered)}'
    assert rules[2410781] == (12410760, [(1240, False), (1241, False),
        (1242, False), (1243, False), (1244, False), (1246, True), (1245, True)])
    nl, _, nd, nr = param.load('NpcParam')
    ll, _, ld, lr = param.load('ItemLotParam')
    receipts = set()
    for file in sorted(Path(game, 'map/MapStudio').glob('*.msb.dcx')):
        mapdata = msb.Msb(file)
        for part, offset in zip(mapdata.parts, mapdata.lists['PARTS_PARAM_ST']):
            entity = part['entity_id']
            if entity not in rules or part['type'] not in ('Enemy', 'DummyEnemy'):
                continue
            type_offset = struct.unpack_from('<q', mapdata.data, offset + 0xB8)[0]
            npc = struct.unpack_from('<i', mapdata.data, offset + type_offset + 0xC)[0]
            assert npc in nr, (file, entity, npc)
            row = param.row_values(nl, nd, nr[npc])
            for k in range(1, 7):
                lot = row[f'itemLotId_{k}']
                if lot not in lr:
                    continue
                reward = param.row_values(ll, ld, lr[lot])
                for flag in [reward['getItemFlagId']] + [reward[f'getItemFlagId0{k}'] for k in range(1, 9)]:
                    if flag > 0:
                        receipts.add((flag, entity))
    assert (50001300, 2410781) in receipts
    lines = ['// Generated from original CUSA03173 1.09 by quest_reward_rules.py.',
             '#pragma once', '#include <algorithm>', '#include <array>', '#include <cstdint>',
             'namespace Core::Bloodborne::QuestRules {',
             'struct NpcRewardState { std::uint32_t entity, flag; bool allowed; };']
    count = sum(len(states) for _, states in rules.values())
    lines.append(f'inline constexpr std::array<NpcRewardState, {count}> NpcRewardStates{{{{')
    for entity, (event, states) in sorted(rules.items()):
        lines.append(f'    // Native state dispatcher {event}, entity {entity}.')
        lines.extend(f'    {{{entity}, {flag}, {str(allowed).lower()}}},'
                     for flag, allowed in states)
    lines.extend(['}};',
        'inline bool NpcRewardKnown(std::uint32_t entity) {',
        '    auto state = std::lower_bound(NpcRewardStates.begin(), NpcRewardStates.end(), entity,',
        '        [](const NpcRewardState& row, std::uint32_t value) { return row.entity < value; });',
        '    return state != NpcRewardStates.end() && state->entity == entity;',
        '}',
        'template<class Flag> bool NpcRewardAllowed(std::uint32_t entity, Flag flag) {',
        '    auto state = std::lower_bound(NpcRewardStates.begin(), NpcRewardStates.end(), entity,',
        '        [](const NpcRewardState& row, std::uint32_t value) { return row.entity < value; });',
        '    if (state == NpcRewardStates.end() || state->entity != entity) return true;',
        '    for (; state != NpcRewardStates.end() && state->entity == entity; ++state)',
        '        if (flag(state->flag)) return state->allowed;',
        '    return false; // native inactive/default branch',
        '}'])
    lines.extend(['struct NpcRewardReceipt { std::uint32_t flag, entity; };',
                  f'inline constexpr std::array<NpcRewardReceipt, {len(receipts)}> NpcRewardReceipts{{{{'])
    lines.extend(f'    {{{flag}, {entity}}},' for flag, entity in sorted(receipts))
    lines.extend(['}};',
        'inline bool NpcRewardReceiptKnown(std::uint32_t receipt) {',
        '    return std::any_of(NpcRewardReceipts.begin(), NpcRewardReceipts.end(),',
        '        [receipt](const NpcRewardReceipt& row) { return row.flag == receipt; });',
        '}',
        'template<class Flag> bool NpcRewardReceiptAllowed(std::uint32_t receipt, Flag flag) {',
        '    bool known = false;',
        '    for (const auto& source : NpcRewardReceipts) {',
        '        if (source.flag != receipt) continue;',
        '        known = true;',
        '        if (NpcRewardAllowed(source.entity, flag)) return true;',
        '    }',
        '    return !known;',
        '}', '} // namespace Core::Bloodborne::QuestRules', ''])
    return '\n'.join(lines), rules, sorted(set(skipped))


if __name__ == '__main__':
    text, rules, skipped = generate(os.environ['BB_GAME'])
    if '--check' in sys.argv:
        assert HEADER.read_text(encoding='utf-8') == text, 'regenerate NPC reward rules'
    else:
        HEADER.write_text(text, encoding='utf-8', newline='\n')
    print(f'{len(rules)} NPCs protected; {len(skipped)} complex/parameterized events left native')
    if '--audit' in sys.argv:
        for name, event in skipped:
            print(f'  review: {name} / {event}')
