## 2026-11-02 — initial join cannot teleport between worlds

Evidence: keys-20261102-0231 laptop log, 02:35:38–42. Native summon
created the character in Dream (0x15000000), then join teleport moved it
from (-15.11,-5.11,-11.24) to dungeon host (39.86,31.50,-52.97).
At 02:36:16 guest died; recovery correctly refused in-place revive in the
wrong world. First follow at 02:34:36 had injected the loader and arrived
in m29; generic m29 missing optional resources also occur on host and do
not establish a loader failure.

Fix: require a fresh host follow map before using any remote transform.
World mismatch hands initial join to scoped follow without teleport.
Dungeon placement requires same map and mounted current revision/key.
Non-chalice adjacent resident blocks remain allowed within one area.
No changes to death policy, altars, saves or network protocol.
Production test_join_destination and test_chalice_scope PASS. Game validation pending.
Includes preceding shared-key receipt fix in the same pending DLL.
