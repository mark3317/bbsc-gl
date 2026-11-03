## 2026-11-02 — repeat HP death lifecycle (source + targeted fixture)

Native OnEvent_4000_Hp is consumed once per map load; kept in-place deaths do not
rearm it. Subsequent HP deaths now enter BeginBbscCoopDeath with the death text
at 500ms instead of the 3500ms repeat watchdog. Native scripts retain the 15s
safety fallback. Alive/load/session reset clears stale native-entry time, so a
rapid next death cannot inherit the previous script. Active death/release/curtain
is guarded against duplicate entry. Boss/wipe/invasion decisions stay in the
common death handler; native Lua event registration itself is not modified.
Both source trees updated. Extracted production lifecycle fixture PASS for host,
guest, rapid next death, native fallback, duplicate entry, load/HP/curtain/teardown.
Bundled DLL build completed exit=0. No deployment. Gameplay confirmation pending; no saves changed.
