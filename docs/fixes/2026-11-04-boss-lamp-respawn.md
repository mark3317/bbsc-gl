# Dead co-op player returns at the defeated boss's lamp — 04.11.2026

Status: SOURCE ONLY. No DLL build, installation or gameplay confirmation.

Request: when a player dies fighting a boss and a surviving player wins, revive
the dead player at that boss's lamp.

The existing spectator/BlockClear2_1 flow already releases the dead player after
the kill and its settle window. Previously BbscRespawnInPlace selected the old
host/own lamp or a living partner. It now prioritizes the defeated boss's native
return point for this release reason, for both dead hosts and dead guests.

RememberBbscBossLamp tracks gauge NPC-name ids while their character handles are
active. It retains the encounter when Failed_BossAreaMission removes the dead
player's HUD. The table includes all 19 story/DLC bosses with their own lamps and
known phase/name variants. Points match the original-event catalog maintained in
the parent scripts/boss_rematches.py; this does not enable rematches.

The new destination requires the existing post-death boss-kill callback, the same
current map and load generation, and a resolvable native lamp point. No lit-flag
requirement: survivors do not need to light the new lamp first. No lamp, progress
or last-checkpoint flags are written by this selection. Normal revive, curtain,
penalty and restock processing continue through the existing path.

Pre-transition/session-departure boss cleanup also discards the tracked lamp.
An active unknown boss clears the old identity. Map matching prevents chalice
copies of story bosses from using a story destination. Micolash, Gehrman and Moon
Presence have no individual lamp, so retain the existing fallback; chalices and
unresolvable destinations also retain it. Wipes and non-boss deaths retain their
existing destination rules.

Verification:

- tools/test_boss_lamp_respawn.py PASS: production identity tracker, destination
  resolver and full destination-selection branches up to native revive; all 19
  catalog destinations and phases, dead HUD retention, host/guest priority,
  ordinary deaths, stale kill/load/map, unknown/chalice and unresolved points.
- tools/test_boss_load_cleanup.py PASS: production pre-load cleanup, including
  discarding the new destination context, and direct warp dependency.
- tools/test_boss_quit.py PASS: unchanged production boss-clear/quit ordering.
- Full bloodborne_re.cpp BBSC_MOD syntax check exit0; diff check PASS.

No saves/settings/game files touched, no commit/pin/push. Existing unrelated local
changes retained. BBSC HEAD and parent gitlink remain 0ddb1d4.

Gameplay still required: die as guest while host kills Cleric Beast; die as host
while a guest kills Gascoigne; repeat with multiple dead players and a DLC phase
transition. Leave the new lamp unlit until the revive. Expected: all dead players
appear at that boss lamp, survivors remain in place and the session stays usable.
Also observe an ordinary death and a full wipe for unchanged behavior.
