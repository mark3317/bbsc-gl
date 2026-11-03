# Kept-wipe local member rebind — 02.11.2026

Scope: client DLL only. Latest observed symptom is session loss after a completed
three-player boss wipe, not a demonstrated process crash. Evidence and original
limits: [run review](2026-11-02-run-review-2215.md).

## Correction

`TickBbscReinsertV8` formerly finished pending recovery and restarted remote
FirstSyncWait tasks before the periodic local member check. That check compared
only PlayerIns+0x3D8. Equal parent ids skipped PlayerIns::SetMemberId even though
the rebuilt +0x60 network child could still need its binding forwarded.

Recovery now restores the phantom type, obtains the existing member tasks, and
calls the native setter using the stable self task (mode 3 host / 0 guest) before
remote task restarts. This one recovery call forces the setter even with an equal
parent id. It also works if the allocator reuses the same player address on the
next load. Once recovery completes, periodic checks remain equality based.
If the local player/child/self task is not ready, recovery stays pending without
restarting remote tasks; session change or the existing 120-second timeout cancels
it. No fabricated acknowledgement, raw member-id copy or queue deletion.
The native reliable limit remains 1001 and genuine stop paths remain enabled.

Native read-only inspection of the local CUSA03173 runtime-mode-eboot confirms
0x018F27C0 calls ref-counted assignment 0x00CA1BA0 for PlayerIns+0x3D8, then
unconditionally forwards the member through child+0x60's vtable+D0.
Thus parent equality alone cannot establish completion of both setter operations.
Whether the child was actually unbound in the recorded run is still unobserved;
this fixes a recovery ordering/completeness gap, not a proven unique crash cause.

Added an observational hook at native Stop 0x01ED07A0. It logs the original return
address, active role/state, summon reload phase and pending-reinsert flag before
cleanup hides the initiating caller. It does not suppress Stop or change packets.
This distinguishes reliable overflow 0x01789812 from other native stop callers if
the next run still disconnects.

## Checks and delivery

- `tools/test_member_binding.py`: PASS. Runs the extracted production recovery,
  binding, self-heal and backlog functions. Equal parent / unbound child,
  host/guest self identity, setter-before-remote ordering, one-shot completion,
  reused address on a second load, pending self-task and session-loss cancellation;
  prior idle/load/death/leave/queue checks retained.
- `tools/test_hook_resume.py`: PASS. Actual production trampoline executes the
  exact six-byte Stop entry prologue on synthetic code; observer reads the caller,
  preserves the argument and returns to the original native body/epilogue.
- Bundled `build-mod-bbport.cmd`: exit=0, four compiler warnings. Mod delta prepared.
- Changed functions and fixtures synchronized to standalone and bundled trees.
  Unrelated existing working-tree changes preserved; no broad commit made.
- Installation initially pending: Bloodborne.exe PID 35624 remained open.
  No process terminated, no server changes, no saves/settings changed.

## Gameplay confirmation pending

Use Player 1/2/3, with one host and two guests; start from the installed update
after all launchers close. Both guests die on a boss, then the host dies. All
three should load back together and remain in co-op for at least 60 seconds;
repeat once to exercise a second recovery generation. New logs must show local
member binding restored with rebuilt=true before each remote insert restart.
If the session ends, collect the first native stop request with the same run's
three mod/game logs. No bug closure based on fixtures/build alone.
