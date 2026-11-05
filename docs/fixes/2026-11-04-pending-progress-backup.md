# Pending shared progress: wrong backup root — 04.11.2026

Status: source fixed; isolated regression and native syntax checks PASS.
No product build, deployment, game launch, real save/journal/settings edits,
commit, pin update or push performed for this fix. Gameplay remains OPEN.

## Evidence and cause

Latest run: PC `D:/Games/Bloodborne/twin`, laptop client `test` at
`C:/Games/Bloodborne/test`, 12:01–12:12 MSK. User confirms the client loaded
its own world and remained there after departing the host's world.
Collected logs: parent `out/coop-dev/runs/repeat-client-death-20261104`.
Detailed BBSC diagnostics were off; the exact runtime branch is not logged.

Read-only laptop inspection found `pending-sd1-1.bin` updated 12:11:57,
containing 18 global progress flags (not 18 distinct bosses) and 160 world
groups. Its `.merged` and trip-journal `.applied` files are from 2 November.
Latest mod save-backup directory is also from 2 November. Pending alone is
not proof that no flags were provisionally applied; retirement follows a
confirmed native own-world save.

`BbscActiveSaveSlotUnchecked` already uses `BB_USER_DIR`, but
`BackupBbscSavesUnchecked` only searched `<cwd>/user`, `%APPDATA%/shadPS4`
and legacy `BBSC_SAVE_DIR`. Current Party launches supply the actual save
tree through `BB_USER_DIR`. With only that tree present, backup returns false.
`MergeBbscSharedProgress` then returns `{-2, 0}` before changing any boss/map
flags. `TickBbscSharedProgress` returns before the own-world save and journal
retirement, retrying the same failed backup every second. This deterministically
reproduces the blocked home-merge path in the current launch layout and explains
the pending outcome; it is not a new instrumented replay of the historical run.

An unrelated legacy tree or old launch snapshot could instead make the backup
report success without protecting the selected live character.

## Change

When `BB_USER_DIR` is set, back up that live root and bypass legacy roots and
`BBSC_SAVE_DIR`. An invalid explicit root fails safely; it cannot authorize a
merge using another tree's backup. Existing user-1004 exclusion, backup-before-
mutation ordering, native save acknowledgment and pending retry are retained.
With no `BB_USER_DIR`, legacy launch behavior remains available.

Existing pending journals are not renamed or replayed by this task. The game
can process them on a subsequent valid home recovery with the corrected build.

## Validation

- `python tools/test_progress_backup.py`: production backup and production merge
  against temporary artificial files. Modern layout, received boss and lamp/map
  bit, conflicting legacy/snapshot trees, protected user, missing source and
  failed destination retaining pending state, legacy launch path PASS.
- Same fixture against HEAD's original source fails at the modern-layout merge
  assertion, reproducing the regression before the fix.
- `python tools/test_personal_progress_commit.py`: PASS. Fixed its mock manager
  address lookup first: the old `p < 100` mock treated the real player-manager
  singleton address as unavailable and failed before exercising reconciliation.
- `python tools/test_shared_progress_policy.py`: PASS.
- `clang++ -std=c++23 -fsyntax-only` for the complete `bloodborne_re.cpp` with
  `BBSC_MOD`, production shim/fmt/xbyak includes: exit 0.

These checks do not confirm the game's eventual save or journal retirement.
Next gameplay validation: return a guest home with host progress, allow settled
home reconciliation, observe `.merged`/`.applied` and the expected lamps/bosses.
