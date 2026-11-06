# Independent lamp returns and authoritative world state — 06.11.2026

## Evidence

P1 guest, P2 host, installed00:31 build. Live logs are in parent
`out/coop-dev/runs/old-yharnam-dream-return-20261106/{pc,pc-followup}`.
P1 reaches Old Yharnam00:42:36.345. Selecting return at00:45:20.955 sets
72300100 but is journaled as personal QUEST, with no queued trip. Native
return eventually begins00:46:38.894 and arrives00:46:41.847. P2 snapshots
while in Dream apply that same map-local72300100 bit. User reports lamp
availability returns when P2 (previous location owner) returns. The exact
native instance/packet causing the delayed recovery is not proven.

## Changes

* Centralize command classification in LampTravel. Both DLL and non-MOD
  predicates recognize the ORIGINAL return flags for all46 ordinary/DLC lamps
  and10 dungeon lamps. Queue only a matching LOCAL lamp in its matching map;
  destination remains original Dream2102950. Release the SAME original flag,
  retaining native animation/waits/stage loading. Starting return does not
  require the map owner to remain present or a destination snapshot to arrive.
* Original-script survey finds t211000 missing from the original allowlist:
  the generator's broad21-area exclusion also excluded the native lamp in
  m21_01. Add it; distinguish actual Dream headstones210xxx from211000.
  Every original ground-lamp ESD carrying the parameterized return is covered.
* Preserve local one-shot trip bits (BOTH0 and1) across owner/map snapshots,
  legacy map application and dedicated Dream application. Applies to ordinary
  and chalice returns, altar selection/layer requests and44 headstone travel
  flags. Incoming owner state can neither cancel our request nor launch the
  owner's trip on another player. These commands are also excluded from the
  personal quest journal through the unified predicate.
* Activation flags remain on the original native path. Workbench t210692's
  literal70000100 is a DIFFERENT action, verified against original ESD; it must
  not be generalized into a trip. Invalid map/lamp, remote actors, zero writes,
  offline and disabled-independent contexts retain their guarded/native paths.

## User's world-state rule

User requests important world state shared from its owner to the other players.
The existing owner snapshot/epoch/coordinator pipeline remains authoritative
for environment state; native ownership/replication remains responsible for
NPC/enemy HP, death and transforms. Owner exit chooses a remaining resident;
returning session host does not seize a resident owner's world. Shared lamp
activation/discoveries still use the session lamp channel. Local travel requests
are commands for one player, not a canonical environment snapshot. Personal
travel must not move everyone or be overwritten by another player's request.
No new enemy cache, periodic manual enemy correction or synthetic warp added.
The tests establish these existing authority rules and preserve ordinary world
flag updates alongside the new command isolation; no claim of exhaustive
in-game validation of every world mechanic.

## Validation

* New tools/test_lamp_dream_returns.py PASS: actual production ESD context,
  command range, queue/release/arrival;46 lamps, host/guest, owner absent/present,
  and negative contexts. Actual independent snapshot apply plus actual
  KeepBbscGuestTalkBits: both roles/bit values, repeating owner snapshots,
  unrelated bytes, disabled mode, and all trip-command families.
* Read-only exhaustive original ESD survey PASS:46 ordinary/DLC +10 dungeon
  return scripts, exact map/index expression, native activation exclusion,
  workbench action exclusion. No game assets copied or changed.
* Counterfactual tests on in-memory source, without modifying the worktree:
  original command predicate FAILS range admission; original snapshot path
  FAILS local command preservation. Corrected production paths PASS.
* Existing native travel + original seven altars/common/Dream/chalice return
  event admission/animations/waits PASS; ten-dungeon return fixture PASS.
* Native authority/source/HP/owner epochs, presence/owner selection/routing,
  bootstrap/FirstSync/door-state admission, session lamp distribution,
  unqueued Dream loader and shared-progress policy fixtures PASS.
* Full BBSC_MOD syntax via build/key-admission-syntax.cmd exit0. Log:
  build/lamp-dream-return-syntax.log (existing CRT warnings).

HEAD/pin4989896 unchanged; shared dirty source tree preserved, no mixed commit.
No DLL build/deploy. Both games remain running (14124/21528 at status check).
No process termination, live-memory, settings/save/game-asset writes or push.
Gameplay OPEN: P2 leaves location for Dream, P1 independently returns through
its lamp; swap roles, repeat after reunion, then ordinary/DLC/chalice lamps.
The earlier diagnostic-only handoff entry is historical; source now corrected.
