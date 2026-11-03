# 03.11.2026 — native transition for confirmed title exit (source only)

User: host still walks during dd47b2c menu exit. User rejected manual input
blocking and requested native SendPhantomHome-like lifecycle, no game build.
Review: parent out/coop-dev/runs/quit-input-review-20261103-091609. Host confirmed
09:13:40.123, Stop09:13:40.177, final/title09:13:42.334. Previous tests covered
an isolated movement gate; they did not establish gameplay immobilization.

## Native evidence (read-only CUSA03173 1.09)

System Exit Yes01C0D050 sets MenuMan+25C, save request bytes+1547/+1548,
then MenuMan+250. Our early interception suppresses these competing save/stage
requests. It also used to close every menu before asynchronous save/Stop/final
leave, exposing the live own world, and attempted to hold it with DisableMove.

SendPhantomHome0138A4A0 selects native Lua event state2, forced-home map bank,
and calls StageTransition013CDE30. StageTransition itself sets global+08=1,
snapshots the native character and handles guest Stop/remote cleanup.
OnReturnTitle0138BAF0 only selects SprjEventMan request+08=2: it does not call
StageTransition or set the loading flag. This difference is verified from
instructions; the exact runtime reason the old movement hook was insufficient
is still unmeasured.

Original eventcommon.luabnd.dcx/global_event.lua: addressed KICKEDOUT ->
OnBeKickOut shows an information menu, schedules OnLeave_Limit after5s, sets
4047 and SetLoadWait. SetLoadWait013358F0 writes Lua event+8D=1. OnLeave_Limit
uses SetFlagInitState(2), SetSosSignWarp, SetDefaultMapUid(-1), WarpNextStageKick,
SetChrTypeDataGreyNext. WarpNextStageKick01332B80 calls StageTransition.
EventMenuBrake is separately CloseMenu -> SetMenuBrake; OnBeKickOut does not
call it directly. Flag4047 prevents duplicate leave events; it is not alone
proof of movement suppression. No explicit DisableMove in these Lua handlers.

## Change

Keep the existing System menu during native save and final distributed leave;
do not call CloseMenus during the wait. After successful save, native idle,
current-ticket durable final leave, and no active native load: select title
with OnReturnTitle, call the same StageTransition used by native home return,
then close the old menus. The retained title guard prevents a second request.
No forced-home map/position selection for a host, no fake session/loading writes.
Removed the quit-specific DisableMove caller, movement hook/r14 mutation,
per-character control snapshots/restoration, MenuBrake and LoadWait writes.
Cancel preserves existing native gameplay restrictions and leaves menus owned
by their native controllers. Both menu roles use the same transition ordering.

## Validation and limits

Production menu state-machine fixture PASS: host/joining/guest/idle, native
menu retained until final ACK, title selected before transition, exactly once,
no forced-home bank, unrelated native load guard, save/Stop completion,
errors/timeouts/slot/context/duplicate guards and no manual control writes.
Two private RPC tests PASS (7.606s): current title ticket and host retained-bell
final guest drain/release. Only isolated fixture compilation was used.
No DLL/native port/package build, installation or game launch. FPS60 setting
and installed dd47b2c remain. Gameplay outcome is pending a later authorized build.
