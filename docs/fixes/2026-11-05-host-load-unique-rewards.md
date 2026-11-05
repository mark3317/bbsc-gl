# Unique reward check on host load — 05.11.2026

> Актуализация05.11 — [итоговая сводка](../REWARDS.md). Эта логика сохранена в последней установленной DLL; затем исправлены глобальные get flags добычи. Последний подтверждённый старт P1/P2 —06:24:17 МСК, не05:42. Исторические результаты проверок/установок ниже сохранены.

User requests: preserve shared progress and duplicate protection, check missing
unique rewards on loading into the host world, remove the one-second reward poll,
then build/install/start two existing profiles. Consumables and random gems stay
outside retrospective recovery. Earlier home-only/specific-layer behavior is
superseded by this change.

The existing progress packet additionally carries17 reviewed original chalice
receipt flags as earned-reward eligibility. Native ItemLotParam is still the
source of category/item/count and new receipt. No inventory is read from the host,
no item code/count packet is introduced, no host receipt is merged into the client
flag table, and no personal dungeon's doors/layers are overwritten. Old receivers
ignore the extra known flags; old hosts cannot advertise these new eligibility
facts. The shared installation updates both profiles together.

After guest inventory readiness, collected original boss victories/base+DLC and
chalice eligibility pass through the native award. Existing first/repeat lot
history, own receipts, carried AND stored inventory provide duplicate checks.
Unique cups use their global per-character receipt: different dungeons cannot
give a second copy of the same unique cup. Original scoped m29 source receipts
remain for event-local awards. A stale local receipt with missing persistent cup
can be repaired; a failed native give restores it and records no actual receipt.

Reward delivery uses a new work bit, not periodic scans. Inventory-ready generation
changes, new host progress facts, new boss event completion bits and pending-file
recovery request work. Repeated identical progress heartbeats and unrelated map
bits do not request work. A signal arriving before load readiness is retained;
readiness transition wakes it. Native calls run on the game thread outside the
progress collection mutex. Old-character pending facts cannot award a new slot.
Shared-world progress retirement waits for successful reward completion, without
retrying the native award every second. Failed delivery waits for another load/
new progress event. The existing unrelated world/progress persistence timer stays.

Catch-up success/accounted own award cancels a pending live boss reward ticket,
so arrival overlapping the native type-wait cannot duplicate flagless clothing/
badges. Normal boss rewards keep their native first/repeat selection; enemy/hunter
loot is unchanged by this task. No new death protection is added.

PASS: production reconciliation and work processor with original19 boss lots /
17 additional cup lots; actual native award trampoline55; PARAM receipt/category
validation; guest readiness, home readiness, character isolation, repeated join,
repeated packets, stored inventory, failed native give/file write, unchanged own
receipt on entitlement-only merge, no timed retry, actual ledger write/read, and
catch-up versus live event ticket cancellation. Shared-progress policy and personal
progress save-ack fixture PASS. These use artificial memory/files; actual gameplay
and native downstream inventory behavior remain OPEN. Real saves/settings/game
files are not changed by development tools.

Final DLL build/deploy exit0, delta5, input metadata unchanged. Backup:
D:/Games/Bloodborne/coop-dev/backups/host-load-rewards-20261105-20261105-054206.
Two existing profile CMDs started05:42 MSK; no profile/settings/save changes.
Native startup confirmation belongs to parent out/coop-dev/runs/host-load-rewards-20261105/run.md.
Gameplay confirmation remains OPEN.
