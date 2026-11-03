## 2026-11-02 — Parting Blank return ownership (source only)

Native send-home and stranded recovery share a game-thread return claim. Duplicate
native callbacks are skipped without releasing the active load locks. Stranded recovery
now waits 15 seconds after state 0 instead of 1 second, allowing the native 5-second
OnLeave_Limit to run first; it claims before native side effects and only after Lua
readiness checks. Ownership survives loading and resets on completed home arrival or
a fresh session. The existing 3-second synthetic OnLeaveMagic remains a startup safety
net; the cause of missing native item events is not established. Both source trees
updated; source control-flow checks only. No build, deploy or game confirmation.
