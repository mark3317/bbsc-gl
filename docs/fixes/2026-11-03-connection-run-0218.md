# Connection run review — 03 November 2026, 02:05–02:17 MSK

Evidence: `bloodborne_pc/out/coop-dev/runs/review-20261103-0218`, six stable
local files, warnings0/ChangedDuringCopy false, plus both VPS service journals
23:04–23:19 UTC. All profiles use BBSC1.1.0 built01:58:23, PIDs23800/24180/34012.
Actual BB_USER_DIR is each numbered profile's user directory. P1/test1 host,
P2/user2 and P3/user3 guests. This review changes documentation only.

## Entry succeeds; prior failure is not reproduced

P2 enters native guest state6 at02:07:38.937 and appears in host world at
02:07:46.943; P3 enters state6 at02:07:50.838 and the host sees all3 at
02:07:59.051. No Native negotiation failure event is present. Further joins
also reach state6. This confirms entry in this run, not a permanent fix or
causality for MSG_PEEKLEN. The first256 logged native receives on each client
all have flags0; no PEEKLEN invocation is recorded in that bounded sample.

P3's02:09:36 departure is confirmed native-menu exit, followed by successful
rejoin at02:10:13.762/state6. It is not an unexplained disconnect.

## Addressed host kick path now executes promptly

Host requests P2 removal at02:12:18.193; P2 receives OnBeKickOut and native Stop
from0x178c11d at02:12:18.347 (154ms). Host requests P3 removal at02:12:32.826;
P3 reacts at02:12:32.925 (99ms). Both clear4047, release leave locks and log
'host kicked you'; VPS confirms each addressed Room13 kick. Native home-return
processing retains its5s delay. The previous23–37s wait for queue overflow is
not repeated for these kicks. Logs confirm notice calls, not the user's visual
perception of the messages.

## Separate automatic failures after repeat joins remain

| Client | Rejoin state6 | First recorded send rejection | Native queue Stop |
| --- | --- | --- | --- |
| P2 | 02:12:49.960 | 02:13:20.498, kind49/24 bytes | 02:13:29.485 |
| P3 | 02:13:46.399 | 02:14:14.120, kind49/24 bytes | 02:14:31.843 |
| P3 | 02:15:07.567 | 02:15:32.727, kind6/97 bytes | 02:15:47.694 |

All3 automatic Stops originate at0x1789812 (native deferred-send limit1001).
The new observer sees repeated rejection at0x1789742 before the deferred
fallback, while ordinary native UDP traffic continues. P2 repeatedly targets
0x11de5b41f0 across these rejoin episodes; P3 targets0x11de5b4630. This points
investigation toward native destination/channel/member lifecycle after rejoin;
it does not identify which player's logical target that pointer represents or
why the native send rejected it. Do not label this simply an ACK timeout or
prove stale routes solely by pointer reuse.

P2 also rejects kind49 from02:14:45.367, but its02:14:51.104 Stop is preceded by
explicit Silencing Blank at02:14:51.095; classify that departure as requested,
not another limit-triggered Stop. Final P2/P1 menu confirmations are02:16:56.881
and02:17:06.569; P3 stops with the host leaving at02:17:06.741 and confirms its
menu exit at02:17:13.442. Host empty-room Stops at02:12:43.477/02:13:41.903
follow guest departure, not initial connection failure.

## Transport evidence and limits

All clients' cumulative counters show tx_error/full/wrong_peer/codec invalid/
digest/no_key/auth0. Some vport30 packets arrive unbound after socket teardown
(P1 final1, P2 final35, P3 final416); this is not proof of a cause before Stop.
Vport40 unbound0. VPS periodic UDP/TCP send_errors0; no service interruption
is recorded. No local relay-send failure is logged.

Server per-packet trace has904 RX and904 TX with matching hash multisets and
no DROP, but its process-wide2048 entry budget (including previous probes)
expires by23:07:50 UTC. It therefore does NOT cover the later automatic failures.
Client65536 sample budgets end P1 at02:13:57.007, P2 at02:14:13.883, P3 at
02:15:24.094; periodic cumulative counters continue. First256 syscall logs also
cover only the beginning. These trace caps prevent full end-to-end attribution
of later failures; do not claim loss-free delivery for the whole run.

## UDP ports checked in response to user question

Physical client sockets are P1 UDP3658, P2 UDP3659 and P3 UDP3660. No bind
collision, fallback allocation or 'address in use' failure is present. At
02:20 MSK Get-NetUDPEndpoint found no listeners on3658–3674,3478 or31314; the
games had exited, and no competing application held those ports at inspection.
VPS relay destination is77.73.67.175:3478. Virtual ports30/40/3173 are channels
within the shared per-process UDP socket, not separate Windows port bindings.
No evidence supports port occupation by another application as this run's cause.

## Status

Initial connection failure NOT reproduced; addressed kick processing confirmed
by logs. Repeat-join automatic disconnect remains OPEN, with newly captured
pre-defer native send rejection. MSG_PEEKLEN's role in the former failure remains
unproven. No code, binaries, service settings, saves or firewall changed in this
review; no game launched or new gameplay test prescribed. Next code investigation
should map the rejected native destination/channel and its lifecycle, while
reserving trace capacity for the later failure rather than logging every healthy
packet until the budget is exhausted.
