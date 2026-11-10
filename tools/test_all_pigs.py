"""Validate every original map through the replacement path, including new models."""
from pathlib import Path
import struct
import sys
import tempfile

from build_all_pigs import Msb, eligible, int32, int64, replace_map, pig_parameters, param, bbfiles


def check(game):
    maps = changed_maps = replacements = added_models = 0
    npc_ids = {}
    bbfiles.GAME = str(game / 'dvdroot_ps4')
    _, row_size, original, old_rows = param.load('NpcParam')
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'modified.msb'
        for path in sorted((game / 'dvdroot_ps4/map/mapstudio').rglob('*.msb.dcx')):
            before = Msb(path)
            result, changed = replace_map(before, npc_ids, old_rows)
            maps += 1
            if not changed:
                assert result == before.data
                continue
            target.write_bytes(result)
            after = Msb(target)
            added = 'c1270' not in before.models
            assert after.models == before.models + (['c1270'] if added else [])
            assert before.points == after.points
            assert before.events == after.events
            assert before.lists.keys() == after.lists.keys()
            assert len(before.parts) == len(after.parts)
            expected = 0
            edits = {}
            for old, new, offset, new_offset in zip(
                    before.parts, after.parts, before.lists['PARTS_PARAM_ST'], after.lists['PARTS_PARAM_ST']):
                selected = eligible(old, before.data, offset) and old['model'] != 'c1270'
                source_enemy = offset + int64(before.data, offset + 0xB8)
                selected = selected and int32(before.data, source_enemy + 12) in old_rows
                if selected:
                    assert new == dict(old, model='c1270', model_index=after.models.index('c1270'))
                    enemy = new_offset + int64(result, new_offset + 0xB8)
                    source_enemy = offset + int64(before.data, offset + 0xB8)
                    source_npc = int32(before.data, source_enemy + 12)
                    assert struct.unpack_from('<ii', result, enemy + 8) == (127400, npc_ids[source_npc])
                    assert struct.unpack_from('<ii', result, enemy + 0x38) == (-1, -1)
                    local_enemy = enemy - new_offset
                    edits[offset] = [(0x1C, 4), (local_enemy + 8, 8), (local_enemy + 0x38, 8)]
                    expected += 1
                else:
                    assert new == old
            # All changes to existing records are restricted to the selected fields
            # and model instance counts/type-local IDs. Regions/events stay byte-identical.
            section = 0x10
            ends = {}
            for name in before.lists:
                count = int32(before.data, section + 4)
                section = int64(before.data, section + 16 + (count - 1) * 8)
                ends[name] = section or len(before.data)
            for name, offsets in before.lists.items():
                new_offsets = after.lists[name]
                for index, offset in enumerate(offsets):
                    end = offsets[index + 1] if index + 1 < len(offsets) else ends[name]
                    new_offset = new_offsets[index]
                    old_record = bytearray(before.data[offset:end])
                    new_record = bytearray(result[new_offset:new_offset + len(old_record)])
                    ranges = edits.get(offset, [])
                    if name == 'MODEL_PARAM_ST':
                        ranges = [(12, 4), (24, 4)]
                    for start, size in ranges:
                        old_record[start:start + size] = bytes(size)
                        new_record[start:start + size] = bytes(size)
                    assert old_record == new_record, (path, name, index)
            assert changed == expected
            # Reapplying the generator must produce exactly the same result.
            assert replace_map(after, npc_ids, old_rows) == (result, 0)
            changed_maps += 1
            replacements += changed
            added_models += added
            if maps % 500 == 0:
                print(f'Checked {maps} maps', flush=True)
    assert added_models > 0 and replacements > 0
    bbfiles.GAME = str(game / 'dvdroot_ps4')
    modified = pig_parameters(original, npc_ids, row_size)
    new_rows = param.read_param(modified)
    assert len(new_rows) == len(old_rows) + len(npc_ids)
    for npc_id, offset in old_rows.items():
        assert original[offset:offset + row_size] == modified[new_rows[npc_id]:new_rows[npc_id] + row_size]
    for source_id, new_id in npc_ids.items():
        offset = new_rows[new_id]
        pig = modified[offset:offset + row_size]
        assert pig[40:68] == original[old_rows[source_id] + 40:old_rows[source_id] + 68]
        assert pig[:40] == original[old_rows[127500]:old_rows[127500] + 40]
        assert pig[68:] == original[old_rows[127500] + 68:old_rows[127500] + row_size]
    # The relocated name pointers still address the exact original strings.
    for index in range(len(old_rows)):
        old_name = int64(original, 0x40 + index * 24 + 16)
        new_name = int64(modified, 0x40 + index * 24 + 16)
        if old_name:
            assert original[old_name:old_name + 16] == modified[new_name:new_name + 16]
    print(f'PASS {maps} maps, {changed_maps} modified, {replacements} replacements, {added_models} new model entries')


if __name__ == '__main__':
    check(Path(sys.argv[1]))
