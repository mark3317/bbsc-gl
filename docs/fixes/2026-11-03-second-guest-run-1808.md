# Second guest still blocked in the 18:08 run — 03.11.2026

Logs: `out/coop-dev/runs/second-guest-1808-review/pc` in the parent repository.
Three profiles, mod build 18:07:19, native PIDs P1=41568/P2=15820/P3=40872.
Run started 18:08:38/39 and ended 18:12:07/08 MSK; runner exit=0 for all three.
Standard collection: 9 files, warnings=0, ChangedDuringCopy=false for all records.
Supplemental read-only copies: each profile's party-events.jsonl and last_run.log
under profile-1/2/3. No saves, settings, or party state journals copied.

## Observed sequence (MSK)

- P3 obtains Beckoning ownership at 18:10:05.284 and hosts the world.
- P3 selection queues its first request at 18:10:19.733: queued=1, ready mask=0.
- P2 receives the claim at 18:10:20.869, delivered serial=1 at 18:10:21.404,
  calls JoinRoom at 18:10:24.158, and reaches guest state6 at 18:10:28.218.
- P3 party events return P1 as a candidate at 18:10:22.654 and again at
  18:10:24.658, with P2 then marked joined. P1 keeps publishing/refreshing its
  sign, published=true, claim_pending=false; no delivered claim or JoinRoom.
- At 18:10:37.173 P3 still reports coop2/2, slot maskFFFFFFFF, ready mask0,
  queued1. At 18:10:37.548 its remote insertion task is mode1, cur6/next6,
  flags0xC, chr1, slot_type1, role7, member3659. The host and P2 show two actors,
  one cooperator. No three-actor transition occurs through the end of this run.
- Established P2/P3 traffic continues, including successful Duel Bell on/off
  round trips. The waiting P1 never reaches native connection negotiation.

## Conclusion and limits

The installed resident-summon completion fix did NOT resolve this run.
The symptom remains in host native admission before the second claim; this is
not evidence of a failed P1 transport handshake. Existing role mask patches
are active. The SosStatus.Update hook is running (recorded in host perf data),
but no `resident guest completed native summon request` success is logged.
The last observed native selection state retains one queued request with an
already resident first guest, matching the preceding run's obstruction.

The completion policy has silent guards for session/world, task, live actor,
PlayerGameData, signature, and queued role/full identity. Current logs do not
identify which guard rejects the real request, nor whether native completion
was called without reducing the count. Do not claim a specific failed guard
or memory layout error from this run. Next code investigation should expose
those decision points and compare actual actor/request identities. No product
code changed, built, or deployed during this log review. No repeat requested.

The test lasts about 90 wall-clock seconds after the first actor arrives; it
cannot validate release at the historical 180-game-second timeout.
