# Native personal receipts and missing unique boss rewards — 05.11.2026

> Актуализация05.11 — [итоговая сводка](../REWARDS.md). Home-only этап заменён проверкой после готовности гостевой сумки при загрузке к хосту. Добавлены17 лотов чаш и событийный work bit без секундного опроса наград. Исторические результаты проверок/установок ниже сохранены.

## Scope and corrected diagnosis

The earlier claim that 2003[4] passes permission 0 was incorrect. The original
CUSA03173 dispatcher at 017C063A passes EDX=1, then jumps to the shared call at
017C1806. Command 2003[36] enters at 017C17A6 and passes EDX=0. The previous
study of the permission function was correct, but its caller attribution was not.
Both dispatch paths are now byte-checked against out/exit-study.elf. Reviewed
personal native rewards substitute permission 0 for a guest; the player role is
unchanged. This is an actual additional cause of the empty Inspect interaction.

Native scripted completion was also being undone by the NPC-state rollback.
Native item completion/receipts now preserve the current local bit at incoming
host-group boundaries, and local native changes are observed instead of reverted.
Other personal NPC stages remain isolated. Confirmed map pickups immediately
commit their exact native receipt into the own-world snapshot and taken journal,
without depending on a one-second scan of the last applied area. Real TakeItem
calls begin a fresh receipt context even after a boss award in the same tick.
Foreign generated-dungeon pickups never mark another own dungeon.

## Ordinary world and The Old Hunters

Shared progress is retained. The 19 original boss award events and their defeat
indicators were audited against original EMEVD/PARAM. Catch-up runs through the
original AwardItemLot entry once the own bag is ready. Pending progress is not
retired until delivery and receipt persistence complete. The game chooses and adds
the original lot; no AddItem/manual substitute or fallback random roll is added.

By the user's latest scope, catch-up targets 15 unique-reward events. The four
flagless ordinary/consumable first lots (Hemwick, Amelia's consumable pendant,
One Reborn, Rom) are not inferred from inventory absence. Native fight rewards
still run normally. Unique runes with personal receipt flags remain included.
Actual first/repeat native awards, including flagless badges/clothing, are kept
in the existing per-character lot journal; its format stays version 1. Inventory
checks include carried and stored items. Catch-up never selects repeat NG+ lots.

Old already-merged victories are checked at home too, so Pthumeru Chalice/other
missing unique rewards do not require another boss kill or another host trip.
A stale receipt on a missing persistent key/chalice can be cleared for its native
award; on a failed grant the old receipt is restored and work remains pending.
Confirmed actual-give history is not discarded. Ludwig and Laurence are identified
individually; their shared map stage flags 3400..3403 are not defeat evidence.
All DLC event files are included; native enemy loot remains a separate path.

## Chalice Dungeons

Seven pure m29 common reward events (12901594..12901598,12901693,12901730) retain
native waits, parameter substitution, original lot selection and gem generation.
A byte-verified hook at bank 1003 / 017BEDD0 removes only the guest multiplayer
route and, with shared progress enabled, the initial already-dead early exit.
Later flag conditions and unrelated events are preserved. The initial guest gate
waits for a valid ritual/character identity instead of guessing a namespace.
Offline/unpublished own rituals keep their original native award path.

The same native reward event can thus provide a missing unique chalice for an
old cleared layer without importing the host's doors/bosses into a different
personal dungeon. Native permission 0 is applied only to this reward call.
Receipts use user/slot, ritual channel/form hash/version/size, resident map, event,
native flag offset, native event slot and lot. A different dungeon/layer remains
independent even when it reuses a lot. Original successful native give windows
write the receipt, not visibility/host inventory. An observed-old event has a
separate origin marker: its untracked old consumables/random gems are not issued
again. An observed-new fight retains normal native rewards. Damaged receipt files
fail closed for every subsequent lookup. No reward packets were introduced.

## Validation and status

PASS: production shared reconciliation + actual merge, 19 original lot/defeat
mappings, native failure/pending paths, stale Pthumeru receipt, old missing unique
reward recovery, carried/storage and consumed-history checks, production ledger
write/read, identity/load gating, Ludwig/Laurence isolation. PASS: 38 native lots
with actual award trampoline, original permission-1 call, m29 permission-0/1 call
provenance and unrelated legacy gifts. PASS: seven original m29 reward events,
actual bank-gate trampoline, production scoped receipt persistence and negative
paths. PASS: native pickup completion/receipt state, same-tick award/take,
personal scripted localization, personal progress save-ack fixture.

Only artificial memory/files are used by fixtures. Native downstream inventory,
lot choice and actual m29 item/gem generation are not executed by these fixtures.
Real saves/settings/game files were not edited by tools. Build/deploy/gameplay
are separate statuses; gameplay confirmation remains OPEN.

Final DLL build and fast delta deployment both exit0; copied5, backup
D:/Games/Bloodborne/coop-dev/backups/native-reward-receipts-20261105-20261105-050421.
Build input metadata unchanged. Related chats completed. Existing P1/P2 launchers
started05:04 MSK, with profiles and immortality setting retained. Native startup
confirmation is recorded in out/coop-dev/runs/native-reward-receipts-20261105/run.md
of the parent repository. Actual gameplay/item delivery remains OPEN.
