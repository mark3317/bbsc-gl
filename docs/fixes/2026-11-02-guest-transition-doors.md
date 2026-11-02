# Lecture Building exit doors — 2026-11-02

User reports clients opening teleport doors. Read-only CUSA03173 1.09 MSB,
ObjActParam and EMEVD identify:

| Object | ObjAct flag | ActionButtonParam | Event | Destination respawn |
|---|---|---|---|---|
| 3201123 | 13200123 | 3200000 | 13200311 | 3302959, Nightmare Frontier |
| 3201124 | 13200124 | 3200001 | 13200310 | 2602959, Nightmare of Mensis |

Events wait for activation, play SFX, wait six seconds, then call 2003[49].
The hook at 0x01CD91F0 sets fourth argument RCX=1 for these actions in session
state 6. Native EDX is ActionButtonParam ID (lookup 0x01F128A0); test at
0x01CD925E returns false through 0x01CD9263/0x01CD97D6 before registration.
Blocking acceptance prevents the local animation/activation, instead of merely
cancelling its later teleport. Host/solo, other doors and follow-host warps
retain existing behavior. No game files, saves or flags changed.

Test: tools/test_guest_transition_doors.py extracts production hook and executes
actual native prologue/rejection/epilogue from read-only ELF. Param lookup stub,
continuation sentinel. Both exits, states 0..8, unrelated buttons, preexisting
rejection and null PASS. Native signature checked. Live UI/replication unverified.
Gameplay: guest tries both exits (no opening/teleport), host uses exit (normal
travel with guests following).
