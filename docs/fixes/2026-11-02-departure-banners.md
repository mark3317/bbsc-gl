# Remote departure banners — 2026-11-02

## Evidence and cause

Latest three-profile run 22:50–22:59 MSK collected again into
`bloodborne_pc/out/coop-dev/runs/review-20261102-departure-banner/pc` (6 files,
no collector warnings, no files changed while copied). P1 host, P2/P3 guests.
P2 used Blank at 22:55:53.540 and native home step ran at 22:55:58.906.
Later P1/P3 both recorded peer f824c509 leaving at 22:59:00.161/.170.

Native departure producer 0x0178B0E0 reads departing PlayerIns role via virtual
+0x560 and its role-table +0x4C line before lookup at 0x0178B14D. Role 0 has
20000406 ("Bell silenced. Returning to own world."); role 7 has 20000405
(named remote departure). Recreated actors can use role 0. This explains the
reported local-return text on peers. Exact rendered string and actor role at
that callback were not logged, so attribution of the recorded banner remains
code-based inference supported by the user's observation and role-table logs.
The previous zero-id fallback does not help: role 0 +4C is already nonzero.

## Change and validation

Hook 0x0178B146 (LEA RDI,[RBP-A8]) changes only RSI for remote non-invader
characters to 20000405. Native leaveName substitution and cleanup continue.
Local identity uses PlayerIns pointer, independently of session state/role.
Local-return ids 20000401/403/406 remain native. Named cooperator departure
texts now say "<?leaveName?> disconnected from the game." / "<?leaveName?>
отключился от игры." in generated EN/RU tables. No transport/server changes.

Both standalone and bundled trees updated. `tools/test_departure_banner.py`
extracts the production callback and runs it through actual bbsc_hooks.cpp
mid-function trampoline: remote role-0/role-7/empty text, two remote actors,
local/absent actor and both invader types PASS; native return ids unchanged.
Generators checked original ids/tags against read-only English game FMG.
Bundled DLL build exit=0 (4 existing warnings), delta deploy exit=0, 5 files.
Backup: D:/Games/Bloodborne/coop-dev/backups/departure-banner-20261102-231716.
Built current working tree atop 59ff490; existing unrelated work remains uncommitted.
No game launch, settings/save changes or VPS update. Gameplay confirmation pending.

## Next gameplay check

Three players connected: one guest uses Blank; only that guest sees own-world
return, host and remaining guest see that guest's name + disconnected. Repeat
after a kept boss-wipe reload to exercise the role-0 case. User launches games.
