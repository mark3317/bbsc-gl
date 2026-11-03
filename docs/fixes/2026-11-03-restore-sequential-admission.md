# Restore sequential admission — 2026-11-03

User explicitly requested restoring the previously working sequential connection.
Removed AllowBbscOverlappingAdmissions and the candidate transaction/retry hooks,
including forced R13 readiness, delayed consumption and their functional trace
registration. Native selector again waits until the previous admission completes.

Retained current-login identity synchronization, exact resident request completion,
role cooldown masking and the confirmed Blank ownership-release/notice fix.
These identity/completion/cooldown components were present in the successful22:52
run (P3 host, P2 then P1 guests, all three resident without first guest leaving).

Archived removed experimental functions and their two standalone fixtures under
parent out/coop-dev/runs/restore-sequential-20261103. No reset of shared dirty tree.
Targeted exact-native cooldown and resident-completion regressions PASS.
Source rollback only; no build/deploy/launch requested or performed in this turn.
Installed DLL remains23:41:30 until a subsequent build/deployment.
