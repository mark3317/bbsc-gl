# 2026-11-02 — review of co-op with 3+ players

Analysis only. Inspected the current bundled working tree (pin 59ff490 plus local edits),
compared the same affected logic with standalone BBSC. No production code changes,
product build/deployment, game run or save changes. Existing resident-guest Blank
protection is already in source and is not a new finding in this review.

## P1: one dead peer blocks repair of every revived remote character

`TickBbscRemoteRevive`, bundled bloodborne_re.cpp:9005, uses
`BbscPeerLifeCounts().second != 0` inside the per-character loop. This tests the whole
party rather than the owner of `chr`. For observer H, A can report alive and have
positive HP with stale local death/draw flags, yet dead/spectating B blocks A's
repair. A can remain visually dead/invisible until B revives/leaves. The repair also
restores physics; collision/movement consequences need a real game run.

Production-function fixture: H+A+B, A alive with stale death bit, B reports dead.
Repair remains blocked after the 1s settle. Changing only B's report to alive
immediately allows the physics reset and death-bit repair for A. Reproduced.

Needed correction: resolve native character/member identity to the corresponding
relay life record. A party-wide dead count cannot decide an individual repair.

## P1: a partial life roster is treated as proof that all partners died

`LivingPartnerExists`, bundled bloodborne_re.cpp:4402, returns false before scanning
native player characters when all *received* life records say dead.
`BbscAllPartnersReportDead` does not require records from all current partners.
With H+A+B, a dead report from B and a missing first report from living A produce
false even when A's native player copy is readable and has positive HP. This can
occur during join/first-report delay, or when a peer's life channel is unavailable.

Production-function fixture: native roster has local H, living co-op A, dead B;
only B has a life record. LivingPartnerExists returns false. Reproduced.
A dead host's BeginBbscCoopDeath then requests a reload instead of retaining the
world for A; a dead guest enters the wait-for-host/wipe logic. The branch behavior
is present in source; occurrence/timing in a real session was not tested.

Needed correction: prove roster completeness and check each known partner's own
life/native state; missing records must not count as a reported death.

## P2: an ordinary host revive is interpreted as a wipe reload

`OnBbscLifePacket`, bundled bloodborne_re.cpp:22618, increments bbsc_peer_revivals
for any host dead(1 or 2)->alive(0) transition, including an in-place lamp revive.
`BeginBbscCoopDeath`:9422 and `TickBbscSpectate`:9497 treat the increment as a
completed wipe/reload. BeginBbscCoopDeath overrides RespawnNow with Spectate and
arms follow-warp without checking the explicit host-reloading state 2 or whether
another guest survived.

Three-player scenario: C stays alive, H and A die outside a boss fight, H respawns
in place while A's death handling is pending. H's alive report can cause A to take
the full wipe-warp path although the host never reloaded. This introduces an
unnecessary load instead of the intended in-place revive. Timing and resulting
world/network effects need a real game run.

Production OnBbscLifePacket fixture confirms that 1->0 increments the heuristic
without a state-2 reload announcement. The downstream branch was reviewed in
source; the whole game-thread death/warp sequence was not executed in the fixture.

Needed correction: distinguish an in-place revival from an actual host reload;
use explicit reload intent/generation while preserving old-client compatibility.

## Validation boundary

A temporary C++20 fixture compiled with MSYS2 clang++ and ran the extracted current
production BbscPeerLifeCounts, BbscAllPartnersReportDead, LivingPartnerExists,
TickBbscRemoteRevive and OnBbscLifePacket with simulated native memory. All three
reproduction assertions passed. Fixture used temporary files and was removed on
completion. These are code-level reproductions, not live gameplay confirmation.
Both source trees contain the affected conditions. No claim of exhaustive
coverage or confirmed cause of the friends' earlier symptoms.
