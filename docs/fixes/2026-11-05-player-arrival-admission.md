## 05.11.2026 — retained-session player summon render hold, SOURCE fixed; gameplay OPEN

Follow-up to second Dream entrant diagnosis below. Read-only observations of the
same still-running230550 pair found P2 HOST's remote guest has activation4/4,
disabled0, assembly_visible1, alpha1/1/1, correctly attached16 mesh parts, but
PlayerIns+1E2 bit4 CLEAR. Native part node+210 bit0 is consequently CLEAR (3E),
while the corresponding guest's own nodes and opposite-direction host copy have
3F. Both peers' coordinates agree. Evidence: parent run player-dream-second-
20261105/live-render.jsonl and live-render-gates.jsonl. These are later same-run
samples, not an atomic capture of the exact original23:07:43 Dream frame.

Original1.09 establishes the cause chain: constructor018B9DAA starts draw bit12
of+1E1 (=+1E2 bit4) enabled. FirstSync01E502C3 explicitly clears it for types
1/2/12. Native PlayerIns render gate018F4830 tests that bit; failure at018F48E6
clears ALL part node+210 draw bits, regardless of valid scene/opacity. Normal
StageFlow admission193A93C enables it, but retained-session recreation happens
AFTER the stage has finished; ordinary summon-only presentation completion no
longer covers this new actor. Retrying FirstSync simply repeats the render hold.

Correction: arm a one-shot native-task/member/world/local+remote visit admission
ONLY when the independent controller explicitly requests native recreation.
At exact FirstSync AND, production Windows trampoline skips ONLY those8 bytes
and resumes01E502CB; constructor flags and ALL following native setup execute.
No mesh/draw-byte/opacity/death writes, native renderer/culling still controls
visibility. Initial/legacy summon is unchanged. Guard role, task4, exit bit,
phantom type, living same-place peer, world/both visits, native task identity,
15-second expiry; prune on world/visit/member/timeout and completed binding.
Other types follow original native branches; log hold bypass and draw_admitted.

PASS: tools/test_world_player_render_admission.py executes ORIGINAL FirstSync
branches/AND and COMPLETE ORIGINAL018F4830 renderer through the ACTUAL Windows
trampoline. Original path makes a ready/attached synthetic player invisible;
scoped hook keeps it drawable for both roles/types1/2/12. One-shot/expiry,
world/visit/dead/loading/self/leave/initial-summon guards, types0/3/9 original
branch, native hide/render-off gates, stack and native R15 continuation PASS.
Production lifecycle (actual arm/completion/prune), original scene attachment,
authority/routing/native19 hook spans and full BBSC_MOD syntax exit0 PASS.
Fixture memory only, no game input/process memory writes/save or asset edits.
No DLL build/deploy/restart; two games continue running and other source chats
are active. Installed23:05 remains unchanged. New gameplay confirmation OPEN.
This supersedes the earlier cause-unknown diagnosis for the reproduced native
hold mechanism; exact original Dream frame was not captured.

## 05.11.2026 — second Dream entrant still cannot see resident, diagnosis ONLY

User reports the second Dream entrant cannot see the first. Installed23:05
coordinated build INCLUDES player mesh scene admission/arrival cleanup; do not
attribute this to the earlier fix being absent. Both230550 profile logs collected
in parent out/coop-dev/runs/player-dream-second-20261105/pc (2, warnings0,
ChangedDuringCopy=true; live snapshots). P1 is GUEST, first Dream arrival
23:07:25.130; P2 is HOST, second Dream arrival23:07:43.377. P2 requests P1
recreation23:07:43.377 and binds actor1026bac670/mesh1026bf5140 at23:07:43.835.
P1 recreates P2 at23:07:43.399 and binds23:07:43.684. No scene-attachment
correction/retry/hide for P1 on P2 is logged during this Dream meeting.
Thus native creation AND the new assembled-parts/scene-link readiness passed,
but neither proves rasterized visibility. Prior scene fix did not solve the
user-observed case; player visibility remains OPEN.

Additional read-only process snapshot saved as live-scene.jsonl in the same run
folder: both actors have16 populated part nodes, all scene/root links match.
Native tasks6/6 and activation4/4. Coordinates match the other process. Snapshot
is non-atomic and already overlaps P2's NEXT travel to Yharnam (native request
23:09:01.852; P1 hides departed P2 at23:09:01.898; P2 arrives23:09:06.750).
Do NOT infer the earlier Dream failure from snapshot fade/disabled fields or
from global+0C (a pending/stale selected destination, not current rendered map).
No per-part draw/cull submission or exact-incident render trace is available;
the actual invisible-model cause remains unproven. No gameplay source edits,
build/deploy/restart, game input, live-memory writes or save/asset changes.

## 05.11.2026 — player mesh scene admission, SOURCE ready; gameplay OPEN

User again reports missing player meshes in the installed22:19 build. Collected
both profiles in parent out/coop-dev/runs/player-models-20261105-followup/pc
(2 logs, warnings0; live snapshots, ChangedDuringCopy=true). P1 guest222014 / P2
host222015 both request recreation and bind at repeated reunions22:22–22:25.
The earlier per-journey admission DOES run; binding is not mesh visibility.

Read-only process observations additionally found active4/4 remote PlayerIns,
normal alpha1/1, disabled0 and mutually consistent remote/local positions.
Draw-state+0C was0 for BOTH local and remote actors. These observations do NOT
prove visible meshes or establish detached scene links in that live incident.
No writes to running game memory, game inputs, save edits or game asset changes.

Confirmed source gaps: DrawModule+28 is an allocated state, not assembled meshes;
its presence let an empty/detached mesh become Resident and bypass recovery.
Native player virtual+B0/018F4A50 attaches c0000 parts+4D0 to WorldChrMan+5FC8;
FirstSync calls it before asynchronous actor activation/model completion.
The controller now checks actual assembled part nodes and their scene/root
links, calls the ORIGINAL idempotent attachment for settled, living, same-place
peers with detached parts, then rechecks. Empty assemblies retain bounded native
recreation. No opacity/death/draw-byte overrides. Binding logs include actor/mesh.
Per-character recreation now also calls native015BC080(manager,handle) BEFORE
019186E0 removal, matching native Delete01E50C19/54. This clears retained arrival
entries before a handle is reused; native arrival creation rejects duplicates.

PASS: previous production Tick fails the detached-scene regression; corrected
production fixture passes detached/empty/ready assembly, no repeated attachment,
bounded recreation, local/remote travel, task absence, apart/loading/pending-task
gates and per-handle cleanup order. ORIGINAL1.09 018F4A50 executed on allocated
fixture parts/scene, dispatching to fixture list callbacks via native ABI. Native authority/routing
fixture and original callable/callsite/part offsets PASS; full BBSC_MOD syntax
exit0; diff --check PASS. These tests do not establish the live symptom's exact
scene links or visible gameplay result. No DLL build, deploy or restart in this
task; integrate with coordinated build. Bug remains OPEN for gameplay.

# Player models after travel into an occupied location — 05.11.2026

User reports missing player models again after the 21:29 build, and requests
installation and two-profile startup after correction. Installed source included
1d5d7ef; this is a follow-up, not an uninstalled copy of that earlier fix.

Player1/2 run_20261105_212953.log: P1 host enters Central Yharnam at21:34:36
and binds the resident peer at21:34:36.613 without requesting recreation. P2
requests a missing actor at21:34:38.328 and binds at21:34:38.917. On the next
reunion P2 recreates at21:36:15.713, P1 only binds at21:36:16.465. Bind messages
do not prove visible meshes. These logs do not contain the bound actor address,
so they cannot prove the exact allocation path responsible for the symptom.

Confirmed controller gap: its mandatory journey refresh depended on equality
with the previous actor address. A new PlayerIns address plus existing draw
state could bypass native FirstSync entirely, although retained member tasks
were already at CreateWait. No actor also fell through to a delayed retry.

Refresh now follows the meeting/local or remote visit transition regardless of
actor address. It waits for a settled native task, then requests existing native
per-character removal/FirstSync once. The actor supplied after that request is
left alone; recovery retries remain bounded. Initial session observations keep
native admission. No opacity/draw/death manipulation or new network protocol.

A second confirmed gap discarded peer lifecycle history whenever its native
task temporarily disappeared, even with room membership intact. Retain history
by membership instead. A separate production regression FAILS before/PASSES
after; an actual member departure still discards its previous lifecycle.

Validation: production TickBbscWorldPlayers fixture first FAILS on new-address
local travel with the old controller, then PASSES with the correction. Added
remote travel with changing addresses while task is pending, immediate missing
actor admission, and no repeated restart after admission. Existing reused-address,
apart/reunion, unfinished actor and four-peer cases PASS. Native authority/routing
fixture PASS. Fixtures use allocated memory only, no game processes or saves.

Build/deployment: coordinated DLL build and five-file delta exit0; main install
updated21:54:40 MSK with completed enemy/host-altar source. Backup:
D:/Games/Bloodborne/coop-dev/backups/player-arrival-fix-20261105-215440.
Existing Player1/2 entrypoints launched21:54:53 MSK. Parent run record:
out/coop-dev/runs/player-arrival-20261105. Gameplay visibility remains OPEN.
