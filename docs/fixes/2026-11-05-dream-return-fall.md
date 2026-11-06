# Unqueued Dream return — source fix, 05.11.2026

This follow-up supersedes the diagnosis-only source status below. Gameplay
confirmation is still OPEN; no DLL build, installation or restart in this task.

## Concrete cause and native evidence

The direct native return after a fresh cross-map summon is not necessarily
queued through QueueBbscWorldTravel (the incident explicitly logged queued=false).
The old BbscWorldNativeWarpBegin only armed actor admission. It did not set
travel_inflight or a destination scope for that path. Consequently the existing
BbscWorldBonfirePhase callback did not protect the return at the load-map branch.

Original1.09, verified read-only against out/exit-study.elf:

- EMEVD2003[49] calls013CDF30 with point in EDI.
- 013CDFAB writes the requested bonfire map to global+0C;
  013CDFFB writes bonfire spawn information to global+153C.
- Loader0192997A compares summon rules+84 to3. On equality01929987/8E
  reads global+14C4, the old summon map. Otherwise01929A8A/91 reads
  global+0C, the actual native request.

For a Dream return after joining a host in Central Yharnam, these maps are
m21_00 and m24_01 respectively. This explains how an accepted Dream request
can complete in m24_01 with a different bonfire selection. The incident logs
prove the wrong resident map and later death; they do not record native phase
registers, final coordinates or falling physics. The exact branch defect was
reproduced in an allocated executable fixture; do not mislabel those registers
as a live capture of the user's process.

## Correction

At the native bonfire entry, adopt an unqueued known ordinary bonfire into the
same scoped lifecycle already used by queued travel. Set the current world,
destination map, requested point and load generation before native teardown.
Discard stale altar context for that ordinary destination. The existing native
phase comparison guard now retains the actual requested map for this path too.
Arrival/cancellation use the existing lifecycle. The native event still owns
animation, waits, stage request and spawn. No synthesized second load or writes
to native summoned placement, save data or summon phase. Unknown destination,
initial joining and non-coop calls do not acquire a local trip. Queued chalice
requests keep their scoped ritual/mount path.

The guard logs a phase3 observation with selected map, summon map and point,
so the next gameplay run can confirm the actual live branch.

## Validation

`tools/test_world_dream_return_native.py`, BBSC_TEST_EBOOT=out/exit-study.elf:

- Production pre-fix callbacks FAIL at the wrong-map assertion (m24_01).
- Corrected production callbacks PASS, returning m21_00 for the same input.
- Executes original CMP/JNE and map-load instructions with only RIP operands
  and branch displacement relocated into fixture memory; original bytes and
  branch destination checked against1.09 ELF.
- Repeated native returns, duplicate hook calls, completion expiry, initial
  join/non-coop/disabled/unknown requests, host path and unchanged native memory
  pass. The existing production ESD/travel fixture also executes and passes.

Full BBSC_MOD syntax check exit0; documentation diff --check exit0.
No build/deploy/gameplay claim. Shared pre-existing source changes retained;
parent pin and BBSC HEAD unchanged. No commit includes unrelated work.

## Historical initial diagnosis

# Guest Dream return after cross-map join — diagnosis, 05.11.2026

Request: inspect logs for falling into the void and dying after joining a host
and requesting Hunter's Dream. No behavioral code change was requested/performed.

Evidence: parent `out/coop-dev/runs/dream-fall-20261105/pc/collection.json`;
`game-7/run_20261105_222014.log` (guest P1) and
`game-14/run_20261105_222015.log` (host P2). Both are live copies,
ChangedDuringCopy=true; collection warnings0. Ignore recorded pre-copy lengths
as final sizes: collection reads live files. Times below are MSK.

- 22:41:13.904 guest cross-map handoff writes host m24_01 placement.
- 22:41:14.082 guest reaches session6;22:41:24.574 enters m24_01;
  22:41:24.767 join teleport adjusts position onto the host.
- 22:42:26.078 native stage request point2102950 (Dream), selected0,
  queued=false; local phase becomes loading.
- 22:42:27.743 local phase becomes resident in m24_01 again, visit12.
  22:42:27.756 native world bootstrap also admits m24_01, load11.
  No AREA change to Dream occurs for that request.
- 22:43:05.585 PartyGhostDeath;22:43:09.126 death penalty640 echoes.
- 22:43:09.845 in-place reset unavailable;22:43:09.859 real reload.
- 22:43:12.366 actual AREA change to m21_00 (Dream), visit13;
  22:43:12.368 respawn2102950 ->2102961.

Host stays resident in m24_01; there is no departure/session teardown in the
incident interval. Guest later travels Dream -> Central Yharnam successfully
(arrival22:43:44.536). This is an in-game death, with subsequent gameplay,
not evidence of a process crash.

Confirmed: native Dream request produced a resident wrong-map load before the
reported death. Not recorded: falling trajectory, spawn coordinates after that
load, floor/collision residency and the exact native write selecting the wrong
map. Do not call any one source path a proven root cause.

Source caution: BbscWorldNativeWarpBegin logs map from optional
bbsc_world_requested_scope, default0. Thus the incident's map0 means absent
queued scope in this diagnostic; it does not establish a native map0 load.
Earlier unqueued returns at22:23:26/22:25:11/22:34:36 reached Dream normally.
Their logged map0x18010000 is retained scope, not the native Dream destination.
Investigate cross-map join placement / forced destination lifetime and native
return-load selection, comparing the failing load with those successful ones.

Source baseline: BBSC HEAD db9a6b9906337ded70bb77b2036e5c079439257f matches
parent pin; shared dirty working tree already contains unrelated source work.
This task only collects logs and adds diagnosis documentation. No build, deploy,
restart, inputs, save restoration, live-memory writes or game asset changes.
Gameplay bug remains OPEN.
