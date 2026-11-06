# Old Yharnam distance: world event bootstrap wait — 06.11.2026

Status: investigation only; gameplay bug OPEN. No source/build/deploy changes.

User reports P1 near Church of the Good Chalice, P2 near Old Yharnam entrance:
P2's door remains closed and lamp unavailable until P1 approaches. User suggests
the distant owner's reduced streaming footprint as the underlying cause.

Both profiles' latest run_20261106_010053.log and two earlier rotations collected
in parent out/coop-dev/runs/old-yharnam-distance-20261106/pc (6 files, warnings0;
latest two ChangedDuringCopy=true). Actual session roles: P2 HOST / P1 GUEST.
Map owner is P1 (6830fdc5), distinct from session host P2 (ac3011d3).

P2 timeline (MSK):
- 01:10:07.045: arrives m23_00, visit8/native load8; receives map flag updates.
- 01:10:52.911: local return72300100 released, but native warp does not run yet.
- 01:12:54.647: native CHR initial state from P1 finally applied, request4;
  immediately logs native world ready before events for load8.
- 01:12:54.676: event12300100 executes door2301000 command.
- 01:12:54.677: event7000 executes lamp2301950 disable/enable commands.
- 01:12:58.798: native Dream departure finally executes.

Confirmed mechanism: pre-event GuardBbscWorldBootstrap waits on native CHR
historical-death admission; BbscNpcPassHook returns before native event execution
while this guard holds. Thus NPC initialization readiness blocks door/lamp/travel
events together. P2 remained without completed admission for167.602 seconds.

Likely distance-sensitive trigger: BbscWorldApplyNativeInitial requires the
owner packet to contain every LOCAL nonempty CHR block with the matching actor
count. Owner serializes its own streamed blocks. If distant P1 lacks a block
loaded by P2, P2 rejects admission until P1 streams that block. Earlier fix
2026-11-05-enemy-arrival-streaming permits EXTRA provider blocks only; missing
provider coverage remains a rejection. This is not evidence that a simplified
door/lamp state itself is copied; an incomplete NPC snapshot can hold all events.

Evidence limit: rejected packet block IDs, actor counts and exact rejection
reasons are not logged. The successful CHR apply and immediate event release
are proven; exact prior rejection branch/streaming mismatch remains a strong
source-supported hypothesis, not measured per-block proof. Do not bypass native
historical death or substitute P2's personal world state to clear this wait.
