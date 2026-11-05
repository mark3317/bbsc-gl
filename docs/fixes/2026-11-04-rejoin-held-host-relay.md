# Rejoin while host retains ownership — 04.11.2026

Status: targeted checks PASS; two-file Party runtime delta installed on PC.
Gameplay verification remains OPEN. Parent run: out/coop-dev/runs/rejoin-host-held-20261104-2302.

## Defects and change

An outgoing peer failure fenced all subsequent frames until a global transport
reset. A new admission can reuse the same owner/generation, so that failure
survived and silently blocked the next aimed placement. A production DynamicEngine
regression failed before the fix and passes afterwards.

Each confirmed new claim now allocates a new outgoing stream for its target,
restarts that peer's sequence and clears its old errors. Old queued work and late
failure reports are fenced by their stream. Native TCP, ownership and other
guests' streams remain active. The existing incarnation/stream protocol is reused.

Relay enqueue now reports acceptance. Compatibility marks a placement submitted
only on acceptance and retries every 500ms while admission remains pending,
bounded by the existing 90-second placement expiry. Native acknowledgment remains
required before JoinRoom; submitting TCP or transport work does not replace it.

## Validation

- New repeated-admission regression: old peer error, retained host generation,
  second healthy guest, late old-stream failure, successful new guest frame.
- Real HTTP/native relay fixture: queue rejection is retryable; unacknowledged
  placement is retransmitted; repeated direct JoinRoom after room teardown works
  without host release/acquire, following a fresh manual responder action.
- Placement before/after admission, relay ordering/dedup/new stream, new-world
  relay reset, real native NP host rotation and retained idle-host role checks PASS.

These are isolated fixtures, not confirmation of the specific 22:47/22:49 live
failure's internal cause. That run did not record peer failure state. No saves,
settings or original game files were modified by this task.
