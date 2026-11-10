"""Build a BBGL delta mod from the player's read-only Bloodborne 1.09 maps.

Run with a Python containing bsdiff4. No game files are copied into the package.
MSBB layouts follow SoulsFormats/Formats/MSB/MSBB/{Model,Parts}Param.cs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'gamedata'))
from msb import Msb
import param
import bbfiles

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from fromsoft import Bnd4, dcx_decompress


# Boss-only models and Patches' face. Ordinary versions of shared models
# (Watchers, Shadows, Blood-starved Beast) are selected by their entity slot.
PROTECTED = {
    1110, 2100, 2180, 2300, 2310, 2320, 2321, 2510,
    2570, 2571, 2710, 2711, 2712, 2720, 3050, 3060, 3130, 4030,
    4070, 4071,
}


def int32(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


def int64(data, offset):
    return struct.unpack_from('<q', data, offset)[0]


def eligible(part, data, offset):
    model = part['model'] or ''
    if part['type'] not in ('Enemy', 'DummyEnemy') or len(model) != 5 or not model[1:].isdigit():
        return False
    number = int(model[1:])
    if model[0] != 'c' or not (1000 <= number <= 4160 or number == 7500):
        return False
    if number in PROTECTED or 800 <= part['entity_id'] % 1000 < 900:
        return False
    enemy = offset + int64(data, offset + 0xB8)
    # Talk scripts identify quest characters even when they share an enemy model.
    return int32(data, enemy + 0x10) <= 0


def add_pig_model(data):
    """Insert a model table pointer, relocating only absolute list pointers.

    All record-internal pointers are relative and their records move intact.
    The appended model has an empty editor-only SibPath.
    """
    count = int32(data, 0x14)
    insertion = 0x20 + (count - 1) * 8
    result = bytearray(data[:insertion] + bytes(8) + data[insertion:])
    offset = 0x10
    while offset:
        new_offset = offset + (8 if offset >= insertion else 0)
        old_count = int32(data, offset + 4)
        name = int64(data, offset + 8)
        struct.pack_into('<q', result, new_offset + 8, name + 8)
        for index in range(old_count):
            value = int64(data, offset + 16 + index * 8)
            target = new_offset + 16 + index * 8
            if offset == 0x10 and index == old_count - 1:
                target += 8
            struct.pack_into('<q', result, target, value + 8 if value else 0)
        offset = int64(data, offset + 16 + (old_count - 1) * 8)
    result.extend(bytes((-len(result)) % 8))
    record = len(result)
    # Enemy model, type-local index, SibPath, instance count, reserved words.
    result.extend(struct.pack('<qiiqiiii', 40, 2, 0, 52, 0, 0, 0, 0))
    result.extend('c1270\0\0'.encode('utf-16-le'))
    result.extend(bytes((-len(result)) % 8))
    struct.pack_into('<q', result, insertion, record)
    struct.pack_into('<i', result, 0x14, count + 1)
    return result


def replace_map(mapdata, npc_ids=None, available_npcs=None):
    original = mapdata.data
    selected = [offset for part, offset in zip(mapdata.parts, mapdata.lists['PARTS_PARAM_ST'])
                if eligible(part, original, offset) and part['model'] != 'c1270'
                and (available_npcs is None or int32(original, offset + int64(original, offset + 0xB8) + 12)
                     in available_npcs)]
    if not selected:
        return original, 0
    added = 'c1270' not in mapdata.models
    data = add_pig_model(original) if added else bytearray(original)
    shift = 8 if added else 0
    pig_index = len(mapdata.models) if added else mapdata.models.index('c1270')
    for offset in selected:
        offset += shift
        struct.pack_into('<i', data, offset + 0x1C, pig_index)
        enemy = offset + int64(data, offset + 0xB8)
        source_npc = int32(data, enemy + 12)
        npc = 127500
        if npc_ids is not None:
            npc = npc_ids.setdefault(source_npc, 1_000_000_000 + len(npc_ids))
        struct.pack_into('<ii', data, enemy + 8, 127400, npc)
        # An original seated/sleeping animation may not exist on the pig skeleton.
        struct.pack_into('<ii', data, enemy + 0x38, -1, -1)
    counts = Counter(int32(data, offset + shift + 0x1C)
                     for offset in mapdata.lists['PARTS_PARAM_ST'])
    model_offsets = [offset + shift for offset in mapdata.lists['MODEL_PARAM_ST']]
    if added:
        model_offsets.append(int64(data, 0x20 + len(mapdata.models) * 8))
    enemy_index = 0
    for index, offset in enumerate(model_offsets):
        struct.pack_into('<i', data, offset + 0x18, counts[index])
        if int32(data, offset + 8) == 2:
            struct.pack_into('<i', data, offset + 12, enemy_index)
            enemy_index += 1
    return bytes(data), len(selected)


def pig_parameters(data, npc_ids, row_size):
    """Add independent pig rows, keeping each replaced enemy's loot and echoes."""
    rows = param.read_param(data)
    if set(npc_ids.values()) & rows.keys():
        raise ValueError('Generated NPC IDs collide with original rows')
    count = len(rows)
    if count + len(npc_ids) > 65535:
        raise ValueError('Too many NPC parameter rows')
    table_end = 0x40 + count * 24
    strings = struct.unpack_from('<I', data)[0]
    table_shift = len(npc_ids) * 24
    extra_data = bytearray()
    for source_id in npc_ids:
        source = rows[source_id]
        pig = bytearray(data[rows[127500]:rows[127500] + row_size])
        # getSoul and itemLotId_1..6 are a contiguous group in the original PARAMDEF.
        pig[40:68] = data[source + 40:source + 68]
        extra_data.extend(pig)
    result = bytearray(data[:table_end] + bytes(table_shift) + data[table_end:strings]
                       + extra_data + data[strings:])
    struct.pack_into('<I', result, 0, strings + table_shift + len(extra_data))
    struct.pack_into('<H', result, 10, count + len(npc_ids))
    struct.pack_into('<Q', result, 0x30, int64(data, 0x30) + table_shift)
    for index in range(count):
        at = 0x40 + index * 24
        doff, name = struct.unpack_from('<QQ', data, at + 8)
        struct.pack_into('<QQ', result, at + 8, doff + table_shift,
                         name + table_shift + len(extra_data) if name else 0)
    for index, new_id in enumerate(npc_ids.values()):
        struct.pack_into('<IIQQ', result, table_end + index * 24, new_id, 0,
                         strings + table_shift + index * row_size, 0)
    return bytes(result)


def build(game, destination):
    import bsdiff4

    maps = game / 'dvdroot_ps4/map/mapstudio'
    if not maps.is_dir():
        raise ValueError('Expected the game folder containing dvdroot_ps4/map/mapstudio')
    if destination.exists():
        raise ValueError('Choose a new output folder to avoid mixing builds')
    destination.mkdir(parents=True)
    entries, total, npc_ids = [], 0, {}
    bbfiles.GAME = str(game / 'dvdroot_ps4')
    layout, row_size, npc_data, available_npcs = param.load('NpcParam')
    fields = {name: offset for name, offset, *_ in layout}
    if fields['getSoul'] != 40 or fields['itemLotId_6'] != 64:
        raise ValueError('Unexpected NpcParam layout')

    def add_delta(relative, original, result):
        delta = bsdiff4.diff(original, result)
        if bsdiff4.patch(original, delta) != result:
            raise ValueError(f'Delta roundtrip failed for {relative}')
        patch = f'{len(entries):04d}.bsdiff'
        (destination / patch).write_bytes(delta)
        entries.append(dict(target=relative, base=relative, patch=patch,
                            base_sha256=hashlib.sha256(original).hexdigest(),
                            sha256=hashlib.sha256(result).hexdigest()))

    for path in sorted(maps.rglob('*.msb.dcx')):
        mapdata = Msb(path)
        result, changed = replace_map(mapdata, npc_ids, available_npcs)
        if not changed:
            continue
        relative = path.relative_to(game).as_posix()
        add_delta(relative, mapdata.data, result)
        total += changed
        if len(entries) % 100 == 0:
            print(f'{len(entries)} maps, {total} replacements', flush=True)
    relative = 'dvdroot_ps4/param/gameparam/gameparam.parambnd.dcx'
    original = dcx_decompress((game / relative).read_bytes())
    archive = Bnd4(original)
    archive.files[archive.index('NpcParam.param')] = pig_parameters(npc_data, npc_ids, row_size)
    add_delta(relative, original, archive.to_bytes())
    manifest = dict(format=1, files=entries)
    (destination / 'bbgl-delta.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Built {destination}: {len(entries)} maps, {total} replacements', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    build(arguments.game.resolve(), arguments.output.resolve())
