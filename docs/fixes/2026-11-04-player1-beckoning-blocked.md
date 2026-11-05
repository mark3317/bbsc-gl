# Player1 Beckoning Bell blocked — 04.11.2026

Read-only investigation. Live logs collected from all three current profiles at approximately 13:02 MSK: 3 files, warnings=0. Player1/3 changed during collection; not final game logs. BB_USER_DIR is each profile/user. Detailed BBSC diagnostics off.

Player2 GPU DeviceLost at12:50:52.078 and runner exit23. Player1 sees LocalPlayer2 DEAD at12:52:14.102; Player3 at12:52:15.231.

All three durable Party journals agree on finalized revision253: owner LocalPlayer3, closing=true, joined/member LocalPlayer2; LocalPlayer1 is absent from joined, pending and members. Profile1 has already left; this is not stale membership of Profile1. The installed coop/party/compat.py tick availability condition requires owner in (None,self.id), so LocalPlayer1 returns unavailable regardless of its own completed leave. bbsc_party.cpp/PartyCanBeckon feeds ApplyBbscBellsAnywhere which forcibly rejects effect9000. This is a sufficient concrete blocking condition in the current state, though release logs do not capture the item-use callback itself.

Static local-three group has one owner for the entire roster. Owner release requires room/joined/pending drained; departed guest cannot start a separate world while another owner remains. Crashed Player2 remains joined, preventing normal room drain. Timeout does not authorize membership/authority release. Treat as recovery/availability limitation of the static path after peer crash; not an Insight/area diagnosis. Existing relay crash-isolation source correction does not release this ownership or restore already-stuck session.

No product code, build, deployment, process termination, settings, saves or live journals changed. No speculative recovery applied. Gameplay recovery OPEN.
