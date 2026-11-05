# New repeated-join placement failure — 04.11.2026

Status: SOURCE FIXED, targeted checks PASS. No product DLL build/deploy or gameplay
confirmation yet. This extends the earlier HTTP-only placement-order correction;
it is the newly reported17:17/17:26 regression, not a claim that an old bug stayed fixed.

## Evidence

Parent `out/coop-dev/runs/join-new-20261104/`: current PC logs collected with provenance;
files changed during collection, so snapshots are not final stopped-run evidence.
Laptop read over strict SSH/Tailscale with existing host key. Large raw SCP was
interrupted after572476648 bytes (partial prefix, through17:30); `laptop/filtered.log`
is a separate completed remote diagnostic-text extraction through17:30. Small Party
event journals copied separately from both participants. No save/profile metadata read.
PC startup16:59, laptop17:03; primary profiles twin/test.

-17:06 first admission: native aimed placement, host lock, destination handoff,
  guest join teleport17:06:29; subsequent Dream/Cathedral follow also works.
-17:10/17:13: NP JoinRoom completes without HTTP admission_delivered. No aimed placement;
  position-based fallback still finds host after loading and teleport eventually works.
-17:17:43 host claims ticket60/generation8; guest NP join changes revision61
  immediately. Guest state4→6 at17:17:46.710, no aimed placement/host lock/teleport
  before exit17:18:55. This is not an absent native connection.
-17:26:52 host claims in Forbidden Woods0x1b000000 (generation9). Guest joins,
  enters state6 at17:26:55.574 but loads its old Cathedral Ward0x18000000,
  reports no host world flags17:27:02, exits17:28:46 without placement.
-17:29:58 next admission DOES use HTTP acknowledgment and aimed handoff;
  Dream destination loads and join teleport succeeds17:30:09. This later success
  does not invalidate the two preceding failures.

## Corrections

1. Direct NP JoinRoom now waits before consuming pending for the same placement
   acknowledgment as HTTP. DLL maintenance publishes accepted `aimed_placement` in
   `/party/tick`, independent of sign/create polling. Current native relay receipt,
   host/generation/ticket and room must match; closed/replaced admissions fail.
   Eight-second bound, worker-side only, no new network calls from the game tick.
2. Native aimed handler accepts joining state4 (before the NP room is committed and
   summon handoff occurs), still denies established host3/guest6. Dynamic relay
   drops foreign-owner, wrong-placement and nonpending aimed frames before native
   delivery. Acknowledgment expires independently of HTTP sign publication.
3. New local world generation resets outgoing relay stream and sequence. Receipts
   were already keyed by world; old sequence>1 in a fresh world left seq1 missing,
   so delivery never progressed. Native sockets remain open. This second defect is
   reproduced in isolation across two worlds with24 ordered frames each; release
   logs do not contain live seq watermarks to prove every lost packet's cause.

No direct character-coordinate fallback, extra load, fabricated claim/actor,
role promotion, real-save or game-data mutation was introduced.

## Validation

- `python -B -m unittest test_join_placement -v`: initial before/after ordering
  checks passed; repeated-direct-join fixture passed after adding stream reset.
  First versions exposed both missing direct admission gate and carried sequences;
  final repeated-join case passes for two worlds with persistent native sockets,
  delayed placement, wrong acknowledgment and no further sign/create request.
- `test_dynamic.DynamicTests.test_new_world_relay_restarts_without_reconnecting_native` PASS.
- Existing `DynamicNativeProcesses.test_real_http_np_late_join_and_host_rotation`
  and `DynamicTests.test_relay_order_recipients_dedup_and_new_native_stream` PASS
  after the implementation changes.
- Production C++ `tools/test_summon_cleanup.py` PASS: state4 acknowledgment,
  established-role rejection, expiry without HTTP traffic, existing async lifecycle.
- `tools/test_party_population.py` PASS: actual worker JSON includes acknowledgment.
- MSVC-target `/Zs` of bbsc_http.cpp and bbsc_party.cpp exit0. Preliminary libc++
  invocation could not compile the existing MSVC-specific wide-string ifstream;
  corrected to the actual build toolchain; no source workaround was added.

Shared-build barrier still has the PvP task active. No DLL build/install or game
restart in this task. Delivery requires DLL and both Party Python files together.
HEAD and gitlink0ddb1d4; parent4483863, pre-existing work retained; no commit/push.
