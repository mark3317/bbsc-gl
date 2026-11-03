# 2026-11-03 — rejoin-triggered capture and bounded TCP queue

## Scope and findings

User requested renewal on every real rejoin, investigation of TCP queue growth
(possibly after host death/respawn at a distant lamp), build and PC/VPS update.
Player3 CPU-overload automatic Stop remains excluded; GPU issue remains deferred.
GNS migration is separate; this change retains the existing stable transport.

Historical run has host respawn/map/lamp changes03:44–47, then TCP queue warning
03:49:39 (261530 bytes), with no logged connection loss and server errors0.
That chronology does not establish death/lamp as the cause. Existing queue log
reported only capacity, without age, writer progress or dispatch duration.
Existing blocking send timeout was per socket call rather than one absolute
frame/queue deadline; partial progress can extend it, and an old backlog could
remain indefinitely. No claim that this is proven root cause of the specific run.

## Diagnostic renewal

Added optional DLL export BbscNetworkAttemptSerial: atomic counter only, no game
memory or game locks on the native-port reader. Increment at the first delivered
claim (existing CAS guard prevents duplicate/chunked reply refresh). Native
transition to joining/guest is a fallback when no pending claim was observed;
repeated4/6 observations and unreadable manager during load do not refresh.
A normal load/death while guest state6 remains state6 does not become a new join.

Native P2P relay reads this optional serial before Route and on KeepAlive,
outside the relay mutex. A changed nonzero serial renews the independent90s
trace of all currently known peers (which also covers the still-present guest).
This works with the same cached signaling connection/connId and creates the
existing BBR1 diagnostic BEGIN/ACK windows on both clients and VPS. No new
protocol message, retransmitted gameplay, member rebind or game deadline change.
Legacy DLL without export retains existing NP-activation tracing. Polling an
unchanged serial cannot replenish the budget. W/I/R/D generation renewal remains.

## TCP behavior and diagnostics

Windows relay uses checked TCP_NODELAY and nonblocking I/O. recv waits via
WSAPoll; writer sends partial frames through the production RelayIo::SendFrame
loop. One10s wall-clock budget includes queued age plus all partial writes and
readiness waits. Exhausted budget shuts down that transport and lets its owning
reader perform existing cleanup/reconnect (2s delay); remaining stale bytes are
not replayed on the next TCP stream. Writer cannot consume the failed connection's
queue while teardown is pending. Existing server replacement/10s reconnect grace
and immediate explicit SessionLeave handling are retained. Queue cap remains256KiB.

SendFrame constructs the envelope/reads SessionKey outside send_mutex; fallback
P2P calls and full-queue logging also occur after unlocking. This removes callback/
logging dependencies from that critical section. No presumed lock deadlock claimed.

A5s independent observer reports queue bytes/frames/oldest age/high-water/drops,
sent frame/byte totals, readiness waits, in-flight bytes/send age/progress age,
last receive age and current Dispatch age. Even if a game callback blocks receive
processing during a load, the observer can expose it. Server RelayClient separately
tracks actual enqueue timestamps, in-flight batch, rx/tx totals/ages and high-water;
periodic per-client and close logs include connection identity and these stats.
Server forwarding bytes, FIFO batching, parties and backpressure limit unchanged.

## Validation

- Production lifecycle header + actual bounded send loop harness PASS: repeated
  cached joins, claim debounce, missing4 fallback, invalid manager/load, partial
  sends, permanent would-block, slow positive progress, native errors, readiness
  errors and old queue consuming the same deadline.
- Actual native Relay implementation harness PASS: changing mod serial refreshes
  expired/exhausted peer capture without a new signaling activation; duplicate
  poll does not; existing marker/ACK/error/expiry/filter cases preserved.
- Production backend departure fixtures11 PASS and queue diagnostics3 PASS:
  batched bytes/order/frame counts, timestamps, queue overflow, failure evidence.
- Real DLL ReadAll/SendFrame/WriterThread functions extracted and compiled against
  production RelayIo header, Winsock nonblocking sockets to77.73.67.175:20444:
  100 ordered2048-byte payloads PASS, no drops, high-water2065 bytes, waits0.
  Initial probe omitted production TCP_NODELAY and stalled after28 frames; it
  demonstrated the deadline firing, but configuration differed. A plain Python
  client sent/received100; final native probe includes production socket options.
  Do not attribute the game's earlier queue to that initial probe or claim a
  deterministic network/CPU/Nagle cause without matching-condition evidence.
- Real production UDP transport via VPS: DLL diagnostic-export adapter drives
  serial1 then2 on unchanged transports/peers. Two BEGIN windows,240 SOCKET_TX /
  240 VPS RX /240 VPS TX /240 SOCKET_RX, matching hash multiplicities, no gaps.
  Adapter tests the actual dynamic export bridge; lifecycle producer is separately
  tested production header. No game session or accounts modified.
  Logs: out/tests/rejoin-lifecycle-vps-20261103, correlation.json;
  out/test-relay-writer-vps-nodelay.log; initial failure log retained.
- Native sink/latency recorder regression PASS. Native build0; full fast package0;
  final bundled DLL rebuild0 (four existing warnings), final mod delta0.

## Deployment and remaining confirmation

PC8-file deploy0 at04:24:22MSK: bin/bb-probe.exe, three mod files, client bundle,
coop/SOURCE, BBSC-GameServer.exe and server bundle. Final staging contains the
last DLL delta; no extra full-package rebuild for the final guard adjustment.
Backup D:/Games/Bloodborne/coop-dev/backups/rejoin-trace-tcp-queue-20261103-20261103-042422.
VPS Python compile0, only bbsc_gameserver.py updated; backup
/opt/bbsc/backups/rejoin-queue-20261103/bbsc_gameserver.py. Only bbsc-gameserver
restarted; active. Persistent log gameserver-20261103-011615.log.
No game launched, no saves/profiles/settings/database/firewall/SSH modified;
no laptop, no commits/pin/push; existing dirty trees preserved.

Game confirmation pending: same-process guest leave/rejoin while another stays;
verify Network attempt trace serial and native P2P attempt lifecycle/BEGIN on
EVERY actual rejoin. Also reproduce host death + distant lamp respawn while
watching TCP queue, writer progress, Dispatch duration and server per-client
stats. Collect all3 profiles plus persistent VPS log+journal before more tests.
The historical queue's precise cause remains open; bounded recovery and enough
observability are installed rather than claiming the lamp hypothesis confirmed.
