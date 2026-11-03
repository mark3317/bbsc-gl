# 16:23 local-three run: host Blank completion; PL1 negotiation remains open

Evidence: parent `out/coop-dev/runs/pl1-blank-20261103-review`.
Nine stable mod/native/bbnet files, collection warnings 0; all three party event
journals copied separately. Actual host is Player 3, successful guest Player 2,
failed guest Player 1. Native processes were already closed before collection.

## Observed sequence

- P3 acquires ownership at 16:25:03; creates its native room at 16:25:16.
- P2 receives a claim at 16:25:19.125, joins at 20.957, reaches state 6 at
  25.422 and two actors at 34.661. P2 uses Blank at 16:25:58.228; OnLeaveMagic
  runs at 59.082, native state 0 at 59.873, own-world load completes at 16:26:12.
- The previous cooldown correction is active: P3 defers the co-op role mask
  at 16:25:59.166, restores it at 16:26:01.324 and builds a request for P1.
- P1 receives that claim at 16:26:01.963. Signaling establishes, all recorded
  vport-40 encoded sends between P1 and P3 match incoming encoded hashes at
  the intended peer (approximately 0.04–0.15 ms). Decoded packets are consumed.
- P1 fails at 16:26:08.586: native phase 11, countdown -0.01257 s, signaling
  task phase 12/result 0, channel/exchange present, ready=false/accepted=false.
  No JoinRoom occurs. Claim is withdrawn at 16:26:22.210.
- P3 remains state 3 after its reported Blank/search cancellation, until its
  explicit menu exit at 16:26:58.549. Room retires at 59.054 UTC-correlated
  party revision 87, ownership releases at 59.971 revision 88. Earlier Blank
  effect/native-item logs are absent; neither their duration nor exact use time
  can be inferred from that absence.

## Host correction

Host Blank previously only watched SpEffect 7 and expected an autonomous native
room timeout. Host-specific Blank/search cancellation can bypass generic goods
execution and leave no observed SpEffect 7. Tick now also observes the runtime
Blank use state and the falling Beckoning search effect in a living, loaded
host. A local generic goods entry is additionally latched when available.

After a three-second grace, an explicit cancellation closes an empty host room
with native Stop followed by remote cleanup, silences remaining Beckoning and
notifies session leave. Host persistence patches remain enabled; no stage/title
request is made. The world/player table must be readable, nonempty and contain
only the local player or empty slots; an unreadable remote is not treated as
absence. Living remaining guests, loading, death and foreign worlds block this
completion. A search effect disappearing across loading/death is not cancellation.
Native idle then clears any remaining host load wait and the cancellation latch,
even when Lua's lock was already clear. Party ownership still waits for actual
native idle and unanimous final drain; no forced ACK/release/journal reset.

## PL1 boundary and additional observation

The previous lost-candidate correction now reaches a real claim. It does not
fix this later native application exchange failure. No UDP loss, identity
collision, capacity failure, or unique initiating protocol cause is established.
This revision does **not** claim that PL1 has been fixed.

A signature-checked observer at native exchange callback 01478130 records
exchange pointer, channel/subtype/length and protocol version tag; failure logs
the corresponding outer/channel/exchange pointers. It observes the callback
before native decoding without changing its registers, packet, readiness or
deadline. Metadata is bounded to 128 callbacks; no packet bodies/secrets are
retained. A new game attempt is required to distinguish missing native dispatch
from a different exchange/subtype reaching the callback.

## Checks and delivery

- `tools/test_blank_host_end.py`: production item latch and host tick/helper,
  executable-memory native Stop bridge; remaining/unreadable remote, unready
  world table, loading/death/foreign world, erase failure/retry, single Stop,
  idle release, later host, effect-only/runtime-item/search-end paths PASS.
- `tools/test_menu_quit.py`: production native save/title/final-group gate and
  Blank versus quit load-wait ownership PASS.
- `tools/test_negotiation_failure_trace.py`: production callback metadata and
  failure observers through exact native entry/mid-function trampolines PASS.

Build/deployment/startup and gameplay confirmation are recorded separately in
HANDOFF and the parent run directory. Saves/settings/game files are untouched.

## Additional reproduced native member-ID defect

The local compatibility allocator encoded `(incarnation << 4) | place` and
assigned owner ID 1. The actual packaged shadNet allocator (also exercised by
parent `tests/test_matching2_slot_allocator.cpp`) uses `(place << 4) | generation`:
initial owner/guests 17/34/51. The native place is `member_id >> 4`. With the
previous format, later rejoins can name places beyond room capacity, while
the advertised joined-slot mask was calculated from a different nibble.

New rooms now use the shadNet format, reuse the actual free place, and retain
the full monotonic incarnation separately in join_date. Thus low-nibble native
generation wrap cannot make a late callback current. Existing live legacy
rooms retain their identities and may drain; new admission requires a new
room. No persisted journal is rewritten/reset and idle groups need no migration.

The new production regression failed before the fix (owner 1 instead of 17),
then passed: five occupied places, 100 non-last departures/rejoins across
generation wrap, unchanged remaining identities, correct masks and unique
join dates. Three independent real socket clients receive 17/34/51 with mask 7.
Legacy drain, existing admission/rejoin and guest menu cancellation cases pass
(5 focused tests). This is a confirmed format defect; P1's recorded failure
precedes JoinRoom, so its causal contribution to that failed exchange is not
established. The party engine is embedded on the three clients; no VPS service
uses this private room allocator.

Additional three-process Blank/final-drain regression PASS: active guest plus
failed admission, host cancellation and real native API LeaveRoom, closing-room
maintenance cancels the idle failed admission; state 7 retains ownership, state
0 permits final drain, then another member's actual acquire succeeds. No timeout
release or title-intent bypass is used in this test.
