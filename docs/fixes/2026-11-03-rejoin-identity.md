# Rejoin identities and stale Matching2 members — 03 November 2026

## What the last run establishes

Evidence remains `bloodborne_pc/out/coop-dev/runs/review-20261103-0218`.
Native sends reject at01789742 before deferred fallback, later Stop01789812.
The log did not capture the rejected native member's room/member fields, so
it cannot identify the actual recipient or prove one unique initiating cause.
This revision fixes a separately reproduced mechanism that can create stale
native recipients after rejoin; gameplay confirmation remains pending.

## Server places versus native identities

The packaged shadNet Room::allocMemberId scans all occupied slots before choosing
a free one. MemberID encodes `(slot<<4)|generation`. A free place can legitimately
move from one client to another; simultaneous ownership is the defect to avoid.
Actual VPS join records:

| Room | Client | memberID | Server slot |
| --- | --- | --- | --- |
| 13 | P2/user2 | 34 | 2 |
| 13 | P3/user3 | 51 then52 after rejoin | 3 |
| 14 | P2/user2 | 34 | 2 |
| 15 | P3/user3 | 34 | 2 |
| 15 | P2/user2 | 51 | 3 |
| 15 | P3/user3 | 36 then38 after rejoins | 2 |
| 15 | P2/user2 | 53 after rejoin | 3 |

Reuse of34 in different rooms is normal. No simultaneous server slot collision
is established. The real packaged allocator was compiled and exercised in memory:
non-last departure plus100 alternating rejoins, including generation wrap,
never changes the host/remaining guest's ownership or duplicates active slots.
This does not inspect live native character-slot assignments in retrospect.

## Reproduced emulator defect

HandleMatching2HandshakePacket formerly accepted a packet when the context's
room/self matched and topology allowed the peer. It did not require the sender's
full memberID to exist in the server roster, or require its online ID to match
that roster identity. It indexed ctx.peers[memberID] before validating packet
kind. A late Check after MEMBER_LEFT could therefore recreate the departed
PeerInfo and call MarkMatching2PeerActive, which also lacked roster validation,
and enqueue ESTABLISHED for the retired member. Meanwhile the same server slot
could already belong to another member generation.

A production-function fixture reproduces the baseline: member34 leaves slot2,
member36 occupies slot2, an old Check34 creates an active ghost34 beside it.
The corrected code drops it before peer-table mutation, sending or callback.
The roster remains the authority for identities; no new local connection path,
wire format, server allocation policy or transport timeout is introduced.

## Callback lifetime correction

Pending signaling events now capture local memberID and peer join date in
addition to room/memberID. Before calling game code, verify current room/self
and peer incarnation. ESTABLISHED requires a current roster entry; genuine
DEAD after removal remains deliverable in the same incarnation. Old DEAD cannot
evict a new incarnation reusing the same fullID after generation wrap.

Room-event dispatch also checks room/self, and queued MEMBER_JOINED (both API
variants) checks current membership/join date. This prevents an old queued JOIN
from recreating a retired native member even if its signaling event is rejected.
Normal room-event producers and the existing experimental replay producer stamp
the same fields. Request completions, context/lobby events and genuine kick
payload translation remain unchanged.

## Native diagnostics for final attribution

The pre-defer observer now logs target_room/target_member and self_room/
self_member after validating the native member vtable052C5C00. The normal
once-per-second session watchdog emits the changed task/slot shape with native
room/member IDs. Thus the next failure, if any, can identify a self-target,
a retired-room member, or two task identities mapped to the same character
slot. This revision does not guess or overwrite a player's identity, delete
queued packets, suppress native Stop or raise the1001 bound.

## Validation

- `tests/test_matching2_rejoin_identity.py --baseline`: reproduced old ghost
  resurrection with original production functions.
- Current production handshake/admission/queue and dispatch branches, actual
  ContextObject/RoomCache/PendingEvent types: PASS. Covers valid Check,
  retired Check, wrong online ID, malformed kind, reused slot, unaffected host
  and remaining guest, delayed old-room/self/member callbacks, generation wrap,
  genuine DEAD, retired/current JOIN and JOIN_A.
- `tests/test_matching2_slot_allocator.cpp`: actual Qt server allocator PASS,
 100 alternating rejoins and active-slot uniqueness.
- Native observer exact mid-function trampoline, preservation of flags,
  throttling and new member fields: PASS.
- `tools/test_member_binding.py`: local binding/reinsert/watchdog checks PASS.
- Existing native KICKEDOUT presence/target/lifetime fixture PASS.
- Changed-source whitespace checks PASS. No unrelated broad test suite.

## Build and installation

Native incremental build exit0; bundled DLL build exit0, four existing warnings.
Existing staging updated using mod delta plus stripped native probe. Six-file
PC deployment exit0 at02:35:53 MSK. Backup:
`D:/Games/Bloodborne/coop-dev/backups/rejoin-identity-20261103-20261103-023553`.
No running game/launcher at install, no process stopped, no game launched,
no save/settings/firewall changes. No server/wire change: VPS update unnecessary.
Previous independent working-tree changes preserved; build atop BBGL572e066 /
bundled151e24c. No broad commit, pin change or push. The mod-only delta ZIP does
not include the updated native probe and is not a distributable full update.

Gameplay remains PENDING; automatic disconnect is not declared closed by fixtures.
Next run: P1 host, P2/P3 join. Keep P3 in the session, kick P2 with the host's
Blank and rejoin P2, wait60s; repeat once, then swap guests. Neither remaining
player should disconnect, and old-room/member callbacks must not create peers
or player tasks. If failure repeats, keep10s for diagnostics then exit normally.
