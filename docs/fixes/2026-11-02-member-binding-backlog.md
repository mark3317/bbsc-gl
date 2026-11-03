# Local member binding and reliable-send bound — 2026-11-02

Source changes only. No DLL/package build, deployment, game launch or save changes.

## Evidence and limits

User reports a living local guest becomes motionless to others and cannot deal damage,
while the session remains established; progressive boss FPS loss clears on Parting Blank.
Local log review-20261102-2013/pc/profile-1/mod-logs/bbsc-mod-20261102-185906-20112.log
shows 57 FPS at 20:11:03 falling to 28.5 at 20:12:43, leave at 20:12:50.
Main measured hook calls/frame stay roughly constant (NPC pass 201, Dream check ~84).
The aggregate mod cost grows ~2.5 to 4.1 ms/frame, insufficient by itself to account
for the entire frame-time increase. This does not establish a unique FPS cause.
Normal logs did not observe the native reliable-send queue or local member binding.
Neither a binding mismatch nor queue growth during this exact run is proven.

## Defects addressed

- Kept-load recovery restored phantom types and remote insert tasks, but its periodic
  health check never verified local PlayerIns+3D8 against the self member task.
  Once per second, on the game thread with an established session, a living character,
  no load/quit/kept-death recovery and a stable self task (mode 0 guest / 3 host,
  current=next=6, no exit bit), compare member IDs. Repair a mismatch with the native
  PlayerIns setter 018F27C0. Never copy the ref-counted member bytes directly.
- Native eboot disassembly confirms StageFlow 01939470 calls 0178DAA0 after player
  creation. That function assigns the member via CA1BA0 and forwards it through
  player+60's vtable+D0. Setter 018F27C0 performs the same two operations. This
  makes the repair consistent with native ownership and child binding semantics.
  The self task, rather than a remote host task, supplies the identity.
- V8 previously restarted any remote task below Delete, including one already
  creating or leaving. Now only stable current=next=6 tasks without exit bit are
  restarted. Self-heal resets its missing timer when native create/leave intervenes,
  requiring a continuous 4-second absence before another restart.
- Removed SendBacklog.Limit, which raised native reliable-send capacity from 1001
  to 30000. Native 01789784..017897AD sums the queued packet counts on each failed
  reliable send; a large undeliverable queue retains/retries work until teardown.
  Keeping the vanilla bound prevents this modification from prolonging broken
  sessions for hours. It is containment, not a transport or recipient repair.
  Material behavior: reaching 1001 can end the whole native session as vanilla does.
- Native queue warnings now run in normal builds: at most one bounded 64-node
  scan per 2 seconds in established sessions, growing-count warning at most every
  30 seconds. No packet deletion, fabricated acknowledgements or raw list edits.

## Validation

`tools/test_member_binding.py`: PASS. Executes extracted production binding,
self-heal and queue-observer functions with native-call substitutes in fake memory.
Covers guest/host identity, replaced actor, stale ID, healthy 10000-cycle idempotence,
load/death/recovery/leave guards, pending-create timer reset and observer throttling.
Includes the actual patch-table header (10 valid WideEdits, no default extra entry).
Native setter/reload-finish instruction flow inspected read-only in local eboot.
Both source trees receive the same scoped changes; unrelated concurrent edits preserved.

`test_pending_work.py` still fails to compile its existing finale/cutscene fixture:
missing BbscRemoPlaying and other finale stubs. Reproduced independently with both
HEAD source and HEAD test, so this is pre-existing. Only its outdated research-only
assertion for SendBacklog was adjusted; no unrelated finale code changed.

Gameplay remains unconfirmed. New binding repair / send backlog warnings should
separate the two hypotheses in a later user-authorized build and gameplay run.
