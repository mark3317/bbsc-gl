# Independent revival: stale remote character and host respawn fallback

Status: SOURCE corrected; DLL not built/installed, gameplay OPEN.

User reports enemies stop reacting to clients after death and continue reacting
to only one participant. Also reports clients revive beside a resident host.

Collected both running 03:46:04 profiles in parent
`out/coop-dev/runs/enemy-p2-aggro-20261106/pc`: 2 files, warnings0,
ChangedDuringCopy=true. P1 HOST f4bbd967 owns both Cathedral blocks; P2 GUEST
dd95f01d. Control queue samples have zero backlog/drops/waits. Logs prove:

- P1 death03:48:01.887, revival03:48:05.232 at nearest lamp.
- P2 death03:48:29.381, revival03:48:33.698 explicitly `warped to partner`.
  Host lamp2802959 cannot resolve in the current Cathedral map; the old follow
  branch therefore uses P1's position. This is a confirmed routing cause.
- Models after the same-visit deaths are merely rebound, not recreated.
  Independent mode returns before TickBbscRemoteRevive; PlayerVisualLife
  previously handled journeys and missing meshes but not kept-death revival.
  Native remote death teardown is therefore not reversed by this lifecycle.
  Native AI target selection is absent from these logs: the exact AI rejection
  condition is NOT measured; the source lifecycle defect is established.

Changes:

- An authoritative same-place dead->alive presence transition schedules one
  original per-character removal/arrival cleanup + native FirstSync creation.
  It waits for the native member task and retains identity/world/visit fences.
  No AI target forcing, enemy aggression writes, bulk character cleanup or
  synthetic remote HP/death-bit writes. Each peer/life is independent.
- Restored native HP with a remaining dead bit also admits bounded recreation
  after1s, covering a death shorter than the presence interval. Existing retry
  bounds apply. A healthy replacement is left alone.
- Independent local revival (both roles) resolves the player's selected native
  lamp, preserving defeated-boss-lamp priority. An unavailable lamp returns to
  the normal local death load instead of a nearest/host/partner teleport.
- Independent spectate/repeat-death fallback no longer follows host wipe
  placement, waits for the host's load, or ends the room for a local reload.
  Host-revival counters cannot select the legacy guest warp branch at death.
  Legacy non-negotiated follow behavior remains unchanged.

Validation: production per-peer lifecycle fixture PASS (native removal/arrival
cleanup/insertion ordering, repeated same-visit lives, four peers, pending tasks,
missed death presence/dead-bit fallback, healthy replacement, travel guards).
Old bind-only negative control FAILS the new revival assertion.
Production destination selection PASS both roles, own-vs-host lamp, host in
another map, missing local lamp and defeated-boss priority. Production full
spectate controller PASS host revival/wipe/repeat death/no partners/failed
local lamp/loading/legacy path; old follow negative control FAILS.
Original1.09 FirstSync/render-gate Windows trampoline PASS; native repeated
death rearm and runtime lamp guard PASS. Full MOD C++ syntax exit0.

No DLL build/deploy while games34116/26236 run. No real saves, settings or game
assets modified; no commit/push or pin change (HEAD/pin4989896).
Gameplay still requires both players to die/revive repeatedly and separately,
then approach the same living enemies: enemies must be able to acquire/switch
between either player. Also verify each client's own lamp with host nearby and
in a different map. Passing fixtures does not establish live enemy perception.
