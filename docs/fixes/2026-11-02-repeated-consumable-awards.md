# 2026-11-02 — repeated one-time consumable awards on join

Latest collected run: perf-combined60-20261102, PC guest / laptop host.
Goods 1500 (Madman's Knowledge), lot 37000, flag 50002000 awarded at
05:15:45.981, 05:18:45.106, 05:20:37.861, 05:23:33.746 MSK; counts 1/2/3/4.
The latter three follow join loads. K3-repeat detected but allowed each repeat.

SkipBbscRepeatedLot now blocks an already recorded flagged stackable goods lot
outside chalices even if its item has been consumed. Uses the existing per-character
receipt, not the host's flag or mere ownership of the goods. First awards, other lots,
unflagged drops, unknown goods rows, explicit ledger regive and chalice scope remain
allowed. Missing unique-item recovery retains its previous behavior. Skipped awards
restore get flags through the existing path. No special case for goods 1500.

Production-function C++ fixture: tools/test_repeated_consumable_awards.py PASS.
Only an isolated test executable was compiled; no mod/package build or deployment.
Both source trees updated. Gameplay confirmation pending. Existing duplicated items
are not removed. Exact native event restarting the award is not established here.
