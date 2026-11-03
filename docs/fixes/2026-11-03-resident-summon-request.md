# Resident summon request blocks later guests — 03.11.2026

## Latest run and correction to the previous diagnosis

Run17:44:10–17:57:32MSK. Logs and copied read-only party event journals:
parent `out/coop-dev/runs/second-guest-1744-review`; `final-pc` is the later
complete collection (9 files, warnings0). The first collection was taken while
all three games were still running; Windows file timestamps lagged writes.
Use the final collection rather than assuming its earlier snapshot was final.

P1 host: P2 enters17:47:43; P3 gets no claim until P2 exits17:49:47, then enters
17:49:57. P2 host: P3 enters17:51:30; P1 waits until17:54:32/33 and enters at
17:54:50 while P3 remains. Three actors/two cooperators are recorded at17:54:50;
all three leave17:55:28/29. Thus an apparent one-guest limit can also release
after a long timeout, not exclusively on a guest's departure.

The previous mask edits are active: slot maskFFFFFFFF throughout, ready mask0
while a resident guest is present. Co-op slots become2/2 with just one live
guest, consistent with live + queued accounting of the same invitation.
The old selection observer's `queued3720386000` is INVALID: it read candidate
manager+1C8 instead of SosStatus+1C8. Corrected to the status pointer at native
frame[rbp-6F0]. Do not use the old number as a queue size.

Read-only live process observations before exit: normal established insertion
tasks remain at6/6 (CreateWait), including the host's self task. A new remote
task can be3/3 StartWait and must continue blocking selection until ready.
No memory was written to the processes, and no game was terminated.

## Native mechanism and fix

Native18731A8..18731C9 allows selection only when SosStatus+1C8 is zero and
its post-completion cooldown+210 has expired.187796C0 counts queued requests
plus live cooperators. Online requests with entity=-1 at+34 persist in the
queue until the native summon-result completion removes them, a cancellation
occurs, or native55/180-game-second timeout paths run (187292A..1872B83).
The late second invitation above is consistent with the180-game-second path;
old logs did not expose the exact live queue count, so that timing correlation
is not itself a captured queue-age value.

Seamless insertion can establish a real resident character without the expected
vanilla summon-result callback draining that request. CompleteBbscResidentSummons
runs on the existing signature-checked SosStatus.Update game-thread hook and
uses native identity-bound completion18777D00, also reached by1336200,
13807E0 and138B180. It does not edit counts, unlink objects, manufacture claims,
change task states, shorten timers or bypass native selection/capacity guards.

Completion requires host state3, living loaded own world, no quit/title, a
cooperative remote task at6/6 with arrived/not-leaving flags, matching live
cooperator MemberId, valid PlayerGameData, and a queued request whose role AND
full TargetUserId/TargetCharaId pair match that actor. The native routine then
performs its own PlayerGameData-id lookup, request identity match, destructor,
unlink, count decrement, role backoff and status update. A signature mismatch
leaves native behavior unchanged. Guests/loads/invaders/unfinished/foreign
requests remain untouched. The observer now records the real status queue count.

## Can invitations be fully parallel?

Not safely by removing the queue checks. Native1873340..1873605 dispatches
requests from its list through one active_request_id at SosStatus+90 and one
completion/result context+88/+8C. It only dispatches when+90==-1 and consumes
one front request id. The session has one create/join operation context and
native insertion readiness guards. Builder1874B96..1874C92 also counts live
and queued members against total4 remote slots and role caps.

Removing the queue or ignoring counts would discard admission reservations;
bypassing the guards does not create independent response contexts. True
parallel invitation/response handling requires redesign of those native
transactions and failure/late-response ownership, beyond a safe gate patch.
The correction instead releases an actually completed invitation promptly,
retaining serialization only while a native operation is genuinely unfinished.
Multiple independent native clients and established members still run together.

## Validation

`python tools/test_resident_summon_completion.py` PASS: executes the production
policy plus exact native18777D00..18777EAB and selection queue/cooldown guard
18731A8..18731CA in executable scratch memory. Baseline: resident request keeps
the gate closed. Corrected: native free/unlink/update once, then native role
backoff, then selection opens. All five co-op roles; unrelated pending request
retained and continues blocking;21 rejection cases including loading/death/quit,
wrong task/member/role/account/character/signature. Allocation/deallocation
services and final status update are controlled stubs; actual queue list and
identity comparisons are the native instructions. This is not full gameplay.

Full changed BBSC_MOD translation unit syntax check PASS. Product build,
deployment and next gameplay confirmation tracked in the delivery entry.
No save/settings/journal mutation or VPS/protocol changes.

Delivery: DLL build0, six-file copy0; backup resident-summon-completion-20261103-180809. Coordinator41392 launched18:08:10MSK/15:08:10UTC, all existing profiles. Gameplay confirmation remains pending.
