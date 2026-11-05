# Player models after travel into an occupied location — 05.11.2026

User reports missing player models again after the 21:29 build, and requests
installation and two-profile startup after correction. Installed source included
1d5d7ef; this is a follow-up, not an uninstalled copy of that earlier fix.

Player1/2 run_20261105_212953.log: P1 host enters Central Yharnam at21:34:36
and binds the resident peer at21:34:36.613 without requesting recreation. P2
requests a missing actor at21:34:38.328 and binds at21:34:38.917. On the next
reunion P2 recreates at21:36:15.713, P1 only binds at21:36:16.465. Bind messages
do not prove visible meshes. These logs do not contain the bound actor address,
so they cannot prove the exact allocation path responsible for the symptom.

Confirmed controller gap: its mandatory journey refresh depended on equality
with the previous actor address. A new PlayerIns address plus existing draw
state could bypass native FirstSync entirely, although retained member tasks
were already at CreateWait. No actor also fell through to a delayed retry.

Refresh now follows the meeting/local or remote visit transition regardless of
actor address. It waits for a settled native task, then requests existing native
per-character removal/FirstSync once. The actor supplied after that request is
left alone; recovery retries remain bounded. Initial session observations keep
native admission. No opacity/draw/death manipulation or new network protocol.

Validation: production TickBbscWorldPlayers fixture first FAILS on new-address
local travel with the old controller, then PASSES with the correction. Added
remote travel with changing addresses while task is pending, immediate missing
actor admission, and no repeated restart after admission. Existing reused-address,
apart/reunion, unfinished actor and four-peer cases PASS. Native authority/routing
fixture PASS. Fixtures use allocated memory only, no game processes or saves.

Build/deployment/startup: pending coordinated build with the concurrent enemy
and host-altar corrections. Gameplay visibility remains OPEN for user verification.
