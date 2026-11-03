# Local Party protocol

## Current integration — 04.11.2026

Party is the mainline BBGL co-op path, started inside run.py from BB_PARTY_CONFIG.
The loopback compatibility API serves native NP/game requests; authenticated
peer control and native UDP gameplay remain separate. No external shadnet.exe,
gameserver.exe or VPS is required for this path. Offline / Co-op are launch modes.
Launcher discovery uses UDP announcements and TCP mesh checks; the replicated
engine below uses explicit unicast peers. The no-broadcast statement below
applies to the engine, not launcher discovery.

The original isolated experiment and baseline are historical; see the parent
repository docs/experiments/serverless-party.md and docs/P2P-HANDOFF.md.

## Identities and transport

The optional member `name` is the native NP online ID shown by the game (1–16
ASCII letters, digits, hyphen or underscore; launcher names require at least3).
Names must be unique, ignoring case. Invitations without names retain their
previous native IDs. The compatibility boundary translates names to stable
member IDs for control/signaling requests and back for native responses/events.
Account IDs, game UserIds and durable journals remain keyed by stable member ID.
Launcher discovery preserves chosen names in the agreed configuration/digest;
renaming does not change the group or secret and takes effect on the next launch.

An invitation contains a random group ID, epoch, secret, ordered immutable roster,
and explicit unicast IPv4 endpoints. Each member has a stable ID/account ID and
independent profile. TCP connection incarnation, proposal revision, native room ID,
and game-world owner are distinct. There is no broadcast/multicast. TCP is chosen
for bounded authenticated control and opaque BBSC commands, not for native game
packets: those keep their existing P2P UDP framing and Bloodborne semantics.
The existing VPN provides reachability and NAT traversal; this protocol does not.

The invitation is a capability: keep it private. HMAC-SHA256 authenticates group,
epoch, sender and entire envelope; the source IP must match the configured member.
The model assumes honest invited members, not Byzantine members sharing secrets.
Malformed/oversized inputs are rejected. Local compatibility APIs bind loopback.

## State machine (defined before implementation)

Replicated state: revision, roster, epoch, generation, owner (or null), room,
joined members, pending admissions, and per-member completed request sequence.
Local durable state: current state, accepted proposal, final revision and outgoing
request counter. A missing journal in an already used invitation is not recovery:
restore the profile or create a fresh group while all games are closed.

Each revision has one deterministic temporary coordinator: roster[revision % N].
The coordinator is unrelated to the native world owner and rotates after commits.
No local timeout changes the coordinator, membership or owner.

1. IDLE: everyone in own world; acquire(member) may be requested by actual bell use.
2. PREPARE: coordinator serializes one request against exact current revision;
   every member validates the transition and durably accepts the identical proposal.
3. COMMIT: only after all PREPARED replies; everyone persists the next state.
4. FINAL: only after all COMMITTED replies; coordinator disseminates finality.
   The requester may consume the bell / create a native room only after FINAL.
5. RESERVED: owner is locked while beckoning, admitting, joining or playing.
   admission is replicated before its native join; completion retires pending join.
6. RELEASE: only the owner may request it, after its native create/search has been
   fenced and the room, guests and pending admissions have explicitly drained.
   Cancellation without guests uses the same unanimous transaction. Map loads,
   death, TCP EOF and heartbeat loss never release anything.
7. RECOVERY: accepted/committed work is retransmitted from journal; repeated IDs
   are not re-executed. Older revisions/epochs and late FINAL replies are ignored.
   Crashed active owner stays locked until recovery and explicit native teardown.

If a coordinator crashes midway, progress waits for that member to restart.
Availability is deliberately sacrificed to prohibit two worlds during partitions.
There are no leases and no timeout-based failover. Live-world migration is absent.

Membership change is allowed only while idle, by the same unanimous transaction
of the old roster. First-stage removal supports a subset of existing members;
adding members uses a new one-time invitation after all clients close the old group.
An unavailable member cannot be removed unilaterally. A removed member's old
revision/epoch cannot get all confirmations and cannot acquire a world.

## Compatibility mapping

- Accounts: stable IDs from invitation; loopback shadNet login only accepts own ID.
  No external registration/email/password service is contacted.
- Matching2: local protocol codec retains protobuf response shapes, native callback
  IDs, slot membership and peer endpoints; mutations go through the party log.
- Signaling/STUN: VPN addresses + per-client P2P ports; existing signaling remains.
- Summon broker: per-group advertisements, one owner, idempotent claims tied to
  generation; stock JSON create/get/request/delete responses and placement headers.
- BBSC relay: loopback framed adapter routes opaque existing envelopes only within
  current group/generation, with ACK IDs and bounded queues/deduplication. Frequent
  state has bounded backlog; overload fails the local channel rather than replaying
  arbitrarily old commands. Native gameplay UDP payloads are never rewritten.
- Online messages/ghosts: well-formed empty list replies; public social services,
  account recovery and public matchmaking are outside this private experiment.

## Evidence boundaries

Protocol tests, adapter tests, successful builds and gameplay are different claims.
Two LAN devices do not prove cross-provider NAT/VPN behavior. Game confirmation
must include concurrent bells, cancellation, guest join/leave, host alternation and
recovery on isolated profiles. Never run games automatically for this experiment.

## Implementation notes after targeted verification

Explicit cancellation uses a monotonic native cancel counter (Blank, ringing bell,
search cancellation, confirmed menu quit). Idle/death/loading alone do not release.
A current native process has an exclusive Windows identity mutex; transport bind
is also exclusive. Startup recovery may acknowledge quiescence of a prior native
incarnation only after a fresh report from the new exclusive game process.
Native kick retains a departing-member barrier until explicit leave/idle recovery.
Source-IP bind pins outgoing control traffic to the invitation's interface.
Request results retain a bounded 32-entry per-member cache so overlapping completion
observers cannot lose an earlier ACK. Matching2 messages use native callback shapes.

First-stage ACK is transport ingress, not a transaction with the native game. A
receiver crash between receipt and application may lose the application; reconnect
requires ordinary BBSC state resynchronization. Exactly-once game effects across
crashes are not claimed. No WorldFlags chunk is coalesced by message type.

The prepared two-device run uses LAN addresses. The same explicit endpoint format
accepts VPN IPv4 addresses, but cross-provider VPN reachability/NAT fallback and
native gameplay remain unverified. First-stage private ancillary APIs return empty
social lists and do not implement the chalice catalog.

## Bounded I/O revision (03.11.2026)

Control decisions remain unanimous and durable. Filesystem operations run in a
bounded writer outside Engine.lock; outgoing protocol replies wait for their
persistence ticket. Only the ticket containing the final revision gates native
role/title approval; unrelated later counter/ACK metadata cannot retract it.
Snapshots are cumulative, so queued writes to the same path may be coalesced.
Write errors never authorize a decision. Network sends use bounded independent
per-peer workers with control priority and duplicate queued-frame suppression.

BBSC relay uses16 outstanding frames per recipient, with per-recipient sequences
and stream identity(process incarnation, transport generation). A replacement
native connection or world generation starts a new stream. Receiver buffers at
most16 out-of-order frames per sender, delivers contiguous frames individually,
and cumulatively ACKs only a durable contiguous ingress watermark. Parts are
never merged by message type. Per-peer retransmit timeout follows RTT with
backoff, rather than resending every80ms on a healthy higher-latency path.
Backlogs and10s expiry remain bounded; expiry never releases world ownership.

Receipt watermarks live in party-relay-journal.json, separate from control state.
Old receipt fields are migrated durably before rewriting party-journal.json.
ACK still means durable ingress, not native application: the documented crash
window between receiving and applying an effect remains. Updating all party
clients together is required for the new window/stream wire format.

A separate event-driven relay dispatcher cannot be blocked by the lifecycle
monitor's group operations. Lifecycle commands are polled asynchronously and
confirmed state is copied only on revision change. Native bridge uses one
pooled HTTP/1.1 tick RPC; title confirmation is requested only for an awaiting
current exit ticket. The native title transition still requires final group
leave and never accepts a timeout or an earlier ticket's ACK.
