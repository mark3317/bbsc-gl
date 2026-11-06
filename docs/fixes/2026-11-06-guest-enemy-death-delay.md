# Guest lethal-hit delay while separated — 06.11.2026

## 05:56 diagnostic run: predicted HP0 loses native lethal edge; SOURCE corrected

User again reports delay, then asks to preserve native death for a guest in the
zone they simulate. Keep local responsible-player death fully native; followers
must apply authoritative confirmation through the same native lifecycle, not
reconstruct death from a mod HP cache or make every nearby player an owner.

Fresh stable055637/055731 logs collected after exit in parent pc-repeat-0556,
2files/warnings0. P1 hostaf899c81/P2 guest82d89c47. COMBAT trace is present on
BOTH clients this time (435/1014 lines across loads). Exact selected raw events
are also saved in parent confirmed-lethal-timeline-0556.json. Some log lines
interleave with PERF text; only intact timestamped evidence is used below.

Central Yharnam, same NPC native handle285c:

- P2 hit-selection06:18:18.017 HP225; native hit15 intent18.018; predicted
  HP0 by18.030, death0. P1 receives that native hit18.078, immediately executes
  HP-set(-32542), native death-worker with death1. Thus hit delivery is~60ms,
  not a seconds-long backlog.
- P2 authoritative HP-set18.304 sees oldHP0/requestedHP0, still death0.
- P1 state3D fingerprint e616b160337126bf at18.955 is received/admitted on P2
  at18.967:12ms. P2 remains death0, then reports death6 at21.229 (+3.199s from
  predicted HP0). NPC285d repeats: P2 HP0 at19.241, owner processes19.269;
  matching state sent20.232/received20.260 (+28ms); P2 death6 at22.503.
- Control example6028 in Byrgenwerth: host kills it; P2 HP-set at06:02:03.184
  starts from762, immediately enters original death-worker with death1. The
  failing distinction is P2's predicted zero BEFORE the authoritative zero.

Original1.09 explains this exact race. NPC HP receive sets native pending bit10;
01916EEF captures old actor HP, 01916EF5 stores it at [RBP-140], original setter
applies the owner value, then01916F38..01916F5B calls native Kill018BF9A0 ONLY
when captured oldHP>0 and resulting HP<=0. A locally predicted HP0 makes the
confirmed0->0 case skip that original call. No native death-request bit is set
then, unlike the positive->zero control. Waiting for later state completion
explains the traced symptom; do not label the12/28ms state delivery as the delay.

Correction in the original HP application path:

- Confirmed record/pending bit still comes from the current block owner's native
  receiver. At01916EF5 ONLY the old-HP scratch EAX is promoted0->1 when incoming
  HP0 confirms an awake remote-owned NPC with no requested/in-progress/completed/
  historical death and no native dead/proxy exclusion. The original instruction
  stores that scratch, original setter runs, original positive-edge branch and
  original single Kill call perform the death. Hook never writes actor HP or
  death, never calls Kill itself, retains original revival/proxy/loot policies.
- Already-dead/duplicate packets cannot repeat the native death. Nonzero HP,
  negative oldHP, sleeping/disabled actors and native invalid-HP sentinel retain
  their original behavior. This is not a per-tick zero-HP kill/watchdog.
- Original application loop formerly ran only guest6/outside-own-world. Block
  simulation now enters that SAME loop for either role after scene admission,
  then drops pending data for local/unadmitted/reassigned actors before applying
  it. A guest owning their own block retains local native death; a room host
  following a guest-owned block can also process its native confirmations.
- Three new native spans, both continuations, positive-edge branch and exact
  original Kill call are byte checked before installation. No protocol/cache/
  timer/AI/visibility/save changes.

Validation: tools/test_native_lethal_confirmation.py runs ORIGINAL1.09 pending
bit lookup/consumption, HP unpacking/application, edge branch AND original Kill
proxy/revival bytecode using production Windows trampolines on fixture memory.
Predicted0+confirmed0 starts death once, duplicate/no-pending/old negative/nonzero/
local-owner/unadmitted/load/dead/historical/proxy/sleep/sentinel paths PASS, both
roles and legacy/Dream/disabled admission PASS; native revival clamps HP to1.
Old-edge negative control FAILS exactly missing native death assertion. Existing
native hit/state/HP/block runtime and original30 site ABI PASS. Full MOD/relay
syntax exit0, build/native-lethal-confirmation-syntax.log, existing warnings.
SOURCE corrected, gameplay OPEN; new DLL not built/deployed. A fresh game PID26932
started06:39 while analysis proceeded; no process was stopped or modified here.
Other chats' source edits preserved, HEAD/pin4989896 unchanged, no mixed commit,
saves/settings/game-asset edits or push. Earlier all-fixes-installed runs remain
failed gameplay evidence; only a new installed game check can close this bug.

## Installed03:18 repeat: gameplay still FAIL; bounded combat trace SOURCE

User again reports delayed death after the shared03:18 update. HANDOFF/common
run record confirms it contains BOTH previous corrections. Logs031857 from P1
PID5220/P2 PID21568 collected after both exits, parent pc-repeat-0318: two files,
warnings0, ChangedDuringCopy=false for both. No game process remained to sample.
The previous source fixes must not be described as resolving this gameplay bug.

Observed: P1 host558b88b5, P2 guest9aa41383. P2 Old Yharnam ready03:21:41.294,
block17000000 owned by P1. No takeover of that block before P2's Dream departure
03:22:25.382. Across the full online run,118 host/115 guest sampled control queues
are empty. These samples do NOT measure native gameplay UDP packet delivery.
Steady03:21:50–03:22:20 frame windows: host55.02–57.06 FPS, worst63.927ms;
guest50.58–53.14 FPS, worst77.446ms. No one-second frame stall in those windows.
Thus neither a logged ownership handover nor a whole-frame1–2s freeze establishes
the cause. There are ZERO per-target COMBAT lines: neither exact lethal hit nor
native death transition of the reported enemy can be timed from this run.
Summary: parent latest-log-summary.json. Do not assign a third proven root cause
from these logs or assert that reliable state packets were slow/lost.

Added READ-ONLY source diagnostics in bbsc_combat_trace.inc. Explicit opt-in
SHADPS4_BBSC_COMBAT_TRACE=1 AND SHADPS4_BBSC_TIMELINE=1 is required on BOTH clients
at the NEXT diagnostic launch after rebuilding. Default off: the three extra
native observer hooks are not even installed, preserving ordinary/perf runs.
No profile/settings edits or automatic build/deploy/start were done here.

Observations: target selection, native channel15 application entry019165C1,
HP setter018BCD40 entry (requested HP versus actual HP), death worker018BD9D0
entry (not proof of death completion), and subsequent per-tick actual HP/death
byte/action/proxy/native ownership. Native handles re-resolve from the current
CHR record each sample; no retained pointer is followed. Outgoing intent versus
incoming admission of5/15/3D/41 carries peer/owner/payload fingerprint plus
world/room/visit/map/load fencing. Send-intent is NOT a successful socket send.
Up to8 targets expire after15s; max512 lines/load, at most128 packet lines so
packet traffic cannot consume the actor-transition reserve. Repeated identical
zero-HP setter calls are deduplicated. No simulation state/HP/death/save writes.

Production observer fixture PASS: HP0 separated from death+1500ms, checksum of
all native fixture memory unchanged, recreation/unload fresh resolution, context/
session/load fences, expiry/caps and disabled no-memory-read path. Existing actual
native hit/state receivers and HP producer/receiver + original27 site ABI PASS.
Full MOD/relay syntax exit0, build/combat-trace-syntax.log (existing warnings).
Diagnostic DLL not built/installed. Bug OPEN; next evidence must locate whether
the remaining delay is before the native owner processes death, in delivery, or
after the follower receives state. No new speculative behavior correction.

## Repeat on installed02:54 build: HP fast, death late; target/state correction SOURCE

User confirms HP now drops quickly but death remains delayed on P2, describing
first enemies over the bridge from the Central Yharnam lamp. Fresh025439/025440
logs show P1 HOSTe4be33fd and P2 guestcbee1dfd, both Old Yharnam by03:00:55.815;
native block17000000 stays owned by P1. The02:54 common build DID include the
first dirty HP correction. This is therefore a failed gameplay confirmation,
not a test of the old receive-only DLL. Bug remains OPEN.

Logs: parent out/coop-dev/runs/guest-enemy-death-delay-20261106/pc-repeat-0254,
two files/warnings0; P1 changed during copy. Read-only process snapshots03:03:20
and03:03:59 show handle6159 HP0 on BOTH clients; P1 death byte6, P2 death byte0.
P1 ownership1, P2FFFF, both native activation4/4. P2's animation table eventually
matches P1's, so a blanket claim that ALL state packets were lost is unsupported.
The unmatched actor is not proven to be the exact1–2s kill originally reported.
No live-memory writes, inputs, game termination or save/asset edits were used.

Found a second definite native ABI defect: at01A2A102, RBX is the ATTACKER
(01A29E57 copies RSI), R12 is the target damage module (01A29E5A copies RDI).
The original native hit packet takes its target from [R12+8] at01A29FED. Our
block-role hook used RBX, so a local attacker's locally owned handle selected
role3 and suppressed native channel15 even when the TARGET belonged to a remote
participant. The native owner's authoritative hit/death path was bypassed.
Now selection uses the same [R12+8] target as the original packet producer.
Replicated-hit markers retain their original no-report path; unknown targets
cannot gain local authority or deliver a hit to an arbitrary member.

Also completed per-owner fencing for original native animation/state3D and
status41 queues, previously left outside block packet routing. Their records
are100/24 bytes, from original receiver loops018EF108/018EFD12. Both outgoing
and incoming records now follow the CURRENT target block owner, just like HP;
proxy/former-owner messages cannot overwrite authoritative state. Native payload,
ordering, queue drain and transport stay original; no extra timers, mod state/HP
cache, death reconstruction, repeated Kill or reward replay. Status41 skips
negative handles but asserts on-1, so rejected records use-2 on that channel.

Validation:

- New tools/test_native_enemy_states.py executes the ORIGINAL1.09 full native
  hit-role/packet production plus state3D/status41 application loops using
  production Windows trampolines in fixture memory. Local attacker/remote target,
  remote attacker/local target, both roles and native replicated-hit suppression
  PASS. Current-owner state applies, proxy/stale/unknown source state does not;
  outgoing opaque payload/producer buffers retained. No real game is changed.
- Independent negative controls: old attacker-based selection FAILS actual hit
  delivery; old unfenced state receiver FAILS protection of the owner's state.
- Native block runtime, independent authority/original ABI24 hook spans,
  existing original native HP producer+receiver regression PASS.
- Full MOD/relay syntax exit0, build/enemy-state-target-syntax.log (existing
  compiler/CRT warnings). Native fixture setup needed its original divide
  constant initialized; final native hit and both state loops PASS.

New correction is SOURCE ONLY; not built/deployed or game-confirmed. Processes
1984/34844 were present at collection and later no longer running; none stopped
by this chat. The separate next-run preparation is for the user's planned common
update after optimization changes, so no competing build/deploy/start was done.
HEAD/pin4989896 unchanged; other chats' shared edits preserved, no commit/push.
Next gameplay check must verify actual death/states as well as quick HP, with
separated roles reversed. Earlier first-fix PASS described fixture coverage only.

## Source correction after user's follow-up

User requests correct senders/recipients and a fix. Found a concrete production
defect beyond the earlier ownership hypothesis: BbscWorldHpState unconditionally
selected native role6 in block mode, even for a participant owning blocks. Native
018EF578 chooses either role3 dirty HP production OR role6 reception. Thus the
dirty producer018EF809 (bit20) was never reached in block mode. Only the separate
018EF279 periodic ten-entry/every-fourth-frame sweep remained. A large native
table can therefore visibly lag despite an empty control queue. The existing
block owner's identity being the host is not itself proof of wrong ownership.

Correction: an admitted block owner selects the original role3 dirty producer;
participants without owned blocks keep role6. At the original common tail
018EF94F an owner continues ONCE into original receiver018EF6C6, preserving R12,
the native frame, and the manager load displaced by the trampoline. A per-thread
frame marker is consumed before re-entry, so exhausted receive returns normally.
Both the hook span and receive continuation are checked against original bytes
before installation. Native packets, dirty flags, batching and reliability stay
native; no HP cache, Kill/reward replay, timer changes or global role mutation.
Existing per-handle block ownership filters outgoing channels4/5 and incoming5;
hits0x15 still target the specific block owner. The new dirty path uses those
same filters, including when a map follower owns a block.

Validation:

- tools/test_native_hp_routing.py executes the ORIGINAL1.09 machine-code dirty
  scan/packet assembly/receive application through production Windows hooks on
  fixture memory. Kill at slot199 sends HP0 in the same call, receives a different
  owner's kill in that call, rejects foreign HP, covers both native roles, no
  owned block, load fencing, legacy and disabled paths: PASS. Only external
  network/member predicates are mocked. No game process/assets/saves are written.
- Negative control reinstating old receive-only selection FAILS precisely the
  immediate kill delivery assertion; detection PASS.
- tools/test_world_blocks.py and tools/test_independent_native.py PASS, including
  original native channel11/CHR and all22 current hook spans/receive target.
- Full MOD/relay MSVC-target syntax exit0; build/native-hp-routing-syntax.log
  (existing compiler/CRT warnings). Test setup initially needed fixture global
  pointer/ABI declarations corrected; final native fixture is PASS.

SOURCE corrected. DLL not built/deployed, gameplay OPEN. Both games37524/29340
from01:49 remain running; no termination, mixed commit/pin update or push.
The collected live logs alone still do not establish the timing of a particular
reported enemy. Confirm separated lethal hits and both-role behavior after a
coordinated update; do not mark the gameplay bug closed from fixtures alone.

## Earlier read-only diagnosis (superseded source status)

User reports damage immediately visible, but enemies die 1–2 seconds later
when the guest is far from the world host. Diagnosis only; gameplay bug OPEN.

Both live Player1/2 run_20261106_014900 logs collected without warnings in
parent out/coop-dev/runs/guest-enemy-death-delay-20261106/pc. Collection ends
02:35 MSK; Player2 file changed during copy, so this is a live snapshot.
Installed run started01:49; source HEAD/parent pin4989896 match, shared dirty
source preserved. No build/deploy, process stop, save/settings/game-asset writes.

Evidence:

- Player1 is guest851073bb, Player2 hostd21588f5. Host Central Yharnam
  block0x18010000 lease epoch1 at02:28:11.975; guest admits that host-owned
  block at02:28:27.030 and again02:29:06.323. No later ownership change for
  this block appears before collection. Guest owns adjacent block0x18000000;
  owning an adjacent block does not give authority over the Central block.
- Native block election retains an active incumbent; responsibility is by
  native CHR block, not by nearest player/enemy. Thus separation inside one
  block does not necessarily make nearby enemies locally authoritative.
- BbscWorldHitState chooses native host/guest hit behavior from target block
  ownership. BbscWorldBlockPacketSend retargets channel0x15 to that owner;
  HP channels4/5 retain owner filtering. A remote-owner hit/update round trip
  is a plausible contributor; exact death-completion path remains unproven.
- At02:33–02:35 sampled TCP control queues are empty, oldest_ms0, dropped0,
  dispatch_ms0. This does NOT measure native gameplay UDP latency/loss or
  exclude delays between samples.
- The1000ms block publication guard only suppresses identical records;
  changed records bypass it. It is not evidence of a mandatory one-second
  lethal-hit timer. Historical records apply once per admitted epoch.

Limits: no exact enemy handle, lethal-hit time, HP-to-zero/death-state timeline
or per-channel gameplay delivery trace is recorded for this report. Therefore
neither a precise1–2s mechanism nor a safe behavior correction is established.
Next useful evidence is target-handle hit/owner/HP/death progression on both
clients during the same reported kill, including native owner simulation
activity when separated. Do not substitute repeated Kill, forced HP0 or model
hiding for diagnosis. Earlier05.11 historical-arrival ghosts are a different
scenario and do not establish the cause of this live-combat report.
