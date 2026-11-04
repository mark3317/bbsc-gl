## 04.11.2026 — Player 1 menu exit corrected; build pending

Latest Player 1 run09:43-09:45MSK, native PID9008 exit0, diagnostics off.
Read-only Party journal retains ownerLocalPlayer3 and joinedLocalPlayer1 at rev239.
Title unload incorrectly required unanimous shared leave, blocking an isolated
player with stale membership. Current title ticket now permits LOCAL unload only
after fresh native idle/not-loading observation and explicit cancel. Ownership,
room/journal, consensus and Beckoning gates remain unchanged; no forced release.
Native StageFlow01940DBB..01940E14 requires System MenuMan+250 to set task+150;
request2 alone omits it. Restore +250 after CloseMenus, after save and Stop,
without replaying save latches or invoking StageTransition. Earlier claim that
+250 itself was necessarily a world reload was incomplete and is superseded.
Production quit, actual native branch on fake memory, offline-peer RPC and real
WinHTTP tests PASS. No real saves/settings/journals changed. Gameplay pending.
Details: fixes/2026-11-04-player1-menu-exit.md.

The latest run has no verbose quit trace. Journal evidence proves retained group
membership, not the exact point reached by this run's callback. Independent socket
processes reproduce the inability to obtain the old title ACK with an offline
owner. Local unload no longer waits for that ACK; shared release is still blocked.

Native regression executes the original 01940DBB..01940E14 instructions from a
local analysis ELF on fake memory, proving the menu latch selects task+150.
This does not simulate all StageFlow or establish actual arrival at the title.

Tests: tools/test_menu_quit.py, tools/test_title_request_native.py;
party/test_rpc RPCTests offline-peer, current-ticket and retained-bell cases;
party/test_winhttp_bridge native_title_with_offline_peer_preserves_group_fence.
The quit fixture also needed the current Blank atomic declaration to compile.
No trampoline change. No protocol format change or VPS component affected.
