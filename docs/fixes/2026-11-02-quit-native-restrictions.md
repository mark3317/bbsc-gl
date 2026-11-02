## 2026-11-02 — native death/leave restrictions during confirmed exit

User clarified: no neutral input filter; character must be unable to move/open
menus, camera remains native. Prior pad-block implementation rejected by user
in run quit-input-review-20261102 (both machines collected). Confirmations
03:03:02.815 laptop and 03:03:55.889 PC reach title requests at 03:03:03.504 /
03:03:58.152. Logs do not establish pad filtering effectiveness.

Removed pad neutralization and its header/test, including unbuilt frontend
release experiment. Accepted Yes snapshots player-slot manager+70 and flag4047,
then holds native death/warp-pending +70, menu brake +2DC, Lua load wait +8D
and native death/leave flag4047 throughout pending/title world context.
Camera data is untouched; no actual death/HP change or death penalty requested.
Cancellation restores original values only in the same non-loading world;
actual load owns reset, Continue uses existing native character-ready release.
Native loading-after-session-close remains. Production menu_quit fixture PASS,
including held restrictions until title, cancel restore and native-load ownership.
Actual movement/camera behavior still needs game validation.
