# Joined claim retirement, title controls and own-world save position — 02.11.2026

Status: source only in bundled and standalone. No DLL/package build/deploy,
server change, game launch or player save edits. Includes the previous source-only
guest bell restriction. Runtime verification is pending.

## Duplicate summons: retire a completed invitation

Review run room 113 had JoinRoom at 00:31:12.965, but retained claim remained
searchable, causing new native summon operations for the same user at 00:31:41.876
and 00:32:12.393. The broker's retry retention does not know room completion.

bbsc_http WatchSessionForStaleClaims now marks the own sign for Force consume
on first native guest state 6 (JoinRoom established), and retries failed cleanup
with the existing backoff. It leaves state 4 alone so slow/incomplete joins still
receive the original invitation. Uses the existing authenticated server-facing
identity SessionId/UserId and Force:true delete; other guests' signs are untouched.
ReadData re-arms retirement if a pre-join create reply completes after the first
acknowledgement. This closes publication/ack reordering. Lifecycle mutex serializes
cleanup with new creates, including departure/rejoin. No shadnet deployment needed.

## Why the 28-second exit waited

Old log: save completes 00:32:16.469, LeaveRoom not called until 00:32:44.203.
The duplicate summon request at 00:32:12.393 already returned HTTP 200 and was
fully read/deleted by 12.566. Therefore neither save nor HTTP reply causes the wait.

Read-only eboot trace establishes the native ordering:
01ED07A0 StopRequest sets session state 7 and calls 00C8ED70.
00C8ED70 calls 00C98070(reason FF000023). That allocates a task (kind 0xC)
and enqueues it through 00CBACA0, which appends to the scheduler's list.
It does not interrupt or remove the current task. 00CBABC0 removes a completed
head and advances the queue. Thus state 7 is a queued request, not a completed
room departure. A previous pending operation can delay LeaveRoom.

The last redundant summon and subsequent notify_multi_play_error are ~30 s
apart, consistent with its native negotiation timeout. Logs do not contain the
old queue-head object/type, so the exact internal timer/task identity remains
unproven; do not label a guessed task as verified. New LogBbscQuitQueue reads
queue length/head/type before Stop, so a future slow case identifies the blocker.
The fix removes the source of these redundant summons; it does not forcibly
mutate native session state, pop/free tasks, shorten unrelated native timeouts
or report that room teardown is completed merely because Stop was issued.

## Host control regression

The host has a living own-world character after native disconnect state 0.
Old TickBbscPendingQuit cleared its intent immediately after requesting title;
subsequent session/death/leave recovery could release menu brake and Lua load wait
while the host was still in the world. Guest control followed a different path.

Keep bbsc_title_quit until native character creation on the next Continue.
BbscQuitInProgress includes committed title intent, preventing release helpers
from unlocking it. Game-thread/load-step pending-quit tick reasserts the same
menu brake/load wait while the old context exists, with pointer-access checks.
Release on native_finish + own world + session 0; never on disconnect or the
event-request acknowledgement alone. A cancelled pre-title exit still restores
its original controls. Native menu reset handles title UI, not a simulated world
state or an artificial character freeze flag.

## Position loss: serializer input was the host warp bank

KeepBbscHomeSpot already captures map/position/heading before native summon.
However RequestBbscSessionWarp overwrites global+14F0/+1500/+1510 for cross-map
join/follow loads. A direct title exit bypasses GuardBbscStrayForcedWarp's normal
trip-home restoration. Native save code therefore serializes the wrong bank.

Byte-verified CUSA03173 1.09 native serializer:
- 0156AB75 tests global+1592; guest map comes from global+14F0 at 0156AB7E.
- 0156AB9F: map is already in EAX; hook before the header is serialized.
- 0156B45A/0156B484: RSI becomes global+1500/+1510. At hooks 0156B461 and
  0156B48B it is the source of the native 16-byte position/rotation writes.

Three save-input observers select the captured origin for a guest or a committed
guest exit, scoped to the captured character slot. They change the native saved
map value and vector source pointers, not live character position/world flags,
inventory, progress, or save files. Origin arrays are aligned/stable. If any
location hook fails installation, the shared enable flag keeps all overrides off
rather than mixing one origin field with another native field. Missing origin,
a different slot, solo and host saves retain native behavior. Keep origin valid
through title teardown; normal home/Continue cleanup can retire it afterwards.
Existing already-written saves are not rolled back or repaired automatically.

## Checks

PASS test_summon_cleanup: pending-join retention, completed-join retirement,
late-publication re-ack, failed cleanup/backoff, fresh publication and serialized
concurrent departure/rejoin.
PASS test_menu_quit: successful/failed save, native disconnect wait, committed
host controls reasserted, no release on request acknowledgement, native own-world
Continue releases, slot/session guards and original-lock restoration.
PASS test_home_return: production origin serializer values, map/position/rotation,
guest and committed title path, other slot/host exclusion, previous home-return
and native fallback behavior. Uses fixture memory only; no player saves.
PASS test_hook_resume: actual production trampoline with the native save-vector
LEA and callback-supplied RSI surviving, plus existing confirmation/skip tests.
PASS test_guest_bells: previous source-only restriction retained.
Full bloodborne_re.cpp and bbsc_http.cpp checked with production MSVC-target
compiler/includes using /Zs (no DLL or object output). PASS; only existing CRT
deprecation warnings from omitting the build's warning-suppression macro.
Both mod trees synchronized, diff whitespace checks PASS. No claim of in-game
control, restored location, or universally fast disconnect until user testing.
