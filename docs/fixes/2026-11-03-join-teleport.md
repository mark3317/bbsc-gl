# Initial guest placement — 03.11.2026

Request: move the joining guest to the host sooner and hide the visible relocation;
do not build yet.

`TickBbscJoinTeleport` waited for two seconds of host position stability and
polled every 250ms after native summon loading. This deliberately exposed the
old spawn before the final in-map warp. The tick now uses the first validated
actual host transform in the correct resident destination world. It runs every
normal game tick, with no additional settle delay. Unknown map, wrong world or
chalice mount, loading, dead actors, invaders and quit retain their gates.

A zero-duration native fade-to-black precedes the warp by one update, then holds
for 100ms before a 150ms reveal. It does not request another map load or play a
new teleport animation. This covers the final positional correction; it does
not suppress the game's entire summon animation sequence. Failed fade access
falls back to immediate placement. Invalid vtable remains retryable and does
not mark initial placement complete. No fallback to another guest's position.

The cover releases after 500ms if readiness disappears or immediately on session
loss in the same living world. Native loads/title, actor replacement, death and
quit take fade ownership; this tick does not reveal over them.

Validation: `python tools/test_join_teleport.py` extracts and executes the actual
production tick with native calls stubbed. Covers immediate/once-only placement,
cover/reveal, failed readiness/vtable/fade, session reset, map handoff, invader,
load/death/quit/replacement ownership. `python tools/test_join_destination.py`
passes destination/map/mount/freshness and no-second-load assertions.
These compile isolated fixtures only. No DLL/game build, deploy or game launch.
Native frame ordering and visual appearance still require an in-game check.
