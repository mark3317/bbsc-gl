# Guest return from a host chalice — 06.11.2026

## Evidence

Both running234844/234843 profiles collected in parent
out/coop-dev/runs/chalice-dream-return-20261106/pc (2 files, warnings0;
live snapshots). Roles changed after the earlier menu test: P1 now HOST,
P2 GUEST. P2 selects slot2 and enters channel3996722017841681/revision11,
layout1D0A0050, arrives00:08:35.550. Original t290110 sets72900200 at
00:08:46.379 (lamp activation), then72900100 at00:09:00.051 (Dream return).
The latter is journaled as a personal quest flag; no independent return or
native stage request follows. At00:09:36.647 the guest uses Silencing Blank,
leaves the session, reaches Dream00:09:45.402. This is NOT a successful
retained-session lamp return.

Original read-only1.09 ESDs t290110..119 instantiate lamp template with
map290 and index0..9. Return helper2147483641/c1_11 computes
70000100 + 290*10000 + index =72900100..109. Activation helper2147483639
uses70000200 instead, yielding72900200..209. The legacy ESD reader prints
the multiply opcode as '/', which must not be interpreted as division here.

## Source correction

The shared travel-flag predicate omitted72900100..109, so BOTH the native
guest command range and early travel interception excluded actual dungeon
return requests. Add those ten return flags to the existing travel route.
Require matching native lamp talk290110..119 and a current m29 map. The
existing queue clears requested dungeon mount/ritual, targets Dream2102950,
and releases the EXACT original return flag for the original native event.
This occurs before personal quest journaling. No extra warp, changed native
animation/wait, activation interception, session leave or save edits.

## Validation/status

New production test_chalice_dream_return.py FAILS old source at guest native
command admission, PASSES corrected: all10 lamps, both roles, exact original
flag release, arrival lifecycle, retained role, cleared altar context; unrelated
lamp/NPC/remote actor/map, activation/zero/offline/feature-off exclusions.
Read-only original ten ESD template arguments and return expression PASS.
Existing production travel and original ESD/native animation checks PASS;
existing Dream loader regression and original native map-selection bytes PASS.
Allocated-memory fixtures only; no real game/process/save writes.
Full MOD syntax recorded in parent run syntax.log. No DLL build/deploy/restart
in this task: two games continue running. Gameplay remains OPEN until the next
coordinated binary: activate a dungeon lamp, select Dream, arrive without
Silencing Blank/disconnect; check both roles and repeat after changing layers.
