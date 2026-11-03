# Connection failure and original BBSC network audit вЂ” 03 November 2026

## Evidence and current limit

Latest run: 01:35вЂ“01:39 MSK, captured under
`bloodborne_pc/out/coop-dev/runs/review-20261103-0140/pc`, six stable files,
no collection warnings. P1/test1 host, P3/user3 attempted guest. P2 was also
collected; no P2 claim or JoinRoom is present in this attempt. Actual native
transport ports are now P1 3658, P2 3659, P3 3660.

P3 claim reaches the mod at 01:37:47.498. Signaling is ESTABLISHED and game
vport40 packets flow. At 01:37:56.358 the game's outer negotiation reports
phase11, remaining wait -0.01145s, task phase12/result0, channel and exchange
present, ready=false/accepted=false. It initiates cancellation; the later
signaling close is a consequence. P3 never calls JoinRoom. Claim expires at
01:38:07.939. Host subsequently times out its empty room at 01:38:41.344.
This is not a targeted-kick event or an authentication failure.

Correlated decoded-payload hashes leave four sends without matching receiver
samples: one of two host 17-byte sends, host 26-byte send, one of two guest
17-byte sends, guest 54-byte send. Existing samples omit destination endpoint
and pre-codec bytes. They cannot distinguish a wrong recipient, codec handling,
local send failure, or actual WAN loss; do not describe WAN loss as proven.
No vport40 full/wrong-peer/codec rejection is recorded.

## Original 0.0.1 versus 0.0.2

Compared the actual local upstream release tags:
- v0.0.1: `315f76c38b1ca5843b082f93f47927a9193ad94a`.
- v0.0.2: `4f11faf88b6ba658ebde6fe5fbefdadedba4fa41`.

Both already contain emulator source and BBport mod packages. Version0.0.2 did
not first introduce an emulator. The major import into BBGL was a change from
its shadPS4-0.20 implementation to BBSC's NP code (BBGL commit0a5167e), a
separate comparison from upstream v0.0.1 versus v0.0.2.

| Component | Difference between upstream tags | Decision for BBGL |
| --- | --- | --- |
| np_matching2 directory | Identical, no source differences | No evidence for reverting it to solve this failure |
| np_signaling.cpp | Identical | The base activation/status API is already the v0.0.1 algorithm |
| np_signaling_state.cpp | Adds timeline calls only | No v0.0.2 handshake algorithm to undo here |
| Signaling helpers | Adds PvP/progress/boss payloads, emulator-to-mod relay interoperability | Game-mod handlers remain responsible in BBGL; avoid duplicate application in emulator |
| p2p_sockets.cpp relay | Relay from first frame; preserve all endpoints as aliases keyed by online ID | Retain: these fix delayed activation and one-way relay behind NAT/CGNAT |
| HTTP claim handling | Placement on /request only; targeted placement by TargetUserId, own-sign identity | Retain: v0.0.1 broad /get placement could reserve unrelated signs and select the wrong host |
| Game-side policies | Spectator, progression, night state, rewards and more | Independent from NP activation; wholesale rollback loses working features |

A real difference remains between the original emulator's network backend and
BBGL: original BBSC uses a plain four-byte vport header; BBGL retains the modern
FramingCodec (communication ID, optional crypto/signatures, streams). Its
matching/signaling code is adapted on top. Both BBGL peers can exchange this
format, but it is not binary-compatible with an unmodified upstream emulator.
No wire-format switch is made on speculation in this revision. The Python UDP
relay forwards opaque frames and supports either format without translation.

## Reproduced adapter defect and correction

Original BBSC P2PSocket::ReceivePacket supports MSG_PEEKLEN: return the full
queued datagram length, optionally copy a prefix, and keep the datagram queued.
BBGL translated it to ordinary PEEK, returning min(buffer capacity, packet
length). With no buffer and capacity0, it returned0 even when data was queued.

Restored the original contract through sceNetRecvfrom -> P2PSocketRecvFrom ->
DatagramSocket::RecvFrom. Plain PEEK and consuming/truncated receive keep their
existing behavior. Null-buffer queries do not allocate scratch packet storage.
This defect is independently reproduced; its use by the failed native
negotiation has not yet been established. It must not be called the proven
cause of the 01:37 failure.

## New bounded diagnostics

Client decoded T/R/D samples retain hash and add the first four header bytes.
W samples hash encoded datagrams before relay wrapping; I samples hash the
encoded bytes after relay unwrapping, before codec rejection. They carry peer
endpoint, so an outgoing game command can be tied to its actual recipient.
Native syscall logs capture socket, length/capacity, flags, return value and
address (first256 per direction). Relay raw-send errors are no longer invisible
in logs (first16 errors); delivery/error semantics are not changed.

Server logs RX, TX and DROP, online IDs encoded safely as hex, encoded-frame
FNV-1a64, lengths, endpoint and send result/error (first2048 trace entries per
server process). No tokens, keys, account request bodies or packet bodies are
retained. Protocol, native deadlines, native packet acknowledgement and queue
limits are unchanged. No localhost shortcut remains; the user explicitly
requires testing through the server.

## Checks

- Production receive adapter (extracted unchanged function) plus real compiled
  guest backend/transport: null/short MSG_PEEKLEN, ordinary PEEK, subsequent full
  consumption and ordinary truncation PASS.
- Real transport fixture: 540 UDP deliveries/readiness/peek plus full-length
  query assertions PASS.
- Native sample hash/header/endpoint/logging fixture PASS.
- Production server forwarding, matching known FNV hash, source/target rejection,
  send errors, trace bound, forwarding after bound PASS.
- Standalone Python UDP probe through the live VPS:120/120 payloads delivered.
- Two independent compiled production BBGL transports through the live VPS:
  60/60 each direction; server120 RX and120 TX with identical hash multisets.
  Every flushed native W has a server RX, every flushed native I has a server
  TX. Native traces flush in batches, so end-of-test batches contain fewer than
  all120 received payloads; the application counters establish receipt.

Synthetic probes do not execute Bloodborne negotiation, callbacks or world
loading. They cannot close the gameplay defect or establish loss-free gameplay.
No game launched, saves/settings/firewall untouched.

## Deployment and next gameplay

VPS bbhost_service.py updated with backup
`/opt/bbsc/backups/connection-trace-20261103/bbhost_service.py`; Python compile
PASS, bbsc-gameserver active. Native shadNet unchanged. Fast package build exit0; final incremental native build exit0; staging probe
refreshed and PC deployment exit0,5219 files. Backup:
`D:/Games/Bloodborne/coop-dev/backups/connection-emulator-audit-20261103-20261103-020241`.
No games or launchers running at installation. The development staging probe
was refreshed after package creation; the ZIP is not this task’s deliverable. Existing dirty source changes
are preserved; this is not a clean commit-only release.

Next focused run: P1 host, ring P3 once and wait for world entry; then ring P2.
If entry fails, leave the games running for about10 seconds for diagnostic
batches, then exit and report completion. Record actual roles/actions; no save
restoration or local-network bypass is needed.

Sources: [v0.0.1 release](https://github.com/CLSAMG22/BBSC/releases/tag/v0.0.1),
[v0.0.2 release](https://github.com/CLSAMG22/BBSC/releases/tag/v0.0.2),
[upstream comparison](https://github.com/CLSAMG22/BBSC/compare/v0.0.1...v0.0.2).
