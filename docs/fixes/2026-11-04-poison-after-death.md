# Poison retained after death — 04.11.2026

Status: BUILT / INSTALLED PC15:19MSK / gameplay OPEN. DLL build, five-file delta
preparation and PC copy exit0. Backup:
`D:/Games/Bloodborne/coop-dev/backups/death-status-20261104-151917`.
No game launch or real save/settings/game-data edits. Record: parent
`out/coop-dev/runs/death-status-deploy-20261104-1518/run.md`.

Earlier implementation status: SOURCE FIXED. Retained revival now applies the original
death effect-persistence rules and native resistance reset. Targeted fixtures and
full BBSC_MOD syntax PASS. No DLL build/deploy/restart, real save/settings/game-data
changes, commit/pin/push. Earlier investigation below is historical evidence.

Snapshot: parent `out/coop-dev/runs/poison-after-death-20261104/pc`.
All three current Player profiles collected at 14:57 MSK, since 14:30 MSK;
three game logs, no collection warnings. All ChangedDuringCopy=true: live
snapshots, not final logs. Profile mapping: game-7=Player1, game-14=Player2,
game-21=Player3. Source BBSC HEAD and parent gitlink both 0ddb1d4, with existing
working changes. Player1 reports DLL built Nov 4 14:35:40, version 1.1.0.

## Observed timeline (MSK)

- Player1, guest in Chalice Dungeon: 14:55:22.849 PartyGhostDeath, session6,
  character type1, own-world0, echoes19832.
- 14:55:26.675 PartyGhostDeath_2: living partner, no boss fight, retained
  respawn without reload. This is the native death chain, not the old watchdog
  substitute.
- 14:55:26.704 death penalty drops19832 echoes; stain holds19832.
- 14:55:27.451 revived in place, HP594, host lamp2902950 at39/31.5/-49.
- 14:55:27.452 native death detectors rearmed for the next life.
- Player2 host sees remote revive14:55:28.665; Player3 guest14:55:28.915.

No poison/effect list or buildup values are logged. This is the relevant recent
death candidate, not proof that the reported affected player was Player1.
Logs cannot distinguish a retained effect, renewed exposure at the destination,
or stale status UI.

## Initial interpretation (historical)

The earlier detector-rearm change is active and native death dispatch occurs in
this episode. Native dispatch alone therefore does not establish status reset.
`BbscRespawnInPlace` retains the same actor, reproduces event-revive operations,
calls the actor reset vtable+0xA8, restores HP and clears death state. It contains
no explicit status cleanup. Whether the native reset covers poison has not been
established; the skipped real load is a plausible missing cleanup boundary.

## Original native behavior traced read-only

- Local event revive013CBC46 calls actor vtable+A8. The PlayerIns vtable's
  target018BD0E0 only writes zero to control+114: no status or gauge cleanup.
- Native death018C4C45..018C4C9A removes unsaved timed effects: param duration+8
  >=0 and saveCategory+141 ==FF. This alone misses saved poison effects.
- Per-frame native effect serialization018BCA37..018BCC87 first clears the ten
  saved-effect records. At018BCC20 it reads current HP from stats+F8. Mask03B7
  categories0/1/2/4/5/7/8/9 require positive HP; mask0048 categories3/6 survive
  death. Restoring HP on the same actor lets the former persist unless removed.
- Original SpEffectParam rows1200/2120/2121 and many enemy variants use saved
  category0 for poison; rapid poison category2, frenzy variants category1.
  Files under the configured install/game/dvdroot_ps4 read only.
- Native SprjChrResistModule at modules+28 has five remaining-resistance values
  +10..20 and caps+24..34. Function01A5C380 recomputes caps through player virtual
  +1E0 for indices0..4, then sets remaining to max(cap,0): zero buildup. Constructor
  01A5C1B0 also zeros fractional regeneration+38..48, pending trigger mask+4C and
  capacity-change latch+50. A pending trigger must not fire again after revival.

## Change

`BbscResetDeathStatuses` runs once on the dead local actor after a safe respawn
destination and native revive vtable have been validated, before warp/HP restore.
It removes effects with the native death-discarded categories and unsaved timed
rule. Native017E1D90 owns unlink/VFX/bookkeeping; its returned next node is used
instead of a freed node's link. No poison-ID list and no blanket effect erase.
Native01A5C380 resets all five gauges; fresh-module fractions/triggers/latch are
cleared. Persistent categories3/6, indefinite session/equipment effects and unknown
custom categories remain. The normal native serializer updates remaining records;
the helper does not edit savedata or call a save/load routine.

Actor ownership, loading/quit/title, writable resistance module, complete bounded
acyclic effect list and native API signatures are checked first. Unavailable cleanup
returns false into the existing real-load death fallback instead of reviving with
stale statuses. The shared path covers host/guest, ordinary/boss-lamp retained
revival and repeated deaths; real death loads keep the original path.

## Validation

- `tools/test_death_status_reset.py` PASS: extracted production cleanup, all256
  category values and duration boundaries, three host/guest lives, native erase
  boundary including poisoned freed nodes, saved/indefinite effects preserved,
  partial gauges and pending triggers, loading/living/quit/title/wrong actor,
  missing/foreign modules, bad signatures and malformed/cyclic lists.
- The same fixture executes the actual original01A5C380 machine code in isolated
  Windows memory with real SysV virtual resistance calls, including zero/negative
  caps. Original death/serializer mask/HP-gate and API bytes verified read-only.
- `tools/test_repeat_death.py`, `tools/test_boss_lamp_respawn.py`,
  `tools/test_death_accounting.py`, `tools/test_death_hotpaths.py` PASS. Boss-lamp
  fixture first lacked the compiler runtime on PATH; rerun with it supplied PASS.
- Complete bloodborne_re.cpp BBSC_MOD clang++ syntax and diff --check PASS.

No build/deploy/game restart. Gameplay OPEN: poisoned host and guest die and revive
at a lamp, then repeat; status icon/damage and buildup disappear, co-op survives.
Also cover frenzy/rapid poison/other gauges and boss spectator revival. Fixtures
do not establish the visible game's result or exclude fresh exposure after revival.
