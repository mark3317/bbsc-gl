# 2026-11-02 — hold quit DisableMove at native consumption

Last combined run confirms menu interception (PC05:23:49.828, laptop05:16:37.988),
but has no movement-flag readback; it cannot prove when the flag cleared.
Native eboot confirms 0132F770 resolves entity10000 and writes ChrControl+111;
01513EB5 tests that byte before the native movement-permission branch.
Old Hold returned on global+8 !=0, although title loading may leave the same
living character visible. Ordinary tick also offered no protection against
native writes between tick and consumption. Blank's Lua OnLeaveMenu_Yes uses
SetLoadWait/LeaveSession, not an explicit DisableMove call: previous equivalence
was an assumption, not verified native control flow.

Hold now follows exact world/character/control identity through loading. A
byte-verified hook before CMP [r12+111],0 reasserts native DisableMove only for
the captured local control during pending/title quit. Original CMP/JNE resumes;
remote/replacement characters and ordinary play are untouched. Cancellation
restores previous restriction; real load/Continue still owns control reset.
Confirmed-exit interception requires the movement hook to install successfully.

Targeted production menu fixture PASS (native reset after tick, load flag,
pending/title, remote/replacement/idle). Actual Windows trampoline PASS with
exact nine-byte CMP and JNE, both movement permission outcomes. Native game
movement remains pending user confirmation. No save/settings changes.
