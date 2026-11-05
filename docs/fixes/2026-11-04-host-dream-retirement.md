# Host Dream travel: premature Party retirement — 04.11.2026

Status: SOURCE ONLY; not built, installed or confirmed in game. BBSC HEAD and
parent gitlink both remain 0ddb1d4. Existing unrelated local changes retained.

## Latest run evidence

Collected the three current PC profile game logs, plus the three Party event
journals, into parent out/coop-dev/runs/host-dream-20261104. Game logs span the
13:40 launch; collection at 14:06:51–53 MSK reports all three game files changed
during copying, so this is a live snapshot, not a final stopped-run capture.
Detailed native mod/timeline logs for this run are absent.

At 13:58:02.069 MSK LocalPlayer1 emits native_retired reason=host_empty,
generation27. Revision262 clears owner and room on all three peers within156ms.
The preceding revision261 still has LocalPlayer3 joined. A new generation28
is acquired at13:58:14 and both guests join again. At14:04:45–46 a distinct
explicit host LeaveRoom/closing sequence ends generation28. These two endings
must not be conflated. Exact teleport start/map/load phase is not recorded.

## Cause and fix

The newly installed automatic retirement path authorized an irreversible terminal
certificate from one ready/alive/self-only native snapshot. Lamp departure can
briefly satisfy this before the loading byte rises or native role recovers.
The service then destroys the room and prevents normal scoped follow traffic.
A real three-process/native HTTP regression reproduces room destruction using
the previous decision path; no actual game or saves are used in that fixture.

Automatic retirement now requires three seconds of continuous fresh terminal
observations for the same owner/generation/room and reason. A stale frame,
reporting gap >=1.5s, loading, death, unknown/renewed membership or restored bell
resets confirmation. Unsafe reports reset it immediately even between monitor
passes. A single sample cannot age into proof of termination during suspended
frames. DLL loading additionally includes pending world construction, native
reload-finish and the mod curtain, so the first construction tick is protected
before TickBbscLoadState consumes those markers.

Explicit Blank/menu drain remains unchanged; host-crash still requires native
teardown plus missing authenticated host control. Durable scope/replay fencing
and follow packets/placement are unchanged. Automatic recovery gains a3s
confirmation delay; it does not infer success from missing actors.

## Validation

- Previous decision path: new three-process Dream departure regression FAILS
  as expected with owner=None and room destroyed after the transient snapshot.
- Fixed static three-player and dynamic two-player Dream-load fixtures PASS:
  pre-load self-only snapshot, loading, suspended frames, arrival role recovery;
  exact owner/generation/room/guest records remain identical on every peer.
- All12 native-retirement cases passed across the targeted runs: the initial
  suite had11 PASS and a partial-commit fixture timeout. Its command lifetime
  was2s, shorter than the new3s confirmation; changed to8s to keep the intended
  operation outstanding. The corrected partial-commit case passed independently.
  Coverage includes real termination, dead host/guest, stale/unknown/load/death/
  bell guards, scope and late replay. No full suite repeated after this test-only
  timing adjustment.
- Production native tick fixture PASS: disabled mode performs no game reads;
  pending construction, reload-finish and curtain each report loading.
- Scoped follow arrival fixture PASS.
- Production menu quit fixture PASS; native closed-room/recreation/late-leave
  compatibility test PASS.
- Complete BBSC_MOD bloodborne_re.cpp syntax check PASS (/Zs, no DLL generated).

No product build/deploy, game launch/termination, real save/settings/live-journal
edits, game-file writes, commit/pin/push. Gameplay confirmation remains OPEN.
