# Candidate consumption before admission — 2026-11-03

23:23 evidence: both hosts receive the second sign; no second claim, even after
queue0/readyffffffff. Exact rejecting predicate in that run was not logged.

Confirmed native defect: scan018732DD writes pending.state=1 BEFORE checking
prepared!=null (018732E5) or calling native SummonBuild01874710. State1 is skipped
by later scans. Any mode0 refusal (including transient control state at0187482E)
can therefore permanently consume a candidate without any request. Earlier role
cooldown masking covered only one refusal path. Overlap can expose other paths.

New selection transaction skips the 8-byte store/load span for cooperative
candidates, supplies original R14 prepared value, commits state1 only when the
native builder returns a real request, before QueueInsert. Null/not-yet-prepared
signs and mode0 rejection retain original eligible state0/2. Bounded250ms role
retry delay; original builder checks/timers/queue/capacities remain. Real accepted
request never retried. Blacklist destruction/null builder entry retains native
consumption; no freed payload retry. Exact synchronous frame/caller and object
pair checked. Extra rare builder gate hooks log last passed gate on refusal.

Regression tools/test_candidate_transaction.py executes exact native scan,
blacklist-free path, actual builder control-state refusal, call/return/epilogue
and production trampolines. Baseline loses B permanently; patched path retries
and queues B once while A remains consumed. Also covers absent prepared payload,
original state2, PvP, changed payload, blacklist null, other caller, mode1.
Native overlap and role-cooldown regressions also PASS.

This proves the defect and changed native flow. Attribution to a particular
transient predicate in the previous game is not yet proven; gameplay verification
of two simultaneous guests remains pending. No protocol/VPS/save changes.
