# 03.11.2026 — host actions blocked while quitting to title

Request: a host quitting an active session must retain camera control while
movement, actions and reopening System are blocked, like a departing guest.

Confirmed native System exit in hosting states 1/3 now captures and holds the
guest departure's Lua SetLoadWait (+0x8D) and MenuMan menu brake (+0x2DC).
Both apply immediately and throughout native save, Stop and final party wait.
No pad/camera filtering, HP/death changes or DisableMove writes. Existing
save/disconnect/title order and native System-menu lifetime are preserved.

Cancel restores the captured values only in the original non-loading context;
replacement menu/Lua objects are never written. Native title loading owns reset,
and this hold stops once the native stage transition has started. Guest/idle
exit remains unchanged. Delayed host Blank cleanup cannot clear the quit wait.

Production tools/test_menu_quit.py PASS: host vs guest, repeated confirmation,
native reset/reassertion, cancellation and preexisting restrictions, replacement
contexts, load ownership, final party wait, title/Continue and earlier Blank.
The fixture executes production functions with mocked native calls; actual
movement/menu/camera behavior still requires a game run. The separately recorded
host title auto-reload issue remains open; this change does not claim to fix it.

Code commit: ac5e70b.

DLL build exit=0 (three existing unused warnings); five-file delta installed
on the stopped main PC, copy exit=0. Backup:
D:/Games/Bloodborne/coop-dev/backups/host-quit-input-20261103-20261103-161436.
All three Player profiles use this installation. No game launched; gameplay
pending. Saves/settings, laptop and VPS unchanged; no push or parent pin update.


Game check: in an active host+guest session choose System -> Exit -> Yes.
Until title, movement/actions/System must be blocked while camera still turns;
guest must leave normally. Check controls after Continue. User launches the game.


## 03.11.2026 — host menu lock retained through asynchronous title handoff

User reports System can reopen after a delay during active-host exit. Source
had an unguarded interval: TickBbscPendingQuit returned immediately after
bbsc_title_quit was populated, although OnReturnTitle only queues intent.
Host LoadWait/menu brake now remain asserted after final leave and CloseMenus
until native loading or world/menu replacement is observed. Handoff is latched
so reused singleton addresses cannot reapply the restriction at title/Continue.
Guest behavior and native save/Stop/final-leave ordering are retained.

Production menu fixture first reproduced the gap on old code, then PASS:
60s deferred title, reset by CloseMenus/native updates, host vs guest, loading,
context replacement/reuse, Continue and cancellation. Full BBSC_MOD translation
unit syntax PASS (existing getenv deprecation warnings). Source only; no product
build/deploy/game launch; live confirmation remains pending coordinated build.
See fixes/2026-11-03-host-quit-input.md. No save/settings changes.
