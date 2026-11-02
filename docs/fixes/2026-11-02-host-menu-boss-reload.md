## Installation 2026-11-02 05:01 MSK
Bundled DLL build exit=0 (two pre-existing unused warnings). Five-file delta installed on both stopped machines, copy exit=0. Backups: PC D:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050137; laptop C:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050146. No file audit per preference. First laptop invocation stopped before copying due to missing explicit delta file list; corrected invocation succeeded. Gameplay pending: laptop host / PC guest, quit host to title shortly after boss clear; title must remain until explicit Continue. No game launched, saves/settings untouched.

## 2026-11-02 — host menu exit raced delayed boss-clear reload

Latest run collected from PC and laptop under bloodborne_pc/out/coop-dev/runs/host-menu-20261102 (3 files each, no collector warnings). Laptop was host, PC guest. Host log: boss reward 04:55:38, System Yes 04:55:51.306, BlockClear2_1 51.446, save/Stop 51.505, direct title request 51.808, unexpected world construction 04:56:14.995; second exit at 04:56:24.734. The old message claiming Continue is not evidence that the user selected Continue.

Production boss-clear hook previously returned as soon as session stopped, allowing delayed BlockClear2_3 native reload to compete with confirmed menu exit. Guard now precedes session/role checks: skip delayed leave and home callbacks while quit intent exists, for host and guest; do not arm boss recovery during quit. Normal boss behavior retained. This closes an identified code race; logs alone do not establish all native request writers.

Standalone c41723b / bundled b80d19f / port pin 554ebdd. Production boss_quit and menu_quit fixtures PASS. Build/deploy status below; gameplay confirmation pending. No saves/settings changed.

