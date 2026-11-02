# Active repository tables and scaling spans — 2026-11-02

## Evidence

Post-optimization laptop run perf-after-20261102 still had 282607 ms background scaling discovery and TickBbscScaling max361812us, with10 calls >50ms in one report. A 1ms budget checked after every8 rows cannot bound kernel queries or the earlier function stages. Runtime FPS gain is not established by this change.

## Changes

FindBbscParamTables now resolves the live game repository through BbscGameParamTable and validates type/count/first row. It returns only the active table, never scans the address space or keeps abandoned copies. This also removes full-process NPC scans from SolidNpcs. The second kit worker that scanned and patched all copies is removed; the existing live-repository worker remains the single readiness owner. Kit polling has the same3min limit. Optional Dream event-code searches are a separate subsystem and are unchanged.

Param row lookup validates a whole index directory once and reads entries directly; fragmented directories retain guarded field reads. Preparation creates a checked data view, validates row bounds and sizes, then avoids repeated memory queries for individual fields. Invalid/overflow/header offsets are rejected, fragmented resources fall back to checked rows. Scaling preparation polls the live repository every250ms (no initial5s sleep), at most180s. It still runs on the existing preparation worker and patches only the active tables. No game files or saves are changed.

TickBbscScaling checks the currently loaded owner tables and NPC row count before writing. A temporarily unloaded repository skips work; a replacement resets the pending key and starts preparation of the new active tables. Original armor is retained when retrying the same owner, preventing compounding of stagger multipliers. Data is published with the existing atomic Ready state, and only immutable prepared vectors are read by the game tick.

For a changed key, effect rows require one current writable-span validation each. Armor uses one current validation of its complete span per batch; after success values are copied directly within that validated span. The validation result is never cached across ticks. If mappings are fragmented, guarded writes remain, at most8 rows per batch. Direct batches remain capped128 rows. Time is checked after every row with a1ms cooperative target; a failed guarded write keeps the row pending rather than incorrectly marking completion. A single OS operation, owner lookup or log flush can still exceed a cooperative target: no hard latency guarantee is claimed.

New nested profiling labels: scaling table owners, scaling selection, scaling effect writes, scaling armor writes, scaling completion report. They overlap the parent TickBbscScaling and must not be added to it.

## Targeted verification

Bundled production fixtures: test_scaling_repository PASS (real allocated param directories/rows, direct preparation/armor writes, bounded batches, fragmented spans and directories, per-row deadline, failed write retry, original-armor preservation, unload/replacement, corrupt offsets, no process-scan calls or second kit worker); test_pending_work PASS (existing concurrent queue and scaling role/host-packet/expiry cases adjusted to direct effect writes); test_perf_policy PASS (live repository cache, changed owners/type/unload); test_original_bells PASS (native parameter identity/policy retained). No game launch or live saves used in these fixtures.

Standalone244ae80 / bundled e3a6c6d / port pin910ddd0. Native game-flip telemetry unchanged, no native rebuild needed. Includes preceding single-load join from2d68a7d.

## Runtime test pending

Use same graphics, route and roles: offline if desired, online alone, then PC host/laptop guest for2–3minutes; record times. Separately leave/rejoin and swap roles to exercise scaling key changes. Check enemy/boss HP and stagger, normal/solid NPCs and all bells. Compare preparation-ready time and TickBbscScaling/subphase maxima as well as FPS and >50ms frames/min. Do not clear caches or restore saves. After completion collect both machines including rotated logs. Until that run there is no measured improvement or confirmed elimination of long holds.

## Build / deployment

DLL build exit=0 (two existing unused warnings). Delta installed04:10MSK on stopped PC and laptop,5 files each, both copy exit=0. Backups scaling-repo-20261102-041003 (PC) and -041011 (laptop), each under Games/Bloodborne/coop-dev/backups. No file audit, no settings/saves changed or game launched. Runtime confirmation pending.
