# Join failure: launcher embedded network review — 2026-11-02

Read-only code investigation; no runtime changes or build.

## Actual path

launcher/bbport_coop.py:698 removes alternate THD backend settings and sets
BB_ONLINE, BB_COOP and the shadNet endpoints. gpu/CMakeLists.txt:184-226 compiles
BBSC-derived NP signaling/matching, shadPS4 socket/P2P code and THD code into
bbnet, linked into bbgpu. This is the active network emulation in the port;
it is not merely the launcher UI and is distinct from the mod DLL.

Signaling ActivateConnection -> asynchronous peer resolution/activation ->
Offer/Accept/Check/CheckAck -> EstablishConnection -> game callback.
Native game negotiation uses datagrams on vport 40. Matching2 JoinRoom is a
subsequent game request, not an automatic effect of signaling ESTABLISHED.

## Evidence and limits

Run snapshot ../coop-diagnostics/join-20261102-0603, connection 22090:
Both signaling readiness callbacks are delivered; both sides still report ACTIVE
at native close. Old activation-race PENDING regression is not reproduced here.
Host sent a 255-byte packet hash a25d2d80ad646bda; laptop transport queued and
read the same hash. Exchanges in the reverse direction also match. No observed
transport auth/digest/queue errors. Guest invokes native task-13 close first;
peer closure on host follows. Thus no proof of an emulator timer killing this
attempt. A native caller can still reject data/status supplied by emulation.

DatagramSocket::RecvFrom records diagnostic D using the original packet payload,
although it copies min(buffer size, payload size) bytes. Therefore matching D
hashes do NOT prove the game received the entire datagram. Current snapshots
lack receive capacity/returned count and packet contents. net.cpp also applies
FilterTalkEvents after dequeue diagnostics. No filter activation is logged in
these snapshots; interference is not established.

## Concrete code risks, not confirmed causes

HandleControlPacket and HandleHandshakePacket select connections primarily by
online name. Established and Close control messages do not validate from/to
connection generation before changing readiness or dispatching PEER_DEACTIVATED.
A delayed control packet from a prior attempt could affect a newer one. Current
trace does not show an incoming Close preceding the first client-side failure.
Do not label this the proven cause or fix it as if the run demonstrated it.

Next useful evidence is native task-13 failure branch/result source, together
with per-call receive capacity/result and current connection generation. Merely
changing signaling retries, forcing ACTIVE, or suppressing Deactivate would hide
native failure rather than establish a correct room join.