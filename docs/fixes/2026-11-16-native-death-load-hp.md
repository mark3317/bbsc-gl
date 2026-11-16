# 16.11.2026 — native HP restoration on retained death loads

Regression after 50e48f5: removing post-load revival exposed a direct death-load
path that does not run the final Lua death step. The watchdog can call the lamp
point loader without the slot-manager+70 write from SoloPlayDeath_2 or
PartyGhostDeath_2. The point loader selects a destination, but does not arm
native resource restoration. Actor creation alone therefore does not imply HP=max.

PrepareBbscNativeDeathResources runs at the existing NotifyBbscDeathReload
handoff, only for a dead local cooperator before loading. It sets the same native
slot-manager+70 byte. It does not set HP, call a revive or add a delayed action.
StageFlow 019395C6/019395CF runs original 018FD460 (HP=max through 018BCD40),
and clears +70 at 01939610. The full-load old-state reset remains unchanged.
The 10-second reload rule and post-load revive stay removed.

Added timeline fields at existing death-load request, native summon construction
and completed-load observation. No additional hooks, timers, polls or packets.

PASS test_native_death_load_hp.py: production preparation plus executable
original 1.09 gate and max-HP instruction spans in isolated memory. Negative
control retains HP0; prepared host/guest restores 594, consumes native byte;
living travel/damage, invaders, title, quit, loading, missing player excluded.
PASS death_load_boundary, independent_death_destination, post_load_recovery.
Last live run confirms repeated HP0 after guest construction, but did not log
native +70 at construction entry; the exact route in that run remains unproven.
Build/deploy and game result are separate in HANDOFF.
