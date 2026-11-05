"""Remove obsolete bell tutorial messengers from the co-op Dream layout.

Generated overlay only; the player's original MSB is never written.
MSBB layout: SoulsFormats/Formats/MSB/MSBB/{MSBB,EventParam}.cs.
"""
from pathlib import Path
import struct

LAYOUT = 'dvdroot_ps4/map/MapStudio/m21_00_00_00.msb.dcx'
BELL_MESSAGES = {1121, 1122}


def remove_bell_hints(data):
    if data[:4] != b'MSB ':
        raise ValueError('BBSC: unsupported Dream layout')

    def read(fmt, offset):
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(data):
            raise ValueError('BBSC: truncated Dream layout')
        return struct.unpack_from(fmt, data, offset)

    def text(offset):
        end = offset
        while read('<H', end)[0]:
            end += 2
        return data[offset:end].decode('utf-16-le')

    at, seen = 0x10, set()
    while at:
        if at in seen:
            raise ValueError('BBSC: cyclic Dream layout lists')
        seen.add(at)
        _, count, name = read('<iiq', at)
        if not 1 <= count <= len(data) // 8:
            raise ValueError('BBSC: invalid Dream layout list')
        offsets = read(f'<{count}q', at + 16)
        if text(name) == 'EVENT_PARAM_ST':
            break
        at = offsets[-1]
    else:
        raise ValueError('BBSC: Dream event list missing')

    kept, messages, removed = [], [], set()
    for entry in offsets[:-1]:
        kind, = read('<i', entry + 0x0C)
        if kind == 6:  # MSBB Event.Message; signed short FMG ID
            base, typed = read('<qq', entry + 0x18)
            message, = read('<h', entry + typed)
            if message in BELL_MESSAGES:
                # These tutorials have no script-facing entity ID. Refuse to
                # remove a modified entry which other game scripts may address.
                if read('<i', entry + base + 8)[0] != -1:
                    raise ValueError('BBSC: bell hint has a script entity ID')
                removed.add(message)
                continue
            messages.append(entry)
        kept.append(entry)
    if not removed:
        return data
    result = bytearray(data)
    # Offset-based lists permit unused bytes; retain every region/part offset
    # and all remaining event data. Only Message's per-type IDs are renumbered.
    struct.pack_into('<i', result, at + 4, len(kept) + 1)
    struct.pack_into(f'<{len(kept) + 1}q', result, at + 16, *kept, offsets[-1])
    for index, entry in enumerate(messages):
        struct.pack_into('<i', result, entry + 0x10, index)
    return bytes(result)


def apply(layers, game, out):
    """Transform the winning layout, including the PC mirror or user map mod."""
    from fromsoft import dcx_decompress, dcx_compress
    source = Path(game) / LAYOUT
    for _, folder in layers:
        candidate = Path(folder) / LAYOUT
        if candidate.is_file():
            source = candidate
    packed = source.read_bytes()
    original = dcx_decompress(packed)
    result = remove_bell_hints(original)
    if result == original:
        return layers
    folder = Path(out) / 'bbsc-dream-hints'
    target = folder / LAYOUT
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(dcx_compress(result, packed))
    temporary.replace(target)
    return [*layers, ('BBSC Dream bell hints', folder)]
