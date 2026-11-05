# Late-join initial placement ordering — 04.11.2026

Status: targeted tests PASS; DLL built and six-file bridge/DLL delta installed
on PC and laptop (exit0 each) on 04.11.2026. Gameplay remains unconfirmed.
See parent out/coop-dev/runs/join-fix-deploy-20261104/run.md for backups and inputs.

## Evidence and cause

Read-only logs copied to parent `out/coop-dev/runs/join-teleport-20261104/`.
PC twin claims laptop test at 11:35:45.956 MSK, with host placement
`1,18010000,c33f16c9,c24a6a5f,43158c4c,3da56540,-241000`.
Native signaling establishes on both machines at 11:35:46.540–46.715.
Another claim appears at 11:39:23.395; PC reports a multiplayer error at 11:39:58.
Detailed mod/transport diagnostics were disabled: these logs establish the claim
and connection, not the guest's exact session state or final position.

Production SendRequest sends RelaySendAimedPlacement BEFORE original_send submits
the HTTP claim. DynamicEngine.relay only forwards to the current world roster;
an unbound discovered guest is outside that roster until admission commits.
The early placement therefore has no recipient. OnAimedHostPlacement would have
identified the host for scoped follow/world flags and set connect-first placement.
Without it, signaling success alone cannot place the guest. This is a reproducible
source defect consistent with the reported run; its exact in-game chronology is
not available in the release log.

## Change

The dynamic bridge holds native aimed-placement frames for up to 90 seconds.
The HTTP placement header is retained as private admission metadata. Only a
confirmed host admission with matching target and placement may flush the frame,
and only to that pending guest. The ordinary relay membership fence stays intact.
Incoming placement is associated with the current owner and admission ticket.
Native claim delivery waits for that placement and a connected native relay.

A TCP write does not prove native processing. After accepting an aimed placement,
the DLL includes `X-BBSC-Aimed-Placement` on its next native sign publication.
The bridge requires this exact acknowledgment before exposing the claim, then
removes its private metadata from the game response. Wrong/stale ticket or
placement cannot authorize delivery. Existing native target/role validation and
90-second expiry also govern the acknowledgment. Legacy static admission remains
on its existing path.

## Checks

- `python -B -m unittest test_join_placement -v`: 2 PASS; actual HTTP and native
  relay sockets, placement before/after claim, delayed delivery, missing native
  acknowledgment, mismatched placement/ticket, one flush per admission, clean
  native response, repeated polling.
- Direct dependencies: DynamicNativeProcesses.test_real_http_np_late_join_and_host_rotation
  and DynamicTests.test_relay_order_recipients_dedup_and_new_native_stream PASS.
- `python -B tools/test_summon_cleanup.py`: PASS; production native aimed handler
  rejects wrong target and joining role, acknowledges accepted placement only,
  expires old acknowledgment; existing nonblocking native sign lifecycle passes.
- `git diff --check` for this task's changed tracked files: PASS. A later
  repository-wide check encounters concurrent guest-lamp edits/line endings;
  those files are outside this task and were not reformatted.

Parent HEAD 1987812; BBSC HEAD and parent gitlink 0ddb1d4. Existing local late-join,
launcher and other-task edits retained. No commit, pin change, push, real save or
settings change. DLL/package build and installation deferred while the related
guest-lamp travel chat is active, per the shared-build barrier.

Gameplay check after a common deployment: guest starts separately, host rings
its sign from a different location, guest loads beside host; repeat with reversed
roles. Neither signaling ESTABLISHED nor these fixtures closes the gameplay bug.
