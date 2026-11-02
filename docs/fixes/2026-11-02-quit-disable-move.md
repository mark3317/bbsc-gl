## 2026-11-02 — no synthetic title loading screen; native DisableMove

Both-machine logs quit-native-review-20261102 collected. PC 03:21:29.301
confirmation -> 03:21:29.949 title request; laptop 03:22:30.719 -> 03:22:33.003.
The added BbscLoadingScreen(true) immediately before OnReturnTitle is removed:
it opens a world-loading screen (kind2) that the direct-title path did not own.
No substitute fade/logo/overlay added. Native title flow owns presentation.

Removed synthetic death/warp-pending +70 / flag4047 from confirmed quit.
They mark lifecycle state, not direct movement suppression. Use native Lua
DisableMove 0132F770 (registered at 0133DC5C): resolves player entity10000 via
013C97A0 (explicit local-player branch at 013C985C), writes ChrControl+111.
Snapshot original value, apply to the same character/control object throughout
pending/title; cancel restores same-object prior value, real load owns resets.
MenuBrake/CloseMenus and load-wait retain their original native flow. No pad
filter, camera modification, HP change or death penalty. No forced world reload.
Verified read-only native eboot instructions, production menu fixture includes
no loading-screen open, cancellation, prior restriction, replaced character.
Game movement/menu/camera and title presentation still need runtime confirmation.
