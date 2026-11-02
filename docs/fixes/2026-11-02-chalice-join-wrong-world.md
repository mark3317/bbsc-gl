## 2026-11-02 02:46 MSK — join world guard + shared key receipts installed

Standalone e368f45, bundled deae891, port pin 762c374. Bundled DLL build exit=0.
Production join destination/freshness/map/mount fixture and chalice scope PASS;
shared-key receipt and inventory barrier checks passed during preceding change.
Delta installed on stopped PC and laptop: 5 files each, copy exit=0,
file verification disabled per preference. Backups join-world-keys-20261102-024630
(PC D:/Games/Bloodborne/coop-dev/backups) and -024639
(laptop C:/Games/Bloodborne/coop-dev/backups).
Includes previous key fix; earlier unbuilt/uninstalled statements are historical.
No game launch, save/settings changes. Runtime validation pending:
join host already in chalice, exit/rejoin, host Dream-to-chalice follow,
then reload and check shared keys show only on first receipt.
Details: fixes/2026-11-02-chalice-join-wrong-world.md.

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
