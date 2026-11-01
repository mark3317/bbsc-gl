# Native System menu: save before co-op exit

01.11.2026. User reports guest remains connected in title and only disconnects
after Continue has loaded the host world. Existing Lua RegistReturnTitle and
OnReturnTitle hooks have no runtime entries for those exits.

## Corrected native path (02:58 build, 01.11.2026)

The 02:47 laptop run never entered the old hook. Those +1B4/+118 sites were
unrelated generic dialog paths, not System Exit Game. Their hooks were removed.
Followed the port's actual EXIT_GAME_OPENER (BN 0200C9F0 -> image 01C0C9F0),
its relocated functor vtable 05344A10, slot +10 -> Yes callback 01C0D050.
That callback requests native saving and ends with MOV [MenuMan+250],1 at
01C0D0C4. This is now the byte-verified, deferred exit store. Cancellation
keeps +250=0 and clears the save-before-exit latch +25C; completion releases
+250 only after successful native save and session state 0. Generic dialog and
viewport fields are no longer modified.

Native full-save/poll functions remain 0156D570 and 01832160 (epilogue
018322F4), manager singleton 0556D438. No change to the save/disconnect wait logic.

## Implementation

- Confirmed button snapshots the BBSC trip journals and defers the native exit
  request store at +250. Original menu control flow continues, never returning
  from a mid-function hook.
- Game-thread tick/load-step waits for an older autosave, requests a fresh full
  native save, then waits for that manager's successful result and native idle.
- Only then: flush journals again, send leave using old session identity, lift
  persistence, issue native StopRequest; keep title results held until native
  session state reaches 0. Rejoin remains blocked throughout this second phase.
- Reinsert, self-heal, join teleport and follow do not revive/rejoin/warp the
  player while this exit is waiting for its save.
- Save rejection/error, 30-second timeout, loading, changed world/slot/session
  or missing session manager cancel the exit without initiating disconnect.
  An in-progress native save is not interrupted or deleted. Native save error
  handling remains intact. A separate disconnect wait timeout cancels the title
  exit rather than allowing Continue to race an unfinished Stop; it cannot undo
  a native disconnection already requested. No manual session-state writes or save-file edits.

Existing native guest-save snapshots plus BBSC own-world/item/trip journals are
retained; no shared-progress policy changes. A changed session during save is
an independent departure and aborts this pending menu exit. A solo exit retains
native behavior. The peer's existing leave path handles the departure; it does
not intentionally end a three-player group when one guest leaves.

## Validation and remaining checks

`tools/test_menu_quit.py` executes production state-machine functions with a
memory/native-call fixture: host/joining/guest, duplicate confirmation, old
autosave, wrong manager, idle without completion, pending/error/success,
timeout, load/slot/session changes, missing manager, solo and unsupported-hook
paths; verifies journal/save/notification/Stop order and title-request deferral.
`tools/test_hook_resume.py` compiles the actual Windows trampoline and executes
it against synthetic code: mid-function resume preserves stack/return, skipped
store stays skipped, default function-entry skip still works.
Existing 18 post-load recovery scenarios PASS. Hook signatures/instruction
boundaries checked against local eboot. DLL build exit=0, no compiler warnings;
First save-gated DLL build passed; the final completion-gated build hash is recorded below.
The completion-gated refinement also waits for native session state 0 after Stop;
final build validation is recorded below.

Not deployed. In-game validation remains necessary: pickup/quest/echo progress
then confirmed quit; host loses guest while guest is in title; Continue starts
in the guest's own world without a delayed disconnect; fresh summon works.
Also check Cancel, repeated exits, host departure during the save and three
players (one guest exits, the other stays). Do not describe crash-free gameplay
or inventory/world restoration as verified solely from fixture tests.

Final completion-gated DLL build: exit=0, SHA256 `457CE260B129C997F065C33BFEB85B8D254D94CA1CE8CD4E4FD6D9137F86F15D`.
Code: standalone `7ed396b`, bundled `203516d`, BBGL pin `0277410`.
Menu/save, actual trampoline, and post-load fixture checks pass. Not deployed.

Corrected hook build: DLL SHA256 `40E40031A38A9EB1E986B3EB6096D828F8E2D996C9B05B1813538A7177A5FF4F`.
Deployed on PC and laptop, source `9e067a4`. Only targeted menu fixture, actual
ELF opener -> functor -> store trace, DLL build and installed-hash checks ran.
Gameplay result is still pending. Backups: menu-exit-20261101-025822 (PC),
menu-exit-20261101-025825 (laptop).

## Successful user run — 01.11.2026, 03:03

User confirms client disconnects on menu exit. Laptop log
`bbsc-mod-20261101-025956-15584.log`:
- 03:03:07.684: native menu confirmed, saving slot 0.
- 03:03:07.794: native save completed, explicit leave and Stop issued.
- 03:03:08.343: native session state 0 observed, title request released.
- 03:03:23.694: 30 own-world flag groups restored during home load.
- 03:03:23.747 / 03:03:57.775: shared progress merged (25 then 12 world
  flags; no boss flags); pre-merge backup recorded.
- 03:03:24.504: 8 own quest flags restored.
- 03:03:58.732: previously taken item record retained; ledger reconciliation
  required no key-item grants. Own-world cleanup finishes in session state 0.

No save rejection/cancellation, CHECK FAIL, or native Fault in this run. The
only mod warning predates exit: host flags unavailable during the initial
join (03:02:49.728); it is not evidence of a save-write failure.
`userdata0000` exists at the expected 1,310,720 bytes and was updated at
03:04:09 (later autosave); metadata file updated at 03:04:28.
Raw logs preserved under `coop-dev/runs/20261101-menu-exit-confirmed` on PC
and laptop. Save contents were not manually modified or exhaustively compared
item by item. Confirmed scope: native save-before-disconnect, title release
after disconnect, own-world/quest/taken-item recovery after continuation.
Three-player departure and save-error behavior still rely on code/fixture
checks, not this two-player run.
