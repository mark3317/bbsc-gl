# 03.11.2026 — host exit arms a competing world reload

Status: source corrected, targeted regressions PASS. No DLL/package build,
installation or game launch for this fix (user explicitly deferred builds).
Actual title arrival with the corrected DLL remains pending gameplay.

## Evidence

P2 PID21572, DLL15:52:57; parent snapshot
`out/coop-dev/runs/review-20261103-1603/pc/profile-2/mod-logs/`:
confirm16:02:36.966, Stop16:02:37.026, state0 16:02:38.710,
final leave/title command16:02:40.011, character creation16:02:49.548.
User confirms the character appeared automatically, without Continue.
The earlier diagnostic inferred Continue from construction; it did not observe input.

The confirmed exit in `TickBbscPendingQuit` called OnReturnTitle, then
StageTransition, then CloseMenus. The second call was added when modeling exit
on SendPhantomHome. It is a separate world-reload command, not the executor of
the title request. For an own-world host it reloads the retained map context.

Read-only CUSA03173 1.09 native instructions:

- OnReturnTitle0138BAF0:0138BB29 loads the request object from EventMan+10;
  0138BB2D writes request+08=2. It never writes global+08.
- StageTransition013CDE30:013CDE3E loads global,013CDE45 unconditionally
  writes global+08=1, without checking the pending title request. It snapshots
  the character and returns1 in the own-world path (global+1592 nonzero).
- StageFlow separately samples request at0194057F..01940586 and global+08
  at0194059F..019405A9; the two inputs have separate acknowledgement paths
  at0194100A..01941050. Setting both is not an atomic title transition.

`tools/test_title_request_native.py` executes both complete native command
bodies from the local analysis ELF on fake memory. Only the character snapshot
callee is stubbed; no actual game, user profile or save is opened. Native
OnReturnTitle leaves loading0/request2. Adding native StageTransition returns1
and changes loading to1 while request remains2. This reproduces the erroneous
extra world-reload request independently of the old C++ test stubs.
It does not emulate the entire native StageFlow or claim live title success.

## Correction

After successful native save, Stop and durable final group leave, submit only
OnReturnTitle and close the old System menu on the deferred game-thread stack.
Keep the native title lifecycle responsible for processing its request. No
StageTransition, synthetic loading flag, forced map selection or respawn here.
The existing host input-wait work is retained, including cancellation handling.
Rename the load diagnostic to own-world character creation after a title request:
it must not claim a Continue button press or actual arrival at the title screen.

## Validation

- Updated production-function `tools/test_menu_quit.py` failed on the old call
  sequence (loading unexpectedly1 at handoff), then PASS with the fix.
  Host/joining/guest/idle, fresh final gate, duplicate requests, unrelated load,
  save result/error/timeout, cancellation and existing input-wait checks retained.
- Native command regression above PASS against `../../out/exit-study.elf`.
- No hook/trampoline change, protocol change, production build or deploy.
