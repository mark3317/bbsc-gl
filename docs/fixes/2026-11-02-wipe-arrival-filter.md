# Per-member wipe arrival filter — 2026-11-02

Fixes the diagnosis in standalone docs/fixes/2026-11-02-wipe-join-banners.md.
Production changes synchronized between standalone and bundled mod trees.

TickBbscReinsertV8 now marks only eligible remote tasks immediately before
restarting them at FirstSyncWait. A one-shot entry binds task address to its
current member object. Expiry, task removal, member replacement, pending leave
and session-state change revoke entries; game-thread ticks prune stale entries.
Native member equality compares the arrival task's +D8 member with the live
marked insertion task's +C8 member. No copied refcounted member objects are kept.

Native 0196BCEF is the seven-byte LEA RDI,[RBP-F0] preceding text lookup at
0196BCF6; R13 is the arrival task, RSI the +34 role-line id. The hook substitutes
15000012 only for a matching marked arrival, then consumes the entry. That id
is already mapped to BBSC's silent banner sentinel by TickBbscMessages. Native
arrival creation, state transitions and cleanup still run. Unmarked arrivals
keep their original message id, even concurrently with wipe recovery.

Removed the wipe's host-wide +34 override, which would also silence genuine
newcomers for 15 seconds. Only the guest's own local return line retains the
existing +30 override. Other follow/warp policies are unchanged.

Checks (bundled tree): test_wipe_join_banners.py PASS (extracted production
functions: host/guest, two recreated members, unrelated concurrent join,
one-shot, second wipe, task reuse, leave/removal, timeout/session reset/null).
test_member_binding.py PASS; test_hook_resume.py PASS including execution of
the exact new displaced LEA and callback-provided RSI through the production
trampoline. Native bytes inspected read-only in runtime-mode-eboot.elf.
Gameplay confirmation remains pending; fixtures do not confirm the actual UI.

Delivery: bundled DLL build exit=0, four existing compiler warnings. Five-file
mod delta installed 23:08 MSK into the common PC installation, deploy exit=0.
Backup: D:/Games/Bloodborne/coop-dev/backups/wipe-arrival-filter-20261102-20261102-230857.
No game/launcher processes running; no game launch, server, settings or save changes.
