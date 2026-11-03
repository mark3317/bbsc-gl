# 2026-11-03 — review of03:34–03:53 game run

Collected6 stable files from3 profiles, warnings0, VPS journal and persistent
/opt/bbsc/logs/gameserver-20261103-002724.log. Snapshot:
bloodborne_pc/out/coop-dev/runs/review-20261103-0359.
Analysis only: no runtime code/build/deploy/service/config/save changes.

## User steering

User explicitly attributes Player3 automatic stop to CPU overload and asks not
to investigate that moment. Exclude03:48:35 Stop01789812 and its preceding queue
build-up from networking defect conclusions and next test requirements. This
is the user's explanation/scope constraint, not a separately established CPU
causality claim. Earlier automatic candidate diagnosis is superseded by this
instruction. GPU crash investigation also remains deferred as previously requested.

## TCP relay and repeat entries

Player1 host/test1, Player2/user2, Player3/user3; physical3658/3659/3660.
TCP connects03:34:33.976/39.393/42.597; VPS conn6/7/8. No reconnection or
superseded-socket notification in this game run. TCP stats stay3 clients until
final crash/exits, slow_disconnects0/send_errors0. Thus the previous false-host
sequence did not recur, but its actual reconnect branch was not exercised here.

Initial guest state6: P2 03:36:18.995, P3 03:36:34.665. Both play until03:47.
03:47:13 host leave handling observed (Blank/guest leave/session end); P3 native
stop178c11d same interval. P2 explicitly uses Parting Blank03:47:26.545, own
OnLeaveMagic03:47:29.554. These are not the prior stale-TCP departure sequence.

Repeat entries: P3 state6 03:47:46.432, full guest/world state03:47:58.345;
P2 state6 03:48:04.007/full03:48:24.320. P2 menu exit03:48:47.592 leads to explicit
SessionLeave delivered to host03:48:48.268. Further P3 claim03:49:08.422 reaches
pending join03:49:20.176 without confirmed state6 before a new claim03:50:55.916.
Final entries P2 state6 03:50:19.981/full03:50:40.774 and P3 state6 03:51:00.120/
full03:51:13.361. Host shows distinct remote slots0/1; no new stale identity
admission guard hit. No evidence of clients replacing each other's native slots;
this does not prove every possible room-incarnation scenario correct.

Host logs TCP queue pressure03:49:39.390:261530 bytes waiting, dropping new frames.
No connection-lost/WSA timeout logged in this process. Server does not report
slow-disconnect/send-error at this point. Queue symptom remains observed; exact
writer/OS/network cause not established and should not be confused with server
explicit peer departure.

## Final client termination and departure notification

P3 native log03:52:36.102: Vulkan GPU device lost(submit), WriteInvalid at0,
assertion STOP. WER events1001 at03:52:46/03:53:03 confirm current LiveKernelEvent141,
nvlddmkm.sys and WATCHDOG-20261103-0352.dmp. No deeper GPU investigation performed.
VPS conn8 gets reset, waits10s, emits PeerLeft for player0e5b6f79,sessionf174687f,
recipients2. Host and P2 accept03:52:47.244/247; host=false, neither guest-host
stop invoked by that notification. Host later confirms menu quit03:52:49.196,
P2 receives actual explicit host SessionLeave03:52:49.331 then stops03:52:49.343.
This confirms the bounded genuine-departure path after client termination;
it does not validate replacement suppression, since no replacement occurred.

## Diagnostic gap found

Only six local BeginAttempt calls, all initial NP activations03:36:13–49.
Later joins reuse existing signaling and never call ActivateConnection again.
As a result independent packet trace expires03:37–38 and is NOT renewed for
actual native rejoin attempts03:47–51. The earlier statement that NP activation
covers every game attempt is too strong. Renewal must also observe real
claim/join/native-attempt lifecycle while avoiding repeated polling resets.
packet-comparison.json explicitly has tx0 in the two later requested intervals;
zero samples are not zero packet loss. No per-packet attribution for those joins.
Periodic vport40 counters continue and show tx_error/wrong_peer/full/unbound/
invalid/digest/no_key/auth0 around03:48:10–35; they do not prove lossless delivery.
Native rejected-send records exist but this CPU-overload episode is excluded
from causal investigation per user instruction. No claim of a new network bug
based on the excluded stop/queue.

Next useful diagnostic change: renew by actual native attempt even when NP
connection is reused; retain existing stable transport and keep GNS experiment
in its separately requested branch/worktree. No new gameplay run requested yet.
