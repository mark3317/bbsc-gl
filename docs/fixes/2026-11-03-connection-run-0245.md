# First entry fails before the rejoin scenario — 03 November 2026, 02:40–02:44 MSK

Evidence: `bloodborne_pc/out/coop-dev/runs/review-20261103-0245`, all3 profiles,
6 stable files, collection warnings0/ChangedDuringCopy false, VPS gameserver
and shadNet journal23:39–23:46 UTC. DLL1.1.0 built02:33:09, native new logging
present. P1/test1 host; P2/user2 and P3/user3 intended guests. UDP ports remain
3658/3659/3660, with distinct relay registrations. Documentation review only.

## Outcome

No guest reaches JoinRoom/state6 or a remote character insertion. Therefore
this run does not exercise repeat-join slot reuse or validate the new fix.
No Native send rejected, deferred-backlog Stop01789812 or new Matching2
stale-handshake/callback guard rejection is recorded. Do not declare the
specific rejoin guards successful or responsible for the entry failure from
these logs. Both failure families remain open.

- P2: claim02:42:12.886, native negotiation failure02:42:23.057: phase11,
  wait_s=-0.00685, task_phase12/result0, channel/exchange present,
  ready=false/accepted=false. Stale claim cleared02:42:33.305.
- P1: empty room native Stop01789f9e at02:43:05.138; server resets Room16.
- P3: claim02:43:15.055 expires02:43:35.550 without a join. Another claim
  arrives02:43:35.775; failure02:43:42.000 has the same original phase11 /
  wait expired / ready=false fields. A further claim arrives02:44:03.326.
- User exits P3 menu02:44:07.293, P2 menu02:44:14.022, P1 menu02:44:20.099.
  Host negotiation failure02:44:08.961 occurs after P3's menu exit and must
  not be counted as an independent completed guest attempt.

Signaling ESTABLISHED occurs but does not establish a game session. Subsequent
DEAD events are later consequences, not the initiating native negotiation error.

## Encoded packet correlation

Unlike the older decoded-only comparison, new W/I samples carry the encoded
frame hashes and intended destination. Bounded sampling reports no omissions
in this run. Match W to the intended receiver's I (which precedes codec decode),
not to another process or to a decoded payload hash.

| Window MSK | Direction, game vport40 | W sends | No matching receiver I |
| --- | --- | --- | --- |
| 02:42:12–02:42:23 | P1 -> P2:3659 | 17 | 5 |
| 02:42:12–02:42:23 | P2 -> P1:3658 | 10 | 0 |
| 02:43:14–02:43:42 | P1 -> P3:3660 | 11 | 5 |
| 02:43:14–02:43:42 | P3 -> P1:3658 | 14 | 8 |

The comparison searches the receiver's complete captured I samples, including
later arrivals. Correct physical ports are present in outgoing W records.
These counts establish a gap between local encoded send and peer transport
receipt, not the precise network segment that discarded a frame. W precedes
actual send; no local relay-send error is logged. Repeated identical commands
are counted as separate transmissions, not as distinct messages.

Final cumulative tx_error/wrong_peer/full/unbound/invalid/digest/no_key/auth
counters are0 on game vport40. This rules out recorded local queue/codec
rejection for the absent I samples; it does not guarantee successful WAN
or relay forwarding. Native syscall sends report no errors.

## Server limit

UDP relay remains active, registrations bind the correct IDs to3658/3659/3660,
and periodic UDP send_errors0. Its detailed per-frame trace has zero entries
for this run: the process-wide2048-entry budget was exhausted in earlier tests.
Thus W -> serverRX -> serverTX -> I cannot be completed retrospectively.
The one TCP relay send error is counted after clients exit, not evidence for
the UDP negotiation failure. No server restart, code/config change or deployment
was made for this review.

Next instrumentation must preserve a bounded fresh trace for each game run or
join attempt, rather than exhausting the only server-process trace during the
first successful session. This is necessary to distinguish sender->VPS,
server identity/routing admission and VPS->receiver loss. Do not bypass the
server with a localhost path, raise native negotiation deadlines, or attribute
this run to member-slot collisions without an actual room join.
