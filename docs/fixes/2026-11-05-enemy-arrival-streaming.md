# Late-arrival enemy AI wait — 05.11.2026

Status: source corrected; targeted fixtures and full MOD syntax PASS. No DLL
build/deploy/restart. Gameplay remains OPEN; two local games were running.

User reports inert enemies for several seconds on entering a map already
occupied by its first resident. The pre-event bootstrap waits for native CHR
historical-death admission. Until that succeeds, all guarded EMEVD execution is
held, including ordinary events that initialize/enable enemy AI.

Confirmed source defect: `BbscWorldApplyNativeInitial` preflights every local
nonempty block, then additionally required the number of matched local blocks
to equal ALL records in the resident's native packet. The resident may have
additional streamed adjacent blocks. A complete packet for the visitor was
therefore rejected until streaming footprints happened to match. This is a
reproduced source failure, not a measured per-block explanation of the user's
specific live occurrence.

Original CUSA03173 1.09 loader `0191BDD0` looks up each incoming CHR record in
local map storage; a missing local block branches `0191BF1A -> 0191BF70` and
continues with the next record. The actual historical-death handler is still
`0190E8B0`, called by native `0191BF6B`.

Removed the reverse set-equality requirement. All local nonempty blocks still
require a matching ID, actor count and readable entries BEFORE any native
handler runs. Extra provider records are permitted; no-overlap/nonempty input
is rejected. Packet bounds, owner/world/epoch/request/load correlation and
once-only admission are unchanged. No custom enemy cache, local guest AI
authority, HP/position writes or model hiding was added.

Validation:

- `tools/test_world_native_initial_streaming.py`: the previous production
  equality check FAILS the resident-superset case. Corrected production PASSes
  the complete request/reply/load lifecycle with an extra provider block,
  missing local coverage, wrong actor count, atomic preflight and no overlap.
- `tools/test_world_native_initial.py` and `tools/test_world_native_bootstrap.py`
  PASS; original serializer/handler ABI checks PASS against the cached original
  ELF. Native loader skip branch inspected read-only in that same ELF.
- Full BBSC_MOD syntax via `build/key-admission-syntax.cmd`: exit0, existing
  deprecation/unused-option warnings. `git diff --check`: PASS.

Next gameplay check after a coordinated build: owner stays in an active ordinary
map after streaming neighboring blocks; visitor enters via lamp/rejoin. Living
enemies should act immediately, earlier dead enemies should remain absent, and
the resident must keep AI authority. Also check a host entering a guest-owned
map. Do not mark the reported gameplay bug closed from fixture results alone.
