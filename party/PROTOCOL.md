## Drained host search survives native room teardown — 04.11.2026

A fresh native0/2/5 with active Beckoning is not a terminal host event when
room/pending/joined are fully drained, no dynamic admission is staged and no
explicit cancellation is pending. Authority and advertised presence remain held;
new guests can join the same search. Explicit silence/expiry still releases.
Native recovery for occupied/stale rooms and death/loading guards is unchanged.
HTTP keep-alive reset/abort/broken-pipe ends that local socket quietly; unexpected
handler exceptions still reach server diagnostics.

## Consumed Small Bell search / return home — 04.11.2026

Successful JoinRoom withdraws the guest sign. Joined/consumed late create requests
cannot reactivate search; fresh native responder-off personal return followed by
a later responder-on permits a new manual search. Native role6 consumes effect9005
without Stop/Blank/PartyCancel. Cleanup waits through loading/death, and clears any
restored residual search once on return. After a completed guest visit, home return
and later personal loads do not auto-ring Small Bell. Fresh startup discovery and
explicit empty-host collision yielding retain their guest action; host detection
and availability continue independently of automatic bell use.

## Small Bell -> Beckoning acquisition fence — 04.11.2026

Successful local acquire withdraws the old responder sign and advertises reserved
host intent before native Beckoning is applied. Late create requests cannot
republish that sign during local ownership. Automatic responder release requires
that Beckoning was observed in the exact owner/generation/room scope AFTER this
acquisition; an old Small Bell snapshot cannot undo a new grant. Explicit cancel
still drains an empty grant when native application never succeeded. The game
thread erases9005 before replaying the granted native Beckoning item action.

## Network host choice / bell role switch — 04.11.2026

Dynamic authenticated presence optionally includes host={owner,generation,occupied}
separately from the masked responder sign. It requires fresh native evidence;
occupied worlds retain presence across loading. Consumers expire cached presence
after2s. Local-three fixed-roster mode keeps its previous behavior.

Optional /party/tick host_check (with bell_notice+bell_release) adds a fifth integer:
0 neutral,1 existing remote host,2 yield the local EMPTY competing search. Occupied
worlds never yield. An occupied remote host takes priority; concurrent empty
searches use stable identity order. A yield hint first fences room creation/claims
in the losing generation. The DLL cancels its native bell, waits for final release,
then invokes the original native responder item. Availability and acquire recheck
fresh host presence. No title/load/death/actor loss alone releases ownership.

Native observations include responder (actual9005 effect). A ready, alive, fresh
single-member native0/2/5 responder with no Beckoning can release an acquired but
never hosted empty search. Room/pending/joined/staged/attached state blocks it.
The ordinary durable release command retains admission serialization. The game
thread also checks for a host after each world load, allowing3s for discovery and
using native Small Resonant Bell once if ready and no manual search is active.

## Beckoning notices in dynamic worlds — 09.11.2026

The existing native item replay advances `bell_ring_seq` after each successful
Beckoning application. The loopback tick carries the counter to Party. The
authenticated `presence` response carries `[sequence, active, released]` in
`bell`, independently of the responder sign. A peer remembers the sequence per
host and Party incarnation, counts increases even before joining the room, and
offers only the current active ring on first discovery. Attached guests count
their own host's rings. An explicit durable world release can end the latest
notice. Missing presence never implies release.

The dynamic tick reply for DLLs that send `bell_ring_seq` and request all notice
and host fields adds a sixth integer `1`. Its third and fourth fields then carry
the local cumulative notice count and the count of the last confirmed release.
The DLL presents each pending ring when the banner can draw. Fixed rosters and
clients without this opt-in keep their previous world-generation fields.

Clients that send `roster_count` also receive the confirmed room population
in the same tick response. For this extension the preceding marker is 1 for
counted bell notices or 0 for legacy generations. Pending invitations do not
count. An explicit zero means no confirmed membership in a room, whereas an
omitted population leaves the last confirmed count intact.

## Explicit host-load follow metadata вЂ” 04.11.2026 (source only)

Follow0x20 kind1 keeps the34-byte position/lamp prefix, optional24-byte chalice
key, then a24-byte completed-load record: little-endian u32 generation, u32 map,
float x/y/z/heading. Size58bytes ordinary /82bytes chalice. The immutable last
native load arrival repeats until the next completed load; position/map updates
while walking do not replace it. Generation0 means no explicit completion.
Kind0 legacy formats remain readable; malformed kind/size/arrival is rejected.
DLL/native peers encode/decode this; Party forwards it unchanged. Both gameplay
peers need an updated build for reliable explicit arrival (especially chalices).
A fresh explicit load skips the2500ms border debounce, never guest5000ms reload
protection or world/dungeon readiness. See ../docs/fixes/2026-11-04-follow-delay.md.

# Local Party protocol

## Initial placement on reused native joins вЂ” 04.11.2026 (source only)

Dynamic admissions carrying `_bbsc_placement` require native acknowledgment before
both HTTP claim delivery and Matching2 JoinRoom consume the pending reservation.
A repeated native join can skip sign/create, so the independent DLL maintenance
worker includes its accepted `aimed_placement` in `/party/tick`. The acknowledgment
is checked against the current host, world generation, pending ticket and received
placement. JoinRoom waits at most eight seconds and rejects changed/closed scopes.
The DLL can accept aimed placement in joining state4, before room admission and
summon handoff; established hosts/guests remain protected. The dynamic receiver
forwards aimed frames only for the current owner's matching pending claim.

Every local acquire that advances the world generation resets outgoing relay
stream/sequences. Receipt keys include the world generation; carrying an old
sequence into a fresh key otherwise leaves a gap from seq1 and stalls delivery.
Native TCP sockets stay connected. This extends the earlier HTTP-only ordering
fix; DLL and Party must be updated together. Gameplay confirmation remains open.

## Native chalice channels вЂ” 04.11.2026 (source only)

Compatibility serves native `/channel/upload`, share, get_info, get_details_info,
word_search and search locally. Native FormData version0 is preserved byte-for-byte
after decoding; Party does not generate or replace root geometry. Root/general
search returns a typed empty result rather than selecting another saved layout.
Fixed story searches use the ten credited original story descriptions. Upload
assigns a positive JSON-exact channel ID and an eight-character glyph. An existing
ID is reused only for the same creator/character and unchanged decoded FormData;
a fresh ritual or changed layout receives a separate identity. Unknown saved IDs
never appear in LostChannelIdList. Failed persistence never acknowledges upload.

The launcher stores the catalogue at `<BBGL_PROFILE_DIR>/coop/party/chalices.json`,
outside ephemeral group directories. Writes use a process/thread lock and atomic
replacement; no character save or guest altar is installed by this service.
Glyph lookup is profile-local; this is not a distributed/public glyph directory.

Host-authoritative runtime mount/follow/world-flag transport remains unchanged.
Guests use its existing borrowed-loader bridge both for seamless follow and initial
summons to a host already inside a chalice. They do not need the host's catalogue
or a matching ritual on their own altar. Channel HTTP traffic does not reserve,
claim, join or retire worlds. The catalogue is never part of consensus/relay state.
Resource loading, rites and layer progression still require gameplay confirmation.

## Native-confirmed world retirement вЂ” 04.11.2026 (source only)

Supersedes the historical no-release-on-native-loss rule below only for these
confirmed terminal cases. A fresh native DLL observation includes the actual
session member count (self included), living local character, load flag, native
role and Beckoning effect. Unknown counts, dead characters, loading and a stale
frame sample never authorize retirement. Actor disappearance alone is insufficient.

Dream-travel regression guard (04.11): automatic retirement requires three seconds
of continuous fresh terminal observations for the same scope and reason. Loading,
death, unknown membership, restored membership/bell or an observation gap of1.5s
resets the window. The DLL's loading observation includes pending world construction,
reload-finish and the mod's curtain as well as the native loading byte. A suspended
load cannot turn a pre-load self-only snapshot into proof of session termination.
Explicit Blank/menu cancellation retains its existing drain path.

- An observed host with one native member and inactive Beckoning retires its
  ownership, room and stale pending/joined records. This works with native role3.
- An observed host that has stopped hosting (native0/2/5, one member, ready/alive)
  also retires, including a residual Beckoning effect. A recovered old owner
  journal/room is eligible after a fresh, settled native observation.
- A guest must have observed itself in this exact native room. After native
  teardown (0/2/5, one member, no Beckoning, ready/alive) AND loss of the former
  host control connection (no authenticated status for6s), it retires that binding.
  A control timeout alone, an ordinary kick from a live host, a guest death or
  another guest's crash cannot retire the host. The6s test is connection-loss
  confirmation, not a timer authorizing host migration.

DynamicEngine detaches the exact retired guest reservation locally and persists
its rejection; late views/reservations cannot reattach it. An empty/stopped host
persists a closed terminal snapshot, including any staged admission, for guests
that reconnect later. Native mutations serialize with retirement.

Static Engine persists an authenticated terminal certificate for the exact group,
owner, generation and room. It can supersede incomplete prepare/commit/final state
without the crashed member's vote; this is terminal revocation, never a new-owner
proposal. Peers deterministically prefer the highest certificate base revision,
then certificate digest. Certificates replay durably to restarted peers. Owned
proposals for retired generations are rejected; a certificate cannot reset a newer
generation or a different current room. A terminal snapshot is advertised only
after its durable write. The next static acquire still needs the full fixed roster;
normal dynamic launches can acquire independent home worlds without offline peers.

The compatibility bridge emits native room-destroyed on retirement. DLL and Party
must be updated together on all peers; older DLLs omit population/freshness and
therefore do not enable this automatic recovery. No live journal reset/migration.

## Recipient failure isolation вЂ” 04.11.2026 (source only)

An outgoing recipient's bounded backlog overflow, socket queue overflow or10s
ACK expiry fences only that recipient's stream. Other recipients keep ordered
delivery through the same native relay socket. `relay_peer_errors` reports these
fences separately from fatal local `relay_error`. A fenced stream is retired. In
dynamic worlds a successful existing authenticated presence reply can open one
fresh outgoing stream for that recipient, with the next frame at sequence one.
Another reopening requires a relay ACK on the new stream or a new admission.
Failure does not release membership or authority.
The rule applies to both static Engine and DynamicEngine. It does not claim game
handling of non-host native signaling DEAD is validated.

## Dynamic world sessions вЂ” 04.11.2026 (source only)

Regular launcher launches select `mode=dynamic-worlds-v1` and `DynamicEngine`.
The fixed-invitation consensus sections below apply to legacy/static invitations
and local-three tests; they no longer describe normal launch-time membership.

Every player has a stable home identity and a durable independent home journal.
A private-network directory is refreshed by launcher discovery BBGL-P2P-2 while
its game runs. Opening other launchers does not alter a home/session identifier.
An offline acquaintance cannot block acquiring a home world. Multiple unattached
players may independently host worlds; one guest cannot belong to two worlds.

A world has one permanent authority: its original host process/profile. It never
migrates on a timeout. State operations use the existing transition rules and a
monotonic per-member sequence with bounded result receipts. Guest commands are
fenced by the host's stable home ID and world generation. Independent native room
IDs use63 random bits to fence old callbacks even across different world owners.

Admission is a durable two-stage reservation:

1. Host stages the exact claim and identities in its home journal.
2. Guest atomically rejects another host/local acquire, or persists a provisional
   attachment. Repeated reservation IDs return the same answer.
3. Host commits the staged claim only after the guest's durable acknowledgement.
4. Guest fetches and persists the host's committed snapshot. On direct RPC
   failure, it may send a view request or the same sequenced command in its
   signed presence reply. The host answers on that socket using the normal
   authorization and receipt checks. Before confirmation, no native claim,
   role permission or native-state relay is authorized.
5. Native Matching2 join/leave and explicit cancellation keep their original
   admission, room-member, incarnation and draining checks. After confirmed leave
   the guest returns to its home without changing its login or loopback sockets.

Lost replies within one launch retry the same reservation/command. On dynamic
startup, Party replaces the journal with an empty session after binding its
exclusive endpoint. It retains only the stable identity and monotonic counters
needed to fence old requests. A surviving guest learns that its old world ended
through its existing authenticated view request. The host drops only a guest
whose newer process incarnation is authenticated, using the incarnation returned
by that guest's reservation. A staged invitation carries the guest incarnation
from its sign so a delayed request cannot reserve a newly launched guest.
Retired reservation IDs cannot reattach a drained guest within the same launch.
A JoinRoom placement timeout retires its exact unused admission. Explicit
native cancellation may also retire a provisional reservation. The host includes
the pending reservation ID in its presence request and releases only that
pending admission after the guest's authenticated withdrawal. A partition,
native transport EOF, loading, death or elapsed time never clears joined
membership or changes a world owner. Unrelated home worlds remain independent.
Release still requires explicit native intent and a drained room/pending/joined
set. A host retains bounded terminal snapshots for replies across world rotation.

RPC envelopes authenticate sender, nonce and body with an identity-pair HMAC and
check source IPv4. Directory seeds and endpoints use the same private-network
trust boundary as existing launcher discovery, not an Internet authentication
service. An active identity keeps its key, name and ports. An advertisement
for the same identity can update its IPv4 address. Unknown/malformed
identities and duplicate native names/endpoints are rejected. Legacy and dynamic
control protocols do not interoperate; upgrade all players together.

Native gameplay remains direct UDP. The BBSC state relay uses per-recipient
16-frame windows, ordered receive buffering, bounded queues, stream/session fences
and durable ingress receipts. An ACK does not prove native application: the same
receipt-to-game crash window documented below remains. The native DLL ABI and
loopback packet/HTTP shapes are unchanged. Neither legacy journals nor real saves
are automatically migrated, deleted or reset by this change.

Evidence: `python -B -m unittest test_dynamic.DynamicTests
 test_dynamic.DynamicNativeProcesses` (join into one shell line) exercises real
TCP/HTTP/NP/relay interfaces on temporary loopback profiles. Product build,
deployment and real game confirmation have not been performed.

## Current integration вЂ” 04.11.2026

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

The optional member `name` is the native NP online ID shown by the game (1вЂ“16
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
