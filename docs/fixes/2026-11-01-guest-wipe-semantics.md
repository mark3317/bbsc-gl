# Guest boss-wipe semantics and peer visibility — 01.11.2026

Scope authorized: client death echoes, vial/bullet restock, repeated join text,
and 2–3 seconds of missing players after respawn. GPU crash / combat latency
from the preceding run remain separate and open.

Code: standalone 4bdb50f, bundled bd008b6, BBGL pin 2fe5bef.

- Accepted session warp with reason `wipe` applies the existing death penalty
  BEFORE StageTransition snapshots the guest inventory/echo state. Rejected
  placement/map/chalice requests do not charge. Existing death snapshot
  consumption prevents charging the same death again on retry; existing stain
  handling and protection of rewards earned while dead are retained.
- A wipe-restock pending flag is consumed once after completed-load recovery
  finds a living guest. If recovery had to revive in place, that path already
  restocks, so no second refill is added. Session end cancels pending recovery.
- Reinsertion no longer waits 2500 ms AFTER an alive local character and
  loading=0. Existing native FirstSyncWait still gates peer reconstruction;
  tasks already possessing a remote character are not restarted.
- Before restarting insert tasks, the existing role-column override is armed
  and applied immediately for 15 seconds. Its caught-up carrier is already
  mapped to the silent sentinel. This is the existing time-window mechanism,
  not a new per-member announcement hook; a real join overlapping this short
  recovery window may also receive the quiet carrier. Outside the window
  original role lines are restored normally. Multiplayer overlap needs coverage.

Only affected checks ran: production pre-warp ordering/rejected-warps fixture,
native_wipe_alive/native_wipe_dead (exactly one restock), boss_without_load,
home_pending and direct integration assertions. All PASS. No live saves changed.
No full recovery suite or unrelated tests. Gameplay confirmation remains needed:
both death orders, echoes drop once, restock uses available storage, peers show
without the old extra wait, no repeated join banner, real next join still works.

Build exit=0, installed on both stopped computers at 04:45. Override and active
package files match, bundle manifest verified on both.
DLL SHA256 8E1C63DEE97B980DA601558D24C4BD91EE6F16E5B7EE574E25298DC29163A161.
Backups: PC `D:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-044550`,
laptop `C:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-044552`.
