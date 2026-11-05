"""Conservative authority rules for extracting personal NPC events."""
from pathlib import Path
import struct
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tools/gamedata'))
from quest_event_rules import personal_writes
# A native clear of a single known quest family includes unused stage bits.
clear = lambda lo, hi, value: (2003, 22, struct.pack('<III', lo, hi, value))
set_flag = lambda flag: (2003, 2, struct.pack('<II', flag, 1))
npc = {1240, 1245, 1246}
assert personal_writes([clear(1240, 1259, 0), set_flag(1245)], npc)
assert not personal_writes([clear(1240, 1259, 1)], npc)
assert not personal_writes([clear(1240, 1260, 0)], npc)
assert not personal_writes([set_flag(1245), set_flag(12411800)], npc)
assert not personal_writes([set_flag(1245), (2004, 37, struct.pack('<I', 2410781))], npc)

print('PASS: conservative personal NPC event authority rules')
