# Player3 crash and late restart — investigation, 04.11.2026

Status: OPEN, read-only runtime investigation. No product code, build/deploy,
restart, commit/pin/push, save/settings or live journal changes.

## Captured evidence (MSK)

Parent capture: `out/coop-dev/runs/player3-rejoin-20261104/`.
Four game logs including Player3 rotation; warnings=0. Player1 and current
Player3 logs changed during copying; this is a live snapshot, not a final run.
Three Party diagnostic event streams copied separately. Persistent Party state
was read in place, not copied or reset. HEAD and parent gitlink both0ddb1d4;
existing unrelated source changes retained.

- 13:40: three-profile run launched. All original game logs load overrides from
  group `b4d7d8092a74859d92036cb31d1935fc`.
- 14:08:26–14:08:41: Player1 acquires generation29, native room486539297;
  Player2 and Player3 admitted, finalized revision277 on all replicas.
- 14:13:27.705: Player3 `DeviceLost (submit)`, `WriteInvalid at0x0`;
  runner pid33256 exits23 at14:13:29.458. System nvlddmkm153 at14:13:26,
  Application WER LiveKernelEvent141 at14:13:37/54 match this crash.
- 14:14:49.546: Player1 native signaling declares Player3 DEAD/no answer.
- 14:15:13: Player3 launcher pid35112 starts; native starts14:15:45.
- 14:16:25.377: restarted Player3 loads overrides from DIFFERENT group
  `91662daf1b31b1321dab87ec07403f49`. Its journal is incarnation1, revision0,
  owner/room null, empty joined/pending, same three LocalPlayer identities.
  No new-group Party event stream (restart did not inherit diagnostic env).
- 14:17–14:19: restarted Player3 repeatedly posts summon_messenger/create,
  receives HTTP200/52-byte responses; no signaling ESTABLISHED or native join
  observed in the captured restart log. HTTP success does not prove admission.
- 14:17:31.074: Player2 also DeviceLost/WriteInvalid; runner pid360 exits23.
- 14:18:13: Player1 native_retired(host_stopped), generation29/revision278;
  owner/room cleared. This is after the restart, not proof the host was absent
  throughout the attempted return.

## Conclusion and limits

The restarted guest and still-running host demonstrably used different static
Party groups. Engine rejects control envelopes with a different group before
processing them, so this is a sufficient blocker ahead of admission/native join.
This is the legacy local-three fixed-roster route, not regular dynamic discovery.
The current local-three config on disk still names the original b4d7 group.
Both surviving launcher command lines use the same scripts/local_party.py and
the same absolute main-profile coop/local-test/config.json argument.

The origin of9166 is NOT established. Current source and frozen
bbport_local_test.configuration both reuse an existing validated config;
current installed Compatibility directly reads BB_PARTY_CONFIG. Do not claim
that configuration() rotates the group on every restart, or that this proves
a stale-member admission bug. Capture the actual effective configuration at
launch (group/member/epoch/mode and path only; never its secret), reconcile it
with the original live host, and then test recovery within that exact group.
Do not clear live journals or generate a replacement group as a workaround.

Native crash diagnosis remains limited to observed GPU loss plus matching WER;
no GPU remediation undertaken. No tests run: investigation/documentation only.
Gameplay recovery is unconfirmed and the bug remains open.
