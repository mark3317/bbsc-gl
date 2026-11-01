# Disconnect/reconnect stress run — 02.11.2026

Status: source changes only. No production build/deploy/game run in this task.
Collected both machines plus read-only gameserver/shadnet journals. Run archive:
bloodborne_pc/out/coop-dev/runs/disconnect-20261102-0004.
SinceUtc 2026-11-01T20:55Z; actual clients start 23:58 MSK and end 00:04 MSK.
All collection.json entries ChangedDuringCopy=false, no warnings. Both machines:
DLL B8A57192D19682C7A0AD3EC9758DDF156F9E7AD5BECD8C18EDA43367803063CD,
native B67E179AB0D2CD60000876F6A9BFF424826EFCF1D41916876A49634089108C87.
This run uses the answerer fix, not the older DLL from the original menu deployment.

## Timeline (MSK, crossed midnight)

- 00:00:16–20: room 105, PC twin host, laptop test guest; JoinRoom succeeds.
- Laptop menu quit 00:00:58.862, save/Stop 58.928, direct title 59.599.
  PC sees departure, both leave room 105, server destroys it.
- 00:01:40–41: same roles, room 106; JoinRoom succeeds again.
- 00:01:58: laptop guest uses Parting Blank. Both leave; room 106 destroyed
  at 00:02:09. Native send-home runs on laptop at 00:02:03.752.
- 00:02:28–30: reversed roles, laptop host, PC guest, room 107; JoinRoom succeeds.
- Laptop host menu quit 00:03:04.699; save/Stop 04.755; state 7 until 14.638,
  then direct title. PC leaves at 00:03:14 and returns home at 00:03:28.
- 00:03:45: PC advertises sign; laptop sees it and creates room 108 at 46.971.
  Laptop mod logs outgoing claim at 47.035, but native HTTP reports TCP
  ConnectionTimeout at 48.036. No corresponding server claim and no room join.
  Server continues finding the unclaimed sign; room 108 remains empty until
  laptop menu exit at 00:04:33.900 (direct title 34.061).

The new failed attempt is before HTTP claim delivery, not the earlier
ESTABLISHED->PENDING/answerer regression. There are also connect timeouts on
other HTTP endpoints from 00:02:30 onward; the source of those TCP stalls
(network/host scheduling/etc.) is NOT established from application logs.
No server state, service, firewall or routing changes were made.

## Menu/control fixes

The late hook at 01C0D0C4 suppressed only the last +250 store. The original
Yes callback had already written MenuMan+25C and global+1547/+1548/+1549,
so native save/stage work could compete with BBSC's delayed title request.
This is a source-level defect; logs alone do not prove which instruction
consumed the particular user-reported unsuccessful click. All three logged
native confirmations reached direct-title completion, with no cancellation.
PC's later Lua exit is logged but has no native System confirmation.

Move interception to 01C0D057, immediately after a side-effect-free LEA.
Byte-verified MOV/CMP sequence is position-independent and no native stack
frame exists; a RET safely skips all original native save/stage writes.
Production trampoline fixture executes this exact instruction shape.

Confirmation immediately sets the native menu brake (+2DC) and Lua load wait
(+8D). On the next game-thread tick (after the confirmation functor returns),
call native CloseMenus(3) at 0176A900, as EventMenuBrake does. Do not destroy
a menu/command while its Yes callback is still executing. Recovery/unlock
helpers cannot undo the pending-exit locks. On cancellation restore original
values only in the same context, without an active load; successful title
transition leaves release to the native menu/load reset.

Accept valid native session states 0..7, including starting/leaving/failed.
A peer departure (state 7/0) during save no longer silently consumes the
confirmation through a session-changed cancellation. A new live session,
slot/world change, unavailable save, error or timeout still cancels safely.
There is no manual native session-state write.

## Claim transport recovery

Native HTTP converts the game's nonzero connect timeout to at least one second;
this run's failed claim timed out after about one second. Add at most TWO
additional attempts only for the seamless POST /summon_messenger/request and
only for cpp-httplib ConnectionTimeout. Inspecting httplib shows that this
error is produced by waiting for TCP connect readiness, before an HTTP body
is sent. Reuse the same body/headers; do not reissue native room creation or
publish another sign. Read/write errors, HTTP error responses, other endpoints
and public/ordinary requests are not retried. After exhaustion return the
original native transport failure. Persistent network loss can still prevent
matching; this is bounded recovery, not a claim to solve every connection issue.

## Checks

PASS: production menu/save/Stop fixture (roles, departure mid-save, duplicate
confirmation, menu close on next tick, save errors, target disappearance,
timeouts, original-lock restoration and load-context ownership).
PASS: actual production Windows trampoline (native LEA + hooked MOV/CMP,
normal execution and early RET repeatedly, original mid-function-store test).
PASS: production claim retry helper (scope, two retries, exhausted budget,
no replay after read/write/HTTP response, disabled policy).
PASS: http.cpp -fsyntax-only using the existing production Ninja compiler flags.
Diff checks PASS (http.cpp keeps its existing CRLF; cr-at-eol check).
Standalone/bundled mod source and tests synchronized. Real saves unchanged.
Game verification remains pending after a separately requested build/deploy.
