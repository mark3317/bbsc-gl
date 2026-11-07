# 06.11.2026 — host System exit: native ordering restored (SOURCE)

## Cause established in code

The old confirmed-Yes hook returned before the original01C0D050 functor wrote
MenuMan+250 and native save latches. TickBbscPendingQuit then manually saved,
suspended persistence, called Stop and cleaned remote actors while both the
System-exit selector and event request were still zero. It published the exit
only after native idle/PartyTitleReady. This reverses native ordering: StageFlow
can admit the ordinary world-return transition during the gap (task+153=1,
exit-kind task+150=0); later writing a menu latch does not repair an already
selected transition. The16:48 log confirms custom Stop/world reconstruction but
cannot identify the exact intermediate native instruction executed in that run.

Actual1.09 instructions executed on isolated memory reproduce the distinction:
original Yes writes+250/+25C/+1547/+1548 together; native01940DBB..01940E86 sets
exit-kind+150 even while save is pending and admits+153 only once native save
flags settle. The old zero-selector window reaches admission with+150 absent.
Earlier tests checked only eventual+150 after manually setting+250, missing the
ordering window before that write.

## Fix and removed intervention

Host/searching host and confirmed own-world idle System exits now resume the
original Yes body. The game owns save/latch/Stop/menu closure/title selection;
BBSC no longer drives a custom save, Stop, cleanup, CloseMenus, OnReturnTitle or
late+250 replay for these roles. BBSC only flushes journals, cancels reinsertion
and releases session persistence on confirmation, then notifies peers/cancels
Party once at the existing native Stop hook. No additional hook is installed.
Native exit observation blocks the legacy Lua fallback from issuing another Stop.
Notification state is retained independently of idle-time quit-prepared resets.
Duplicate confirmation preserves the existing exit latch.

Removed HoldBbscHostQuitInput, its captured Lua/menu values, cancellation restore
and repeated pending/title tick writes. Original native input/menu lifetime owns
this path. Guest/joining save-before-disconnect and Party title gate are retained;
their ordering was not replaced without equivalent native gameplay evidence.

## Validation and limits

PASS tools/test_menu_quit.py: production host/idle native ownership, one-shot peer
notification despite idle resets, duplicate selector preservation, guest save/
Stop/Party/cancellation; negative control with host native bypass disabled FAILS
as expected. PASS tools/test_title_request_native.py out/exit-study.elf: original
Yes, save-wait exit-kind retention, old-window world admission and prior title/
StageTransition controls. PASS test_hook_resume.py (actual Windows trampoline),
test_native_leave_release.py, MOD C++ syntax exit0. No real save test or mutation.

SOURCE ONLY. No DLL build/install/game restart, commit/pin/push. Original game
assets/settings/saves untouched. Actual title arrival/staying and subsequent
Continue require gameplay confirmation after a separate build/install.

## Earlier active-run analysis (historical uncertainty before native audit)

# 06.11.2026 — host System exit reload: analysis OPEN

User reports host returned to gameplay after System-menu exit. Current run:
PC native37684/run_20261106_164236, laptop17868/run_20261106_164252.
PC snapshot: parent out/coop-dev/runs/native-execution-pc-laptop-20261106/
pc-20261106-164935/game-16/run_20261106_164236.log.
Laptop snapshot: same parent/host-menu-20261106-1651/laptop-run_20261106_164252.log.
These are active-run snapshots; PC collector marks ChangedDuringCopy.

## Evidence (MSK)

- 16:48:18.463 PC native Stop, state3/host, reload phase4, reinsert=false.
- Then PC recreates CSChrThread/CSClothThread and reads map resources.
- 16:48:19.379 laptop native Stop, state6/guest, reload phase4, reinsert=false.
- 16:48:32.374 PC performance window again includes NPC pass/scaling/game ticks.
  Together with the user's observation this supports a world reload after exit.
- Measurement environment explicitly set BBSC_LOG=warning and disabled timeline,
  research and Party diagnostics. Confirmation/save/Stop completion/title handoff
  INFO messages are unavailable. Their absence does not prove hooks did not run.

## Code boundaries

TickBbscPendingQuit saves, stops native session, awaits PartyTitleReady, invokes
OnReturnTitle, closes menus, restores System-exit latch MenuMan+250. Prior04.11
analysis established +250 selects StageFlow task+150; do not revert this solely
on the superseded01.11 explanation. Existing native fixture covers only a branch,
not full StageFlow/title arrival.

ReleaseBbscQuitTitleAtLoad clears committed quit on native/world-ready completion,
session0 and own-world flag+1592. This condition does not independently distinguish
an erroneous own-world reload from a user selecting Continue. It is a diagnostic
gap/possible aggravating guard release, not proof of the initial reload writer.

Exact cause OPEN: snapshots cannot establish whether title intent/latch was lost,
overwritten, or a competing stage operation already existed. Need narrow quit and
StageFlow/request-writer tracing to distinguish these paths; no repeat requested
solely on speculation. No runtime changes/build/deploy/tests/save/settings changes.
