# Fewer repeated memory guards in table/NPC/bell checks — 2026-11-02

User explicitly requests continued source optimization, NO BUILD yet. This chat did not invoke a production DLL/launcher/native build, packaging, deployment or game launch. Isolated C++ fixture executables only were compiled/run for targeted verification. This chat did not change installed binaries, profiles or saves. Concurrent work in the shared repository later committed these source changes and updated the DLL; see the audit below.

## Evidence / scope

Last capped60 comparison showed lower idle-owner overhead but individual table checks still up to15ms on laptop. Remaining Bell/NPC scopes had tens of milliseconds. This patch reduces redundant memory-guard work and detailed diagnostic formatting; it does not claim all remaining stalls have been identified or fixed.

## Changes

BbscGameParamTable still checks the live repository, loaded state, current holder/resource/table and type on each lookup. After validating an object range it now copies the needed fields directly inside that range, rather than repeating ReadValue+HasMemoryAccess for each field. Prefix repository slots up to0x150 are inside the already checked0x158 range; later cached/scanned slots require a separate8-byte validation. No new long-lived pointer or permission cache, no relaxation of owner lifetime/type checks.

LocalizeBbscQuestEvent reads the instance's ref/instruction pair, referenced file pointer, file directory header and final row header from already validated spans. Existing cache identity/range/event checks, generation clearing and writable-bit guard remain. Directory additions also reject overflow before forming event/instruction pointers. This reduces repeated memory-manager queries on each event step. No event permission list changes.

BellsAnywhere reads effect once from the validated goods row; only host/search bells fetch session state (PvP/Blank need no such read). Functional retained/lifted predicates are collected in fixed local arrays/booleans, so ordinary checks allocate no diagnostic reason strings. After applying the exact same availability decision, production returns before map queries, formatting, diagnostic mutex and timeline I/O. Detailed reason strings remain available with research enabled. Inventory/control-item, guest join/search, HP/local actor, native-yes and all retained restrictions remain. Functional profiling remains enabled as before.

## Targeted verification

Bundled fixtures PASS:
- test_perf_policy: loaded/unloaded/replaced repository/holder/resource/type and invalid pointers, prefix-boundary slot. A warm late-slot lookup performs exactly6 fixture validation/read operations per call, checked over100 calls; stale cached slot cannot bypass range checks.
- test_runtime_perf: production event index/instance cache hit/miss, reused rows, reload and overlapping ranges; progress checks unchanged. Test directories now use positive in-file offsets rather than synthetic wrapped offsets, matching the newly explicit overflow rejection.
- test_guest_bells: native/override, host/guest/local/remote, all13 byte conditions and4 register vetoes, all6 lifted conditions, no-lift case, control-item missing, upper register bits. Run with override off/on and research on. Production performs no diagnostic map queries; ordinary/PvP/Blank goods do not read session unnecessarily.
- git diff --check for changed source/tests PASS.

No full mod build was invoked by this chat, as explicitly requested. Game impact awaits later authorized build and another capped60 run. Installed late-run throttling evidence is unchanged; no thermal settings modified.

## Concurrent shared-workspace audit

After tests, HEAD changed externally to standalone bd47d35 / bundled cceaae3 (presentation removal). `git show HEAD:emulator/src/core/bloodborne_re.cpp` already contains event_context snapshots, off>0x150 slot validation and kept_reasons arrays. The shared DLL timestamp is05:05:47 and the external build log ends exit=0; HANDOFF records a separate presentation deployment. The parallel note claiming performance changes excluded conflicts with the actual committed source. This chat did not run those build/deploy operations. Do not treat this work as pending in an entirely unbuilt source tree: code is already in that parallel commit; remaining local changes are tests/documentation and the research-only logging comment. Runtime effect remains unmeasured. No rollback or replacement of external commits/binaries was attempted.

## Explicit combined build authorized and deployed —05:10MSK

The later user request to build/install all neighboring changes supersedes NO BUILD. Bundled62b3200 / standalone cfed133 / port17fde5d; production DLL exit=0. Installed5-file delta on stopped PC and laptop, both copy exit=0, backups combined-latest-20261102-051031 and -051039. Fast mode/no file audit. No game/settings/save changes. Combined runtime confirmation pending.
