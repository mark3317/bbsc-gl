# Boss bar reappears after host leaves first — 01.11.2026

Status: still open. Pre-load HUD reset deployed at 04:10; the 04:21 gameplay
run confirms it does NOT prevent gauge reactivation on return home.

Evidence copied to `bloodborne_pc/out/coop-dev/runs/20261101-0402-host-first/`
(PC/laptop mod logs and last_run.log). PC hosted, laptop was guest.
Mod source: standalone df04dd0; bundled 875884f. Gameplay followed a Cleric
Beast wipe and successful co-op recovery, then host menu exit.

Timeline (local Moscow time):

- PC 04:02:10.730: native menu confirmation, save slot 3.
- PC 04:02:11.594: save/disconnect complete, title exit released.
- Laptop 04:02:11.834: confirmed host departure; native stop follows.
- Laptop 04:02:14.397: stranded-guest fallback sends guest home. The warning
  says "15 s", but only about 2.6 s elapsed since confirmed departure; do not
  use the literal warning text as elapsed-time evidence.
- Laptop 04:02:19.217: restores 480 own-world flag groups.
- Laptop 04:02:19.280: Shared Progress merges 28 world flags, zero boss clears.
- Laptop 04:02:21.406–408: load generation 4 completed; boss context cleared
  with `had bar false`; own-world departure cleanup completes.
- Laptop 04:02:25.472: post-load Shared Progress merges another 10 world flags,
  zero boss clears.
- Laptop 04:02:26.464: `boss bar 500000 (Cleric Beast)` while solo/home.

The bar is re-created after the existing one-shot cleanup, rather than merely
surviving it. ClearBbscBossContext runs from TickBbscSessionExit; the later
TickBbscSharedProgress can still change world flags. Reapplying transient boss
encounter state through Shared Progress is a hypothesis, not proven: current
logs lack the individual changed flag IDs and the native gauge writer.
Next investigation should identify those flags / native gauge activation and
separate persistent progression from encounter state. A blanket periodic HUD
clear would risk hiding a legitimate solo boss fight.

Saves were not restored or changed during this investigation. T24 spectator
camera remains user-confirmed; this is a separate departure/HUD issue.

## Pre-load cleanup implementation, 04:10

Standalone `1a459d1`, bundled `fd49d8c`, BBGL pin `f8f6a38`.
The existing native ClearBossGauge now runs before the actual StageTransition
request in RequestBbscSessionWarp (including the client's wipe reload), before
RequestBbscDeathReload, and before the stranded guest's return-home transition.
Rejected/deferred session warps leave the current gauge intact. Cleanup after
completed loading remains a fallback. There is no periodic solo HUD suppression,
no new hook, and no change to progression flags or save/recovery logic.
This corrects the cleanup timing requested by the user. Whether it also prevents
the later observed gauge reactivation needs a gameplay run; Shared Progress
causality remains unproven and its merge policy was not changed.

Only `tools/test_boss_load_cleanup.py` was run: production death/warp functions
execute against a fixture, asserting three-slot reset before native transition,
failed selector/map/placement/chalice requests preserve the encounter, and a new
encounter can show its gauge. Return-home ordering is checked from production
source. No broad or save/recovery tests. Bundled DLL build `exit=0`.

Both PCs were stopped during installation. Override and active package files
match the build; all bundle.json file hashes verified and source updated.
DLL SHA256: `C59AD8B0C9C45195A2CF8F257B5633373FE30D48FC81C2EB7C83D175EE1CA8DF`.
Backups:
- PC: `D:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-041008`.
- Laptop: `C:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-041017`.

Historical proposed check: fight a boss, client dies, host then dies; the client's boss gauge
must disappear by the beginning of its reload and stay absent at the lamp.
Then host exits first: no boss gauge on the guest's return home. Re-entering a
real boss encounter must show its gauge normally. No save rollback required.

## 04:21 run: early reset executes, home reactivation persists

Evidence: `bloodborne_pc/out/coop-dev/runs/20261101-0421-host-first/`, both
machines' mod and game logs. PC host `041647-34336`, laptop guest `041701-11536`.

- Host 04:20:37.202: before-death-reload cleanup, `had bar true`.
- Guest 04:20:43.555: before-session-warp cleanup, `had bar true`, immediately
  followed by the wipe reload request. The new path actually ran.
- Guest 04:20:50.996: load generation 2 completed.
- Guest 04:20:53.751: post-death-load cleanup, `had bar false`.
- Host 04:21:01.384–04:21:02.172: native save/menu disconnect completed.
- Guest 04:21:02.501: confirmed host departure.
- Guest 04:21:04.489: before-return-home cleanup, `had bar false`.
- Guest 04:21:10.926: Shared Progress at load applies 23 world flags.
- Guest 04:21:17.580: load generation 3 completed; home cleanup `had bar false`.
- Guest 04:21:22.143: Shared Progress after load applies 20 world flags.
- Guest 04:21:23.168: `boss bar 500000 (Cleric Beast)` while solo/home.

This is renewed gauge activation, not a missed early reset. The fixture proves
call ordering only, not this gameplay outcome.

Read-only inspection of CUSA03173 m24_01_00_00.emevd.dcx finds event 12414702
enabling Cleric Beast AI (2004[01]) and gauge (2003[11], name 500000). Its start
condition references 12414700 OR 12415400; it exits if defeated flag 12411700
is set. Thus encounter-start flags can re-create a gauge through native events
after a HUD reset. Shared Progress OR-merges kind-1 bits including these map
flags. Exact changed flag IDs were not logged: this remains a strong lead,
not proof of the specific write. Next investigation/fix must distinguish
persistent progression from encounter state, including old pending progress.
No extra code/deployment or tests during this log investigation; saves untouched.
