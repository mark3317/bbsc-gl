# Echo HUD acknowledgement

## 2026-11-02 — echo HUD acknowledgement corrected (source only)

Replaced the pre-update widget heartbeat / MenuMan+0x210 pending-reward
heuristic with a post-format observer at native 0x016570EC. It reads widget
+0x18C (the number passed to the primary text update). Only an active widget
with an unchanged displayed number and unchanged different balance for 3s
produces a warning. Hidden/absent widgets, loads, ongoing rewards and native
roll-up reset the timer. No currency or pending-reward memory is modified.
Both source trees updated. Extracted production C++ fixture PASS; production
mid-function trampoline fixture PASS. Native bytes inspected read-only in
installed CUSA03173 eboot: whole ADD RSP,0x88 before saved R13 is restored.
No DLL build/install or game confirmation. Prior `widget last ran never`
warnings do not prove a visible HUD failure. Which layout bypasses this native
widget, and whether its visible counter stalls, remain unconfirmed.
