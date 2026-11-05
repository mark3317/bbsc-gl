"""Read-only original-data and real overlay-path checks for Dream bell hints."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PORT = ROOT.parents[1]
sys.path[:0] = [str(ROOT / 'party'), str(ROOT / 'tools/gamedata'), str(PORT / 'scripts')]
from dream_hints import LAYOUT, apply, remove_bell_hints
from fromsoft import dcx_decompress, dcx_compress
from msb import Msb
from enhancements import mirror_layout

game = Path(os.environ['BB_GAME']).resolve()
source = game / LAYOUT
packed = source.read_bytes()
original = dcx_decompress(packed)


def verify(data, output):
    result = remove_bell_hints(data)
    output.write_bytes(dcx_compress(result, packed))
    before_path = output.with_name('before.msb.dcx')
    before_path.write_bytes(dcx_compress(data, packed))
    before, after = Msb(before_path), Msb(output)
    wanted = [e for e in before.events if not (
        e['type'] == 'Message' and struct.unpack_from('<h', e['type_data'])[0] in (1121, 1122))]
    assert len(before.events) - len(wanted) == 2
    assert after.events == wanted  # every other event payload and reference retained
    assert before.parts == after.parts and before.points == after.points
    assert remove_bell_hints(result) == result
    # Original reader follows the new next-list pointer through all later lists.
    assert before.models == after.models and before.lists.keys() == after.lists.keys()
    return result


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)
    verify(original, out / 'plain.msb.dcx')
    mirrored = mirror_layout(original)
    expected = verify(mirrored, out / 'mirror.msb.dcx')
    layer = out / 'mirror'
    target = layer / LAYOUT
    target.parent.mkdir(parents=True)
    target.write_bytes(dcx_compress(mirrored, packed))
    layers = apply([('PC mirror', layer)], game, out / 'generated')
    assert dcx_decompress((layers[-1][1] / LAYOUT).read_bytes()) == expected
    assert apply(layers, game, out / 'generated') == layers
    # Real mods.py CLI used at launch, including mods master switch OFF.
    command = [sys.executable, str(PORT / 'scripts/mods.py'), str(game),
               '--out', str(out / 'launch'), '--mods-dir', str(out / 'mods'),
               '--enabled', '0', '--generated', str(layer)]
    subprocess.run([*command, '--bbsc-runtime', str(ROOT / 'party')], check=True,
                   stdout=subprocess.PIPE, text=True)
    assert dcx_decompress((out / 'launch/bbsc-dream-hints' / LAYOUT).read_bytes()) == expected
    subprocess.run([*command[:], '--out', str(out / 'offline')], check=True,
                   stdout=subprocess.PIPE, text=True)
    assert not (out / 'offline/bbsc-dream-hints').exists()
    for invalid in (b'', b'MSB ' + bytes(32)):
        try:
            remove_bell_hints(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid MSB accepted')
assert source.read_bytes() == packed
print('PASS: two bell hints removed; other events/parts/regions, mirror, idempotence, '
      'real co-op/offline overlay paths and original file preserved')
