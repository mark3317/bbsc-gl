# Local-three run 22:20: second guest still blocked — 03.11.2026

Evidence: parent out/coop-dev/runs/resident-slot-completion-20261103-review/pc.
All three loaded DLL build22:18:18, native PIDs31464/9340/10172. Standard
collection9 files, warnings0; three records changed during the first copy.
Final stopped-run collection: sibling final-pc,9 files/warnings0, all records
ChangedDuringCopy=false. Party events remain in pc.
All runners exited normally (exit0)22:23:55–57MSK; no games left running.

## Sequence (MSK)

P1 acquires ownership22:21:30. It initially invites P3 at22:21:47.854;
P3 receives delivered claim22:21:48.433 but no JoinRoom follows. The existing
20s undelivered-to-join timeout clears that claim22:22:08.466. P1 native queue
remains1 without an arrived guest until22:22:42.518. This is a separate failed
initial admission, not a second-guest transport failure.

P1 invites P2 at22:22:42.536; P2 delivers claim22:22:43.657 and calls native
JoinRoom22:22:46.088. It reaches guest state6 at22:22:50.280 and two actors
(one cooperator) at22:22:59.279. Host shows the arrived insertion at22:23:00.225:
mode1, cur6/next6, flags0xC, actor present, slot0/type1/role7/member3659.

Host search returns P3 again22:22:47.002 while P2 is marked joined.
P3 never gets a second delivered claim or JoinRoom. P1 still reports queued1,
ready mask0, slot maskFFFFFFFF, coop2/2. From22:23:01.975 through22:23:42.047,
completion reports `queued role or identity mismatch` every5s. No completion
success and no three-actor world occur. P2 leaves via menu at22:23:44.130;
that ends the resident-guest observation interval (about45s after actor arrival).

## What this establishes

The87a1186 correction has NOT fixed second-guest entry in gameplay. The diagnostic
stage proves completion got past host readiness, native signature, arrived task,
matching actor and nonzero slot user. It then found no request matching all of
role + full user + full character identity. The log does not separate those
three fields, so a specific role/account/character mismatch is not yet proven.
Remote HP is no longer the stopping predicate in this run; the previous policy
regression remains valid, but is not the complete cause of the game failure.

Next investigation: compare the actual native queued request layout and identity
namespace against remote PlayerGameData (including request role conversion).
Do not weaken full identity checks or clear an unrelated reservation. Investigate
the earlier P3 claim-without-join separately. No code/build/deploy/save/settings
changes made during this review. No new run requested.
