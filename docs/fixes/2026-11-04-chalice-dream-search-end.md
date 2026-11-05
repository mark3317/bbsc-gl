# Chalice → Dream: search timeout arms host Blank cleanup

Status: SOURCE FIXED / gameplay OPEN. Not built or installed.

## Implemented correction

`TickBbscHostBlank` no longer treats loss of Beckoning effect as Blank evidence.
Only actual item entry/runtime item state, native Blank effect or confirmed menu
silence can arm explicit cleanup. `TickBbscHostSearchLimit` still erases search
effect9000 at300s and announces expiry, but calls PartyCancel only in solo state0
to discard a pending acquisition. Established host state3 retains its room and
follow traffic. Explicit item/effect/menu cancellation paths remain intact.

Production native fixture executes the live sequence:300s expiry with two guests,
46s delay, load with empty actor table, first Dream frame with self only, another
4s reinsert window, then guests restored. No native Stop/cleanup/leave/PartyCancel;
host stays state3. Passive disappearance with an already empty host also retains
the room. Explicit item/effect/menu cancellation and real empty-room drain PASS.

Targeted validation: tools/test_blank_host_end.py, test_matchmaking_native.py
(BBSC_MOD branch, active host vs solo expiry), test_menu_quit.py,
test_follow_arrival.py and test_chalice_scope.py PASS. Complete BBSC_MOD C++
syntax check (/Zs) exit0; targeted diff --check PASS. No save/recovery tests run.
The previous test expectation that passive bell disappearance should close a
host was replaced by explicit menu confirmation plus the nontermination cases.

This correction removes the demonstrated passive-expiry trigger; no broader
redesign of explicit Blank intent lifetime or actor-drain policy is claimed.
No DLL/package build, installation, game restart, commit/pin/push or live
save/settings/journal/game-file changes. In-game chalice → Dream confirmation
with both guests remains required after deployment.

## Investigation (before the correction)

Latest three-profile run started14:39MSK on4 November. Host Player2;
guests Player1/Player3. BBSC HEAD and parent gitlink0ddb1d4 plus existing
working changes; preceding build/install recorded in HANDOFF. Logs captured
15:00:30–43MSK into parent out/coop-dev/runs/chalice-dream-crash-20261104.
All three game files changed during copying: live snapshots, not final logs.
Standalone mod logs are older; current BBSC diagnostics are in last_run.log.
Party event journals and Windows Application/System evidence also collected.

## Confirmed sequence (MSK)

-14:58:36.093 host logs `host bell: search ended after 300 seconds` followed
 by `host Blank/search end observed (item false, effect false, search ended true)`.
-14:59:22.942 host completes Dream load, generation8.
-14:59:22.947 host announces map0x15000000 to two peers; world sync still
 reports three members. Native character population then reports self only.
-14:59:22.948 host calls native Stop and logs `empty host room stopped after
 Blank`; the next native stop phase still has three members in room536870949.
-14:59:23.116/23.173 Player3/Player1 handle confirmed host departure and stop;
 both progress from guest6 through leaving7 to solo0.
-14:59:25.332/25.548 Player3/Player1 invoke return to their own original Dream
 position. Dream arrivals14:59:33.431/34.341, respectively.

This is session termination with forced home return, not a process crash.
At inspection all three native processes from14:40 remained alive
(6396/14548/15328); game logs continue after the departure. No DeviceLost,
unhandled/access-violation, critical/fault-stack markers in captured logs.
No System153/4101 events in14:35–inspection window. Application1000/1001/1002
results in that window concern FarmingSimulator2025Game.exe at14:38, not this run.

## Code path and limits

`TickBbscHostBlank` treats `search_ended` as equivalent to item/effect evidence
and arms static `blank_ms`. `CloseBbscEmptyBlankHost` accepts that marker after
three seconds and checks the current character list for self only. It does not
require an explicit Blank/cancel, continuous emptiness, or exclude the native
reload/reinsert phase. The marker stays armed through the load for up to120s.
Thus an ordinary search expiry at14:58:36 becomes native Stop on the first
Dream frame with guests temporarily absent46.855s later. The log has reinsert
true/reload phase4 at that Stop, while the network room still has three members.

The earlier host-dream-retirement change protects automatic Party terminal
certificates. It explicitly left Blank/menu drain unchanged; this is a distinct
native Blank cleanup path. Do not label the prior Party fix sufficient for Dream
travel or infer a new GPU crash.

The investigation recommended distinguishing passive search expiry from explicit user
cancellation, scope pending Blank intent to its session, and prevent transient
load population from authorizing room teardown. Preserve real Blank/menu exit
and selected-member kicks. Target production native fixtures for search expiry
with active guests plus Dream reload, explicit empty-room cancellation, and the
existing Party retirement path. Gameplay confirmation remains required after
any implementation/build/install.

During investigation no games terminated/restarted; no real save/settings/live-journal or game-data
changes, commit, pin update or push. No code tests needed for investigation-only
documentation.
