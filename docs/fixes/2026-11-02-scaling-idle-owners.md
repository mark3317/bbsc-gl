# Idle scaling owner validation — 2026-11-02

Capped60 run showed laptop TickBbscScaling max16.871ms, almost entirely scaling table owners16.866ms, with869 owner calls>8ms across the run. The old guard ran two repository lookups on every tick even when no data could be written.

Move selection of the desired scaling key before owner validation. If there is no pending batch and the complete applied key matches, cached row pointers are not dereferenced: the idle path validates at1Hz and immediately on bbsc_load_generation changes. Every key change and every pending write batch still validates current repository owners/count before touching cached rows. Temporary unload skips writes; replacement resets pending state and starts active-table preparation. An idle replacement without a load notification is detected within1s, and no row writes occur during that idle interval.

This reduces repeated guard work; it does not promise that an individual OS memory query is never slow. Selection work still runs on every tick and has its own profiler label. No arbitrary caching of live memory permissions or change to gameplay scaling formulas.

Production extracted C++ tests test_scaling_repository and test_pending_work PASS:10,000 idle calls produce no repository reads at a fixed clock;999ms still skips;1000ms forces two lookups; a load generation change forces immediate validation; role/settings/expiry/pending transitions, owner unload/replacement, guarded write retry and fragmented mappings remain covered. Diff --check PASS. No live game or saves used in tests.

Standalone0d71cad / bundled1f51244 / port pince93a3f. DLL-only update; native frame telemetry unchanged. Runtime effect pending. Keep60FPS cap and same settings/routes/roles for next sample: online alone then PC host/laptop guest2–3minutes, followed by leave/rejoin. Compare owner calls/frame and total scaling cost, guest >50ms frames/min and frame p99 windows. Previous capped sample is baseline (not earlier uncapped FPS).

DLL build exit=0,2 existing unused warnings. Installed04:41MSK on stopped PC and laptop,5 delta files each, copy exit=0. Backups scaling-idle-20261102-044133(PC)/-044139(laptop), under each Games/Bloodborne/coop-dev/backups. No file audit, no settings/save edits, no game launched. Runtime confirmation pending.
