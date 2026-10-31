# Native System menu: save before co-op exit

01.11.2026. User reports guest remains connected in title and only disconnects
after Continue has loaded the host world. Existing Lua RegistReturnTitle and
OnReturnTitle hooks have no runtime entries for those exits.

## Confirmed native paths (CUSA03173 1.09 eboot)

System confirmation handler starts at 01779AC0. Confirmed Yes writes
MenuMan+1B4=1, optionally its viewport result at +DA4+index*40=1, then
+118=2 at 01779E2B. Cancel takes separate stores with result 2 / state 3.
The alternate native quit path writes the global result at 01C28154.
Both confirmed sites are signature-checked; ordinary menu opening and Cancel
are not intercepted. Per-viewport results must be held as well as the global
result, or the native flow can observe exit before saving finishes.

Full save request 0156D570(-1,0,0) means current character, normal write, no
erase. It serializes while the session is still guest/host and publishes save
state Global+1554=1 only on accepted request. The native save manager singleton
is 0556D438. Its poll at 01832160 returns 1=pending, 0=success and other terminal
results for failure; observe the common epilogue 018322F4 without invoking
teardown on the save stack. Global+1554 must also return to idle after the
engine's own completion handling. Idle or an incremented save counter alone
is NOT sufficient: the engine can clear its save state on failure too.

## Implementation

- Confirmed button snapshots the BBSC trip journals and defers the native exit
  result/state stores. Original menu control flow continues, never returning
  from a mid-function hook.
- Game-thread tick/load-step waits for an older autosave, requests a fresh full
  native save, then waits for that manager's successful result and native idle.
- Only then: flush journals again, send leave using old session identity, lift
  persistence, issue native StopRequest, release native title exit results.
- Reinsert, self-heal, join teleport and follow do not revive/rejoin/warp the
  player while this exit is waiting for its save.
- Save rejection/error, 30-second timeout, loading, changed world/slot/session
  or missing session manager cancel the exit without initiating disconnect.
  An in-progress native save is not interrupted or deleted. Native save error
  handling remains intact. No manual session-state writes or save-file edits.

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
paths; verifies journal/save/notification/Stop order and per-viewport isolation.
`tools/test_hook_resume.py` compiles the actual Windows trampoline and executes
it against synthetic code: mid-function resume preserves stack/return, skipped
store stays skipped, default function-entry skip still works.
Existing 18 post-load recovery scenarios PASS. Hook signatures/instruction
boundaries checked against local eboot. DLL build exit=0, no compiler warnings;
SHA256 B02761E21BD8E86DC4D4129A722D72790216856FEA8E995517B8DD2B23AC3A13.
Code commits: standalone 48604ee; bundled BBSC-GL 03f640f (later commits add tests/docs).

Not deployed. In-game validation remains necessary: pickup/quest/echo progress
then confirmed quit; host loses guest while guest is in title; Continue starts
in the guest's own world without a delayed disconnect; fresh summon works.
Also check Cancel, repeated exits, host departure during the save and three
players (one guest exits, the other stays). Do not describe crash-free gameplay
or inventory/world restoration as verified solely from fixture tests.
