# Repeated native global loot receipts — 05.11.2026

Актуальный общий контекст: [предметы и награды](../REWARDS.md).

P2 run_20261105_054236.log confirms Clawmark / lot29010 / code0x80018896 pickups
at05:53:26.006 and05:56:35.549, with own-world restore at05:53:46.538 between
them. Read-only P2 item-ledger v1 inspection confirms lot29010/code0x80018896
is already persisted: delivery was known, but native receipt50001300 was not
reapplied after the guest load.

Root gap: map snapshots/views deliberately cover area21..99. Global enemy/NPC
receipt groups50000..50099 have area0. RecordBbscNativeItemFlag previously
required an existing map baseline, so it ignored these bits. Map-scoped pickup
fixes alone could not retain Gilbert's global native get flag.

General audit of original CUSA03173 1.09/base+DLC ItemLotParam:107 lots,86 distinct
global get flags. Categories:67 goods,19 gem/rune,13 attire,8 weapon lots.47 lots
are referenced by original NpcParam.63 other NPC-linked receipt lots use existing
map-scoped groups. All107 global flags are main lot receipts: no per-entry global
flags; replay cannot claim unselected alternate entries. Aliases34020/34040
share50001820;29010 uses50001300;51000 uses50003100.

Fix: confirmed global pickup commits only its own bit to a zero-initialized kind5
snapshot group (restored by OR), without copying surrounding host bits. The actual
lot journal is flushed immediately for global rune receipts too. At the native
load view, restore individual global receipt bits from this character's confirmed
lot journal, including earlier versions. The native enemy death-worker and the
shared treasure producer also ensure restoration before their native lot roll;
ForceCharacterTreasure can bypass the death worker. A generation/data/slot cache
keeps later enemy deaths in memory, without a save-directory scan per death.
Missing table/storage does not mark restoration complete; next load/producer can
finish it. Unknown/unreceived lots are not marked. Foreign dungeon and character
contexts are excluded. No timed scan, inventory add, reroll or inventory-based
award suppression is added. The original engine enforces its native get flag.

PASS: all107 original rows through production receipt replay in fake memory;
repeat joins, unreceived items, unrelated bits, character/dungeon/feature guards,
late param/write readiness, forced same-generation load. PASS: production pickup
snapshot state including a global group without map baseline; native death worker
and producer with actual bytes/trampolines; personal scripted pickups.
Real save/settings/game files were not changed. Gameplay validation remains OPEN.

NG+ guard: the ledger's optional backward-readable v1 tail records the native
[GameData+0x68] clear cycle. A confirmed later cycle retires only old global-loot
lot receipts before native replay; ordinary rejoin preserves them. Legacy journals
without that field adopt the current cycle once (their historical cycle cannot be
reconstructed). Original native NG+ loot can therefore become available again.
Production synthetic replay/NG+ and existing actual ledger persistence fixtures PASS.

The producer also reasserts cached own receipt masks when native construction
clears a bit within the SAME generation. This path reads/writes only the few
in-memory global flag groups, without scanning save directories or PARAM per
kill. A newly confirmed lot invalidates the masks. Both the death worker and
the direct ForceCharacterTreasure producer are covered. Same-generation reset
and new-receipt revision fixtures PASS.

05.11 deployment: DLL build/deploy exit0, delta5, backup global-loot-receipts-20261105-20261105-062348. P1/P2 start requested06:23 MSK. Gameplay remains OPEN.

Startup confirmed05.11 at06:24:17 MSK: P1 native PID12408, P2 PID21532; both fresh user/run_20261105_062417.log report34/34 hooks and native enemy loot ready. This confirms startup, not gameplay duplicate suppression.
