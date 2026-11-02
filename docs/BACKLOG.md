## 2026-11-02 — black fade restored for deaths without reload (source only)

Restored native SprjFade black curtain around in-place co-op respawn: 0.6s
fade-out, revive after 0.7s, 0.5s black hold, 0.8s fade-in. Used by open-world
death and spectator respawn after boss victory; announcements wait for fade-in.
No synthetic loading menu. Real load/title/actor replacement cancels pending
revive; session end releases fade; failed revive falls back to native death load.
Watchdog ignores active curtain. Both source trees updated. Extracted production
C++ fixture PASS for host/guest timing, deferred notice, load/actor cancellation,
session end and failed revive fallback. No DLL build/install or game confirmation.

## 2026-11-02 06:46 MSK — final launcher + mod installed on both machines

User requested build/install latest local changes. Full fast package (native rebuild
included), BB_FAST_DEPLOY=1, exit=0. Bundled DLL build exit=0, 5 warnings. Includes
shared Dream ending / NG+ recovery, current polling/text edits and BBGL signaling
changes. Source base: BBGL879c0ee, bundledf2fca10 plus current working-tree edits.
PC deploy and laptop transfer/deploy all exit=0, 5219 files copied per machine.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/final-launcher-mod-20261102-064527;
laptop C:/Games/Bloodborne/coop-dev/backups/final-launcher-mod-20261102-064553.
No games launched, no processes terminated, saves/settings unchanged. File audits
and verification disabled as requested. Build/install do not confirm gameplay.
Package: bloodborne_pc/dist/bbgl-1.0.0-windows-x64.zip; log out/build-deploy.log.

## 2026-11-02 — recover shared ending / NG+ without a home warp (source only)

Supersedes the previous ending-to-home implementation. Per-character append-only
.finale journal retains the complete scene request, host target cycle and phase.
Checksum/phase/scene/variant/cycle checks reject corrupt records; incomplete tails
are truncated before another append. Completed scenes resume the NG commit instead
of replaying; incomplete scenes are replayed after reload. Cycle assignment is
absolute, preventing repeated increments across crashes. Native save result 0 plus
idle save manager is required before durable phase-4 acknowledgement.
Both native send-phantom-home and stranded fallback are suppressed for an active
finale; after native Stop the local actor is adopted in place, old world/progress
journals drain, then host ending flags/target cycle and native save are requested.
No home respawn selection or home StageTransition is issued by this path.
Both trees updated. Static event/native-byte/source-order checks PASS. No product
build, installation, live save edits or game run. Whole translation-unit compilation,
actual movie replay after a crash, in-place role recovery and native NG load remain
unverified. Power-loss durability beyond stream flush is not claimed.

## 2026-11-02 — host search interval 1s (source only)

User requested only host search acceleration. ConfigureBbscSummonPolling now
writes ServerInfo+8A0 = 1s; sign/create and guard remain 2s, all other timers
unchanged. Both mod trees and existing native fixture expectation updated.
No build, fixture compilation, deployment or game launch. Gameplay pending.

## 2026-11-02 — intermittent join: signaling generation guard (source only)

BBGL ignores stale Ack/Established/Close from a previous peer connection instead
of modifying the replacement selected by online ID. Production-handler fixture
PASS; HEAD baseline fails as expected. Activation/readiness fixtures PASS;
pre-existing changes preserved. No product build/deploy or game launch.
Mod source/pin unchanged. Exact cause of recorded native rejection at 06:03:02.838
remains open; intermittent join is NOT marked closed.
Details: bloodborne_pc/docs/fixes/2026-11-02-signaling-generation.md (workspace root).

## 2026-11-02 — shared Dream finale / NG+ (source only, unbuilt)

User superseded the guest-return-only design: host chooses the ending, guests fight
and view scenes, then all enter the host next NG cycle. Added selective m21 boss
flag borrowing, serialized scene replay, native Remo start/completion observation,
departure/follow deferral while the guest ending plays, and guest ending commit after
native departure/home restoration and the old shared-progress journal drain.
Next cycle travels in the existing cutscene packet reserved byte; native AddClearCount
and the m21 terminal ending flags are applied after the local scene. Host dialogue
remains authoritative; guest terminal story events are not opened.
Both source trees changed. NO DLL/package build, install, game run or save changes.
Static game-data/native-byte checks only; full translation-unit compilation and live
three-ending/skip/host-first/NG transition validation remain pending. Crash during
the pending ending-to-home interval is not yet journaled for automatic completion.

## 2026-11-02 — original co-op item text (source only)

Updated RU/EN bell prompts, searches, menus, tutorials and original goods 200/205/225/111
summaries/descriptions (categories 20/24). Category 10 names remain native; names checked
against installed engus/rusru item.msgbnd read-only. No retired kit/duel instructions.
English generator validates menu IDs and item description IDs against game FMGs;
both generated tables contain 199 matching entries. Launcher bell instructions and
server notice use original names too. Both mod source trees updated; no build/deploy
or in-game layout confirmation in this text edit.

## 2026-11-02 05:43 MSK — latest launcher/mod installed on both machines

After user closed game/launcher, retried deployment of the already built full fast
package. PC and laptop deploy exit=0, 5219 files copied each; no rebuild or file
audit. Includes native kit duplicate suppression and current local source changes.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/latest-launcher-mod-20261102-054241;
laptop C:/Games/Bloodborne/coop-dev/backups/latest-launcher-mod-20261102-054242.
Supersedes preceding deferred installation status. Settings/saves unchanged;
no game launched. Gameplay confirmation pending.

## 2026-11-02 05:42 MSK — latest launcher/mod built; installation deferred

User requested latest launcher and mod on both machines. Full fast package with
SKIP_BUILD=1 completed exit=0 (native sources unchanged); bundled DLL build exit=0,
5 compiler warnings. Includes current local source changes, native kit duplicate
suppression and prior consumable award fix. Base mod HEAD f2fca10 (working tree
changes included); standalone HEAD 5c4e124. No source commits/pin changes made.
PC deploy refused because Bloodborne launcher running. Laptop archive transfer
completed exit=0; deploy backed up selected files then refused at second stopped
check (GAME_OR_LAUNCHER_RUNNING), before copying replacement files. Neither
installation updated. Both need game/launcher closed before retry. No processes
terminated, no settings/saves changed. Package ready in dist/bbgl-1.0.0-windows-x64.zip.

## 2026-11-02 — native kit duplicates suppressed (source only)

Notebook remains the sole source of goods 200/205/225/111. Native award hook
skips lots containing only these goods and sets their get flags so gift events
finish. Mixed/unrelated lots are preserved. Shop row-result hook hides these
goods from native stock only at the list-builder call site; other categories,
price lookups and progression goods stay unchanged. Both source trees updated.
Targeted native kit lot/shop C++ fixture and original bell parameter fixture PASS.
No DLL build/deploy or gameplay confirmation. Existing duplicates are not removed.

## 2026-11-02 05:34 MSK — quit movement gate fix installed both machines

User reports movement still possible during latest menu exit. Earlier native
DisableMove implementation is NOT gameplay-confirmed. Native wrapper/address/ABI
are correct per read-only eboot; old Hold skipped global+8 loading interval while
same living character could remain active. No flag readback in old logs, so exact
reset writer/timing is not established. Added byte-verified hook before native
CMP [r12+111],0 at01513EB5; reassert native DisableMove for exact captured local
character/control through pending/title, even during loading. Normal movement,
remotes/replacements unaffected; cancellation preserves prior restriction.
Production menu fixture and actual CMP/JNE trampoline PASS. Standalone5c4e124 /
bundledf2fca10 / port879c0ee. DLL build exit=0 (3 existing unused warnings).
Five-file delta copied to stopped PC and laptop, both exit=0. Backups labelled
quit-movement-gate-20261102-053428 (PC) / -053436 (laptop). No games launched,
saves/settings unchanged. Build also includes pre-existing unstaged consumable
award fix in both trees; that work was preserved outside these commits.
Gameplay PENDING: hold movement input after confirmed System exit as host/guest;
character must stay still through title transition, then move normally on Continue.
Details docs/fixes/2026-11-02-quit-movement-gate.md.

## 2026-11-02 05:29 MSK — optimization work deferred by user

User explicitly ends optimization work for now; resume only on a new request.
Consolidated status, measured wins, unresolved stutters, versions, raw log paths,
thermal exclusions and future investigation starting point: docs/OPTIMIZATION-STATUS.md
(in standalone and bundled mod trees). Latest combined run did not prove another
FPS/stutter gain; do not mark remaining owners/Bell/NPC stalls fixed. Existing
logs retained. No code/build/deploy/settings/save changes in this wrap-up.

## 2026-11-02 — repeated Madman's Knowledge: source fix, NOT BUILT

Recorded one-time stackable goods awards are now suppressed on repeat outside
chalices, including after consumption. First/different lots and unflagged drops
remain allowed; missing unique recovery and chalice exception preserved.
Both source trees updated; production-function fixture PASS. No DLL/package build,
installation or save changes. Gameplay pending; supersedes earlier investigation-only
status. Details: docs/fixes/2026-11-02-repeated-consumable-awards.md.

## 2026-11-02 05:26 MSK — combined capped60 review: no further stutter improvement

Both collected in out/coop-dev/runs/perf-combined60-20261102,3 files each,
no warnings/changed copies. DLL built05:09:41. Thermal tail excluded from05:22:10
conservatively, before visible12–13FPS collapse; no temperature/frequency sensors.
Matched roles remain PC guest/laptop host. Early pair65s vs old70s: PC59.36->58.45FPS,
>50ms/min5.99->7.37; laptop52.45->51.03FPS,16.25->30.39 events/min. Laptop worst
149.99->117.54ms, fewer >100ms but more50–100ms frames. No general gain proven.
Extended first pair160s also retained, PC56.76FPS/26.94 events/min; laptop48.99/
23.19. PC burst05:14:58–05:15:23 not excluded as throttle. Pre-tail owners maxima
laptop15.34->20.87ms, PC13.24->16.47ms. Sustained-profile means did not improve:
owners PC110->148us/frame, laptop197->229 (different report coverage/scenes).
No hundreds-ms scaling calls; preparation PC2ms/laptop5ms, no broad scan regression.
Details docs/fixes/2026-11-02-perf-combined60-review.md + run analysis/metrics.
Do not claim snapshot optimization improved overall runtime. Next: detailed
memory guard/query timing correlated with slow frame events. No source/build/
deploy/settings/save changes during this analysis.

## 2026-11-02 05:10 MSK — combined latest rebuilt and installed on both machines

User explicitly requested build/install with all neighboring changes, superseding
prior no-build instruction. Standalone cfed133 / bundled62b3200 / port17fde5d.
Includes guarded table/NPC snapshots, research-only detailed bell diagnostics,
idle owner validation, repository scaling, book/refund policy, single-load join,
boss-reload guard on quit, and removal of custom loading/death overlays.
Bundled DLL build exit=0 (3 unused warnings). Existing targeted fixture results
retained, not rerun for deployment. No new native/launcher runtime changes, so
mod-only delta. Five files installed on both stopped machines, both copy exit=0;
no installed-file audit per fast preference. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/combined-latest-20261102-051031;
laptop C:/Games/Bloodborne/coop-dev/backups/combined-latest-20261102-051039.
No game launched, settings/saves unchanged. Runtime combined behavior PENDING.
Test reference2026-11-02T02:10:39Z /05:10:39MSK is deployment completion, not run start.
Keep60FPS cap; next same-route/role sample plus join/leave, death/wipe and host
menu exit after boss. Collect both rotated logs. Earlier SOURCE ONLY status is
historical; explicit build now completed. Performance/presentation interactions
need runtime observation, no FPS gain claimed from build success.

## 2026-11-02 — guard/snapshot optimizations; this chat did not build

User requested remaining-stutter source edits, DO NOT BUILD yet. This chat changed
both source trees and ran only isolated perf_policy/runtime_perf/guest_bells C++
fixtures (PASS), no production build/package/deploy/game launch or settings/saves.
Table/NPC reads now copy fields from validated spans; live owners/type/bounds and
NPC permissions/reload guards remain. Bell normal-path predicates avoid detail
strings/map queries/mutex/timeline; detailed reasons remain research-only.
CONCURRENT AUDIT: shared HEAD changed externally to bd47d35/cceaae3 and already
contains these performance edits (verified via git show of the committed file).
External DLL build timestamp05:05:47, exit=0; another HANDOFF entry records
presentation deployment. Its assertion that perf edits were excluded conflicts
with actual commit contents. No external commit/build was undone by this chat.
Remaining local edits: fixture tests, docs and a research logging comment.
Runtime performance impact still unmeasured; do not state no DLL changed globally.
Details docs/fixes/2026-11-02-perf-guard-snapshots.md.

## 2026-11-02 05:06 MSK — legacy presentation removed from mod

Standalone bd47d35 / bundled cceaae3 / port pin 849296a. Removed custom
load cover, death curtain, native loading UI open/close helpers, dead ImGui
loading layer, per-frame ticks and load_cover switch in runtime/launcher metadata.
Uses found: host-follow warp, guest wipe load, in-place death respawn;
respawn now executes directly with existing world guards and fallback.
Native game loading remains owned by StageFlow. No custom logo/plate code remains.
Targeted home_return, load_readiness, boss_load_cleanup, stop_phases, menu_quit,
follow_arrival PASS; bundled DLL build exit=0 (two existing unused warnings).
Delta copied to stopped PC and laptop with backups remove-load-overlays; exit=0.
No settings/save changes. Gameplay confirmation pending, especially death/wipe.
Parallel standalone performance changes excluded from this commit/build.

## Installation 2026-11-02 05:01 MSK
Bundled DLL build exit=0 (two pre-existing unused warnings). Five-file delta installed on both stopped machines, copy exit=0. Backups: PC D:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050137; laptop C:/Games/Bloodborne/coop-dev/backups/host-menu-boss-20261102-050146. No file audit per preference. First laptop invocation stopped before copying due to missing explicit delta file list; corrected invocation succeeded. Gameplay pending: laptop host / PC guest, quit host to title shortly after boss clear; title must remain until explicit Continue. No game launched, saves/settings untouched.

## 2026-11-02 — host menu exit raced delayed boss-clear reload

Latest run collected from PC and laptop under bloodborne_pc/out/coop-dev/runs/host-menu-20261102 (3 files each, no collector warnings). Laptop was host, PC guest. Host log: boss reward 04:55:38, System Yes 04:55:51.306, BlockClear2_1 51.446, save/Stop 51.505, direct title request 51.808, unexpected world construction 04:56:14.995; second exit at 04:56:24.734. The old message claiming Continue is not evidence that the user selected Continue.

Production boss-clear hook previously returned as soon as session stopped, allowing delayed BlockClear2_3 native reload to compete with confirmed menu exit. Guard now precedes session/role checks: skip delayed leave and home callbacks while quit intent exists, for host and guest; do not arm boss recovery during quit. Normal boss behavior retained. This closes an identified code race; logs alone do not establish all native request writers.

Standalone c41723b / bundled b80d19f / port pin 554ebdd. Production boss_quit and menu_quit fixtures PASS. Build/deploy status below; gameplay confirmation pending. No saves/settings changed.

## 2026-11-02 05:01 MSK — initial join black cover removed, installed both machines

Standalone 4ab8575 / bundled e5c149b: removed StartBbscLoadCover("summon")
from JoinSession_White; native summon loading UI and follow/wipe covers unchanged.
Bundled DLL build exit=0 (two existing unused warnings); diff --check PASS.
Five-file delta copied to stopped PC and laptop, exit=0 with backups labelled
join-no-black-20261102-050055 (PC) / -050110 (laptop). No settings/save changes.
Concurrent bundled HEAD advanced to b80d19f during this work; it includes e5c149b.
Gameplay confirmation pending: client should remain visible until native loading.

## 2026-11-02 04:59 MSK — idle owners capped60 comparison, thermal tail excluded

Collected both machines in out/coop-dev/runs/perf-idle60-20261102,3 files each,
no warnings/changed copies. DLL built04:43:41 (latest23677dc includes idle plus
book/bell changes). User reports late laptop throttling; sharp FPS break around
04:55:00, excluded all later data, no temperature/frequency evidence collected.
Matched alone105s: laptop >50ms/min43.91->3.99 (~-91%), FPS54.20->52.52;
PC58.69->58.93FPS, >50ms/min2.15->2.28 (rare-event variation).
Owner profiling laptop510.07->168.25us/game frame (-67%), PC168.18->114.05(-32%).
Individual pre-tail owners calls still15.34ms laptop/13.24msPC; repeated overhead
reduced, not hard per-call latency. Scaling no hundreds-ms holds observed pre-tail.
Roles REVERSED in pair: PC guest/laptop host. New early pair70s: PC59.36FPS,
laptop52.45FPS, >50ms/min5.99/16.25. Do not compare directly against old laptop
guest43.50FPS/94.19 events/min as same-role improvement. Death/wipe and thermal
end excluded. Details docs/fixes/2026-11-02-perf-idle60-review.md and run
analysis.md/segment-metrics.json. No source/build/deploy/settings/save changes.

## 2026-11-02 04:44 MSK — book / latest bell fix installed on PC and laptop

Built bundled 23677dc (standalone cd67d80; port pin 73f2da3), build exit=0,
two existing unused-variable warnings. Includes Vileblood Register removal
from automatic kit, native unanswered-bell Insight refund suppression, and
previous idle scaling / repository / single-load join changes. Game code clean
in both trees at build; original_bells test changes remain local, already PASS.
Five-file delta deployed on both stopped machines, copy exit=0; no installed
file audit, no settings/save changes or game launch. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/book-bell-latest-20261102-044425;
laptop C:/Games/Bloodborne/coop-dev/backups/book-bell-latest-20261102-044428.
Gameplay confirmation pending. Existing books are retained. On a character
without the book, kit must not add goods 130; natural acquisition stays vanilla.
Reference 2026-11-02T01:44:28Z is install completion, not game start.

## 2026-11-02 — bell Insight refund removed in code

Standalone cd67d80 / bundled 23677dc / port pin 73f2da3.
Suppress only common event 9183's 2004[8](10000,4680) refund, return success.
Removed timed currency correction and bell-pending marker handling. Boss/chalice
rewards unchanged. Production-hook fixture and original_bells PASS; bundled DLL
build exit=0 (two pre-existing unused warnings). No installation or save changes;
user requested code correction only. Runtime pending.
Details: docs/fixes/2026-11-02-bell-insight-refund.md.

## 2026-11-02 — Vileblood Register excluded from automatic kit

Latest PC mod log bbsc-mod-20261102-042704-14832.log at 04:31:02.986
explicitly records kit adding goods 130 to carried slot 78, alongside bells.
Removed 130 from BbscKit in standalone and bundled sources: no automatic grant
or kit parameter mutation; vanilla acquisition remains unchanged. Existing items
are not removed. Targeted test_original_bells production C++ fixture PASS:
exact co-op IDs 200/205/225/111, book row untouched, repeated preparation.
Source fix only; build/deploy and gameplay confirmation pending.

## 2026-11-02 04:41 MSK — idle owner validation reduced, installed both machines

Standalone0d71cad / bundled1f51244 / port pince93a3f. Unchanged complete scaling
key returns before repository owner queries;1Hz idle validation, immediate after
load generation, and mandatory current owner validation before every write batch.
No cached row writes happen during skipped idle frames. No formulas/settings change.
Production scaling_repository/pending_work fixtures PASS:10k idle calls no lookups,
999ms skips/1000ms validates, load forces immediate check, pending/role/expiry/
owner replacement/unload/fallback cases retained. Diff --check PASS.
DLL build exit=0 (2 existing unused warnings). Delta5 files installed on stopped
PC and laptop, both copy exit=0, no file audit. Backups scaling-idle-20261102-
044133 (PC D:/Games/Bloodborne/coop-dev/backups), -044139 (laptop
C:/Games/Bloodborne/coop-dev/backups). No game launch/save/settings changes.
Runtime effect PENDING same capped60 test, PC host/laptop guest,2–3min same route
plus exit/rejoin. Reference2026-11-02T01:41:39Z/04:41:39MSK is deployment completion,
not gameplay start. Compare against perf-cap60-20261102, not uncapped FPS runs.
Details docs/fixes/2026-11-02-scaling-idle-owners.md. Slow individual OS queries
can still exceed budget; no hard latency guarantee claimed.

## 2026-11-02 04:38 MSK — capped60 run: repository/scaling improvement observed

User reports much better feel, cap60 FPS kept. Collected both machines in
out/coop-dev/runs/perf-cap60-20261102,3 files each, no warnings/changed copies.
DLL built04:09:10. Active table preparation PC1ms/laptop4ms versus previous
laptop282.6s full background scan (different scope/work by design, not a main hold).
Laptop scaling max361.81->16.87ms, no published scaling calls>50ms. Remaining
max is almost entirely table owners16.866ms; owners869 calls>8ms across run.
Paired selected75s: PC57.76FPS (cap60), laptop guest43.50FPS, >50ms/min94.19
vs previous137.17; no >100ms frames in current paired selection. Previous guest
37.52FPS uncapped; cap/scene/load differences prevent pure optimization attribution.
Alone laptop54.20FPS, >50ms/min43.91. No new offline run. Full logs include
startup/other long intervals (PC8.684s, laptop950ms) outside gameplay selection;
not claimed fixed. Bell33.28ms/NPC25.32ms and other holds remain.
Details docs/fixes/2026-11-02-perf-cap60-review.md + run analysis.md/segment-metrics.json.
User qualitative improvement and targeted scaling runtime improvement supported;
all guest stutters NOT closed. Next candidate owners query cadence/memory checks.
No code/build/deploy/save/settings changes during collection/analysis.

## 2026-11-02 04:10 MSK — active-table scaling built and installed on both machines

Standalone244ae80 / bundled e3a6c6d / port pin910ddd0. Replaced process-wide table
search with active repository lookup for scaling, kit and solid NPCs; removed
second kit copy-scan worker. Parameter index/row reads validate spans once with
checked fragmented fallback. Tick validates active owners, skips unloaded params,
reprepares replacements and preserves original armor on same-owner retries.
Armor uses one current-span check per batch; direct copies inside checked span,
<=128 rows; fragmented fallback<=8 rows, time checked after every row (1ms target),
failed writes retained for retry. No hard guarantee against slow OS calls/logging.
Added nested scopes table owners/selection/effect writes/armor writes/report.
Target fixtures scaling_repository, pending_work, perf_policy, original_bells PASS.
Build exit=0 with2 pre-existing unused warnings. Native telemetry unchanged.
Mod delta installed5 files on each stopped machine, both copy exit=0. Backups:
PC D:/Games/Bloodborne/coop-dev/backups/scaling-repo-20261102-041003;
laptop C:/Games/Bloodborne/coop-dev/backups/scaling-repo-20261102-041011.
No installed file verification per preference. No game launch/settings/save changes.
Runtime FPS/stutter improvement remains PENDING. Next: same route/settings,
online alone then PC host/laptop guest2–3min; separately leave/rejoin and reverse
roles. Record timestamps, verify scaling/NPCs/bells, collect both rotations.
Test reference2026-11-02T01:10:11Z /04:10:11 MSK is install completion, not game start.
Details docs/fixes/2026-11-02-scaling-repository.md. Earlier perf-after analysis
retained as baseline; optional Dream tool event-code searches are unchanged.

## 2026-11-02 03:59 MSK — post-optimization performance collected, guest stalls persist

Both machines collected: out/coop-dev/runs/perf-after-20261102, 3 files each,
no warnings/ChangedDuringCopy. Latest DLL built 03:50:34 includes single-load join
2d68a7d in addition to perf fixes; both logs online, no new offline run.
Matched roles: PC host 85.76 ->84.59 FPS; laptop guest 39.10 ->37.52 FPS;
guest >50ms frames/min 131.66 ->137.17. No general FPS/stutter improvement proven.
Alone laptop 54.74 ->53.27 FPS, >50ms/min 67.47 ->51.20, but longer outliers remain.
SharedProgress laptop max 1314.43 ->41.48ms (old seconds not repeated; different
journal contents); real backup still 49ms laptop /90ms PC. Scaling still361.81ms,
10 calls >50ms in one report. NPC per-call weighted cost improved 5.75->3.33us;
Bell maximum still52.68ms. Overall selected mod reports6.61->5.08ms/frame,
without game FPS gain. Laptop background scaling scan completed03:57:07 after
282.6s (not main-thread hold); it ran throughout first paired segment, unlike
previous baseline, limiting causality. Roles swapped late, only10s comparable
post-load windows, no old baseline for reverse roles. Full online averages skewed
by menus/loading and must not be advertised as improvement.
Details: docs/fixes/2026-11-02-perf-after-review.md and run analysis.md/segment-metrics.json.
No code/build/deploy/save/settings changes in analysis. Next: background scan
cost, scaling subphase timing/budget overshoot, memory queries in Bell/NPC.

## 2026-11-02 03:51 MSK — single-load cross-map join installed

Standalone 21d3c73 / bundled 2d68a7d / port pin fa89ba0. Removed the explicit
post-summon RequestBbscSessionWarp("join") and obsolete WARP_JOIN switch/state.
Native connect-first placement already loads the host destination; final in-map
placement remains gated by host map identity, freshness and chalice readiness.
Wrong-world scoped-follow recovery remains enabled (may require a recovery load).
Production join destination fixture + follow arrival fixture PASS. DLL build exit=0
(two pre-existing unused warnings); 5-file delta installed on stopped PC + laptop,
copy exit=0. Backups single-join-load-20261102-035117 (PC) / -035128 (laptop)
under each machine's Games/Bloodborne/coop-dev/backups. Fast deploy, no installed
file audit. No game launch, save/settings changes. Runtime PENDING: connect from
a different map, expect one summon load and arrival beside host; check lighting
and streamed geometry because the removed reload was a historical lighting workaround.
Test reference 00:51:28 UTC / 03:51:28 MSK is installation completion, not game start.

## 2026-11-02 03:48 MSK — performance fixes built and installed on PC + laptop

Standalone 8f9e6fa, bundled 9d43fb7, port pin ba5956c. All four requested areas
changed: progress no-op preflight + skip duplicate backup/filtering (real mutations
still backup synchronously; failure retains journal); scaling armor in <=128-row
batches / 2ms cooperative checks; reload-cleared file event indexes + validated
instance cache; non-bell early return and validated-stack reads in bell policy.
Targeted production fixtures runtime_perf, guest_bells, pending_work,
shared_progress_policy, perf_policy PASS. New cache/no-op followup runtime fixture
PASS; mod build exit=0 (two pre-existing unused warnings). Native unchanged.
Delta installed 5 files each, stopped machines, both copy exit=0. No installed-file
verification per fast preference. Backups perf-bounded-20261102-034754 under
PC D:/Games/Bloodborne/coop-dev/backups and -034800 under laptop
C:/Games/Bloodborne/coop-dev/backups. Settings/saves unchanged, no game launched.
Includes previously built 2f07242 native DisableMove/no forced quit loading screen.
Runtime FPS gain/stutter removal still PENDING matched test. Scenario: offline,
online alone, PC host+laptop guest, same route/settings; separately join/leave,
NPC talks/bells, exit to title. Test reference 2026-11-02T00:48:00Z (03:48 MSK),
installation completion, not actual gameplay start. Keep prior raw benchmark logs.
Limits: real save backup I/O still synchronous; stagger armor rows transition over
multiple ticks; 2ms check is cooperative, not a hard cap on an OS call.
Details: docs/fixes/2026-11-02-perf-bounded-work.md (both mod checkouts).

## 2026-11-02 03:39 MSK — performance run collected and analyzed

Both PC/laptop collected in bloodborne_pc/out/coop-dev/runs/perf-20261102-review;
no warnings or changed-during-copy files. Deduplicated PC game sources.
Selected gameplay: PC offline 88.63 / alone online 93.85 / paired host 85.76 FPS;
laptop 68.52 / 54.74 / paired guest 39.10. Different scene/route not independently
controlled, so observed deltas are not exact causal mod cost. Laptop >50ms frames
0 / 67.47 / 131.66 per minute. All segment metrics in segment-metrics.json.
Confirmed long wall scopes: laptop SharedProgress 1314.43ms (03:33:34 backup/merge,
1324.71ms flip), Scaling 372.13/461.50/325.52ms; frequent NPC event localization
and ResponderBell processing. 2429.18ms flip not wholly explained by those scopes.
No proof of a specific mutex owner; scope wall time includes scheduling/waiting.
Report: docs/fixes/2026-11-02-perf-runtime-review.md (standalone) and run analysis.md.
No source modifications/build/deploy or save/settings changes during analysis.
Next optimization priorities: split durable file preparation from game memory commit,
bound scaling batches, index event ranges and measure query cache misses; preserve
save ordering and load safety. No measured optimization gain yet.

## 2026-11-02 03:39 MSK — quit DisableMove/no-logo delta installed on both machines

After user closed both games/launchers, prepared bundled 2f07242 delta installed
successfully on PC and laptop: 5 files each, copy exit=0. Previous refusal is
historical; installation now complete. Standalone 9f65a93 / port pin858969e.
Backups PC D:/Games/Bloodborne/coop-dev/backups/quit-disable-move-20261102-033922;
laptop C:/Games/Bloodborne/coop-dev/backups/quit-disable-move-20261102-033923.
No rebuild/repeated tests/file verification, saves/settings changes or game launch.
Runtime native movement/menu restriction, camera and no added logo screen pending.

## 2026-11-02 — quit screen removal/native DisableMove BUILT, NOT INSTALLED

Standalone 9f65a93 / bundled 2f07242 / pin 858969e. Latest run collected both
machines: bloodborne_pc/out/coop-dev/runs/quit-native-review-20261102.
Removed explicit world loading screen before title (source of added logo UI).
Replaced synthetic death markers with native Lua DisableMove on local entity10000;
menu brake retained; no pad/camera modification. Original movement restriction
restored on cancellation for same character/control object. Target fixture PASS,
bundled DLL build exit=0; staging + out/mod-delta.zip prepared, delta sent laptop.
Both installs REFUSED before mutation: GAME_OR_LAUNCHER_RUNNING. PC observed
bb-probe PID13284, Bloodborne PID28896/38588. No process stopped, no live files
replaced, no save/settings changes. Close game/launcher on both, then deploy delta.
Runtime movement/menu/camera/no-logo outcome remains PENDING.
Details: fixes/2026-11-02-quit-disable-move.md.

## 2026-11-02 03:27 MSK — diagnostic performance build installed on PC + laptop

Explicit user deployment request. Installed prepared perf-research-delta.zip,
6 files per stopped machine (native bb-probe + bundled mod + metadata), both exit=0.
Port 02bf0f4 / bundled d5a2322; no rebuild or installed-file verification.
Backups: PC D:/Games/Bloodborne/coop-dev/backups/perf-research-20261102-032649;
laptop C:/Games/Bloodborne/coop-dev/backups/perf-research-20261102-032703.
Settings/saves unchanged; no game launch. Runtime measurement pending.
Test reference: 2026-11-02T00:27:03Z (03:27:03 MSK), deployment completion,
not actual gameplay start. Planned offline / coop alone / paired route;
roles chosen by user, record actual segment times and collect both rotated logs.

## 2026-11-02 — FPS / stutter research build prepared

User requested matched offline/co-op FPS and long game-thread-hold investigation.
Standalone 666a03a, bundled d5a2322, port 02bf0f4. Native build and bundled DLL exit=0;
analysis fixture passed weighted windows/segment exclusion/missing capture.
Staging refreshed; bloodborne_pc/out/perf-research-delta.zip contains loader + mod delta.
No installation, game launch or settings/save changes. Runtime measurements PENDING.
New guest-flip telemetry default on (BB_PERF_CAPTURE=0 disables), five-second FPS,
frame histogram percentiles/counts and epoch timestamps for >50 ms frames.
BBSC reports rare >8/16/50 ms scope calls separately from top-ten cost.
Scope time is not proof of mutex hold; nested costs overlap. Timeline synchronous
flush under mutex is a candidate only. No measured improvement claimed.
Scenario and limitations: bloodborne_pc/docs/COOP-PERFORMANCE-RESEARCH.md.
Next: matched warmed route offline / coop alone / paired host+guest; record segment
times, collect both machines including rotated logs, correlate stalls with lifecycle.

## 2026-11-02 03:14 MSK — latest version WITH launcher installed on both machines

User requested new version together with launcher. Rebuilt launcher/package using
BB_FAST_DEPLOY=1 package.sh, exit=0; reused already-built current native binaries
(03:03, including d97ff1d window mouse recapture) and bundled d8741ed mod DLL.
Package includes current working-tree HomePage.qml. Port HEAD a1eecbb.
Both stopped machines: 5214 files copied, exit=0, backups saved; no file/hash/
manifest verification per fast preference. PC backup latest-with-launcher-
20261102-031338 under D:/Games/Bloodborne/coop-dev/backups; laptop -031405
under C:/Games/Bloodborne/coop-dev/backups. Settings/saves unchanged, game not
launched. Native quit restrictions runtime validation remains pending.
Build log bloodborne_pc/out/launcher-package-latest.log.

## 2026-11-02 03:11 MSK — native quit restrictions installed

User explicitly requests death-like character restriction with free camera,
not a pad input block. Pad filtering removed. Native death/leave pending,
menu brake and flag4047 held during confirmed exit; cancellation restores
prior values, real loading owns native reset. No HP/death penalty changes.
Standalone 17c3f99, bundled d8741ed, port pin a1eecbb. DLL build exit=0;
production menu_quit fixture PASS. Delta installed stopped PC/laptop: 5 files
each, copy exit=0; no file verification per preference. Backups quit-native-state-
20261102-031058 (PC D:/Games/Bloodborne/coop-dev/backups) and -031105
(laptop C:/Games/Bloodborne/coop-dev/backups). No game launch/save/settings edits.
Actual no-movement/no-menu/free-camera behavior PENDING user runtime check.
Prior pad-block success statements superseded by user's failed 03:00 run.
Review logs: bloodborne_pc/out/coop-dev/runs/quit-input-review-20261102.
Details: fixes/2026-11-02-quit-native-restrictions.md.

## 2026-11-02 02:58 MSK — quit input/loading installed on PC + laptop

Standalone 73f2847, bundled e98fbfd, port pin ae94f76. DLL build exit=0.
Confirmed Yes blocks pad buttons/sticks/triggers through save and native Stop.
At native session closure, open loading screen once before direct title request;
cancel restores input, title handoff releases pad so menu/Continue work.
Production menu_quit, quit_input, hook_resume PASS. Both stopped devices received
5 delta files, copy exit=0; file verification disabled per fast-deploy preference.
Backups PC D:/Games/Bloodborne/coop-dev/backups/quit-input-loading-20261102-025831;
laptop C:/Games/Bloodborne/coop-dev/backups/quit-input-loading-20261102-025837.
No game launch or save/settings changes. Runtime confirmation pending:
confirm Exit Game as host and guest, try movement/actions during disconnect,
expect loading immediately after session closure, then verify title/Continue input.
Logs both machines: bloodborne_pc/out/coop-dev/runs/menu-20261102-0248.
Details: fixes/2026-11-02-menu-input-loading.md.

## 2026-11-02 02:46 MSK — join world guard + shared key receipts installed

Standalone e368f45, bundled deae891, port pin 762c374. Bundled DLL build exit=0.
Production join destination/freshness/map/mount fixture and chalice scope PASS;
shared-key receipt and inventory barrier checks passed during preceding change.
Delta installed on stopped PC and laptop: 5 files each, copy exit=0,
file verification disabled per preference. Backups join-world-keys-20261102-024630
(PC D:/Games/Bloodborne/coop-dev/backups) and -024639
(laptop C:/Games/Bloodborne/coop-dev/backups).
Includes previous key fix; earlier unbuilt/uninstalled statements are historical.
No game launch, save/settings changes. Runtime validation pending:
join host already in chalice, exit/rejoin, host Dream-to-chalice follow,
then reload and check shared keys show only on first receipt.
Details: fixes/2026-11-02-chalice-join-wrong-world.md.

## 2026-11-02 — initial join cannot teleport between worlds

Evidence: keys-20261102-0231 laptop log, 02:35:38–42. Native summon
created the character in Dream (0x15000000), then join teleport moved it
from (-15.11,-5.11,-11.24) to dungeon host (39.86,31.50,-52.97).
At 02:36:16 guest died; recovery correctly refused in-place revive in the
wrong world. First follow at 02:34:36 had injected the loader and arrived
in m29; generic m29 missing optional resources also occur on host and do
not establish a loader failure.

Fix: require a fresh host follow map before using any remote transform.
World mismatch hands initial join to scoped follow without teleport.
Dungeon placement requires same map and mounted current revision/key.
Non-chalice adjacent resident blocks remain allowed within one area.
No changes to death policy, altars, saves or network protocol.
Production test_join_destination and test_chalice_scope PASS. Game validation pending.
Includes preceding shared-key receipt fix in the same pending DLL.

## 2026-11-02 — повторная выдача shared keys, прогон 02:30–02:37 МСК

Логи обеих машин: bloodborne_pc/out/coop-dev/runs/keys-20261102-0231.
На клиенте семь shared keys повторно показаны в 02:33:51, 02:34:39,
02:36:31. В 02:35:42 те же предметы восстановлены K2-trip без окон.
Причина: shared-key tick мог опередить ledger reconciliation текущей загрузки;
постоянная принадлежность проверялась по временному phantom inventory.
Дополнительно FinishBbscTripAtHome удалял receipts через 60 секунд дома/при join.

В исходниках обоих checkout: shared keys ждут BbscGuestLoadItemsReady;
receipt из сериализуемого per-user/per-slot trip journal означает полученный
предмет, восстановление без popup/новой записи Given. Shared-key receipts
сохраняются при FinishBbscTripAtHome; запись Key гарантированно попадает в journal.
Формат файла не изменён. Старые уже удалённые receipts восстановить задним числом
невозможно: при наличии предметов join снова фиксирует их в журнале.
Проверки test_shared_keys.py и test_load_readiness.py PASS (clang++).
Код не собран и не установлен, игровой результат pending. Живые сейвы,
настройки и metadata не менялись. Запуск игры не выполнялся.

## 2026-11-02 02:27 MSK — Stop/chalice routing installed on both machines

- Standalone `96db2f2`, bundled `e72801d`, port pin `3f079b9`.
- Bundled DLL build exit=0; target fixtures passed. Delta installed PC and laptop, 5 files each, both copy operations exit=0. No installed-file verification per fast-deploy preference; no game launch or save/settings changes.
- Backups: PC `D:/Games/Bloodborne/coop-dev/backups/stop-routing-20261102-022723`; laptop `C:/Games/Bloodborne/coop-dev/backups/stop-routing-20261102-022732`.
- Fixes: mount/register type collision; pre-load chalice-context gate; native Stop member drain bounded at 2 s; single cleanup owner; next-tick lock release; loading close once; no corpse fallback / wrong-world guest revive; readiness before uncovering. Details and scenario matrix: [stop-routing-fix](fixes/2026-11-02-stop-routing-fix.md).
- Runtime confirmation PENDING. 2 s bounds member drain, not the whole save/network/menu rendering. New `BBSC stop phase` records identify the remaining stages. First non-chalice claim/sign cadence (~31 s) remains OPEN; no claim that interval writes solve it. HTTP timeouts likewise not attributed to this issue.
- Deployment helper fixed to allow an explicitly enumerated mod-only delta ZIP without a full-package Bloodborne.exe; full-package guard remains for deployment without -Files.

## Прогон01:45–01:59 разобран — 02.11.2026, без правок кода

Continue/quest commit/inventory-before-fade подтверждены логами. Четыре выхода
0.58–0.80 s, два выхода guest12.95/17.05 s; поздний host quit5.66 s. Stop не закрыт.
Найдена точная коллизия0x2B: session-register перехватывает chalice-mount, затем
отвергает размер/версию. Чаши не монтируются. Guest recovery возрождает тело на
Y=-1500.17 и открывает cover, затем повторная смерть вынуждает настоящий reload.
Остаются поздние host leave locks, двойной cleanup и native loading UI после смерти.
Архив обеих машин+server: bloodborne_pc/out/coop-dev/review-20261102-0159.
[Полный разбор, времена и границы доказательств](fixes/2026-11-02-run-review-0159.md).

## Порядок кооп-событий установлен на обе машины — 02.11.2026, 01:43 МСК

Bundled1767a8d / standalone8e82daf / BBGL pinf259df9. DLL build exit0.
На остановленные ПК/ноут установлен mod delta: по5 файлов, без файловой верификации.
Бэкапы lifecycle-order-20261102-014341 (ПК D:/Games/Bloodborne/coop-dev/backups)
и lifecycle-order-20261102-014343 (ноут C:/Games/Bloodborne/coop-dev/backups).
Continue наблюдается через spawn-resolution, quit guard сбрасывается по готовности
мира; Stop сразу сопровождается native remote cleanup; accepted quit не отменяется
через30 s; home fallback не конкурирует с quit и ждёт1 s после завершения сессии.
Cover гостя ждёт inventory reconciliation текущего load generation. Ledger service
ограничен10 Hz с обходом на новую загрузку. Диагностика cleanup больше не лжёт при quit.
Целевые menu/load readiness/chalice/follow/home/trampoline/post-load fixtures PASS.
Правила смерти сохранены: boss spectate, вне boss немедленное revive. Гости следуют
за фонарём хоста, после ухода host идут домой. Код/деплой выполнены; игровой результат,
в особенности время Stop <нескольких секунд, ещё не подтверждён.
Сейвы/настройки/VPS не менялись, игра не запускалась.
[Матрица порядка и ожидаемое поведение](fixes/2026-11-02-lifecycle-ordering.md).

## Последние правки установлены на ПК и ноутбук — 02.11.2026, 01:06 МСК

Standalone 4873852 / bundled 80cae9b / BBGL pin 8494bbe. Полная сборка
build-coop-package.sh exit=0; Release payload and hygiene PASS.
На каждой машине заменено 9 файлов, проверено 5223, оба manifest PASS.
ZIP SHA256 C5D1577BB3D718E3D25F78C3081693A2B708C54880ED5AA65BC5ABC49CE9805D
проверен перед установкой на ноутбуке. DLL/launcher/native совпадают на обеих.
DLL 54F2683222CB6B9F6116439D439D76C4A799DACB6E09420BD36A4C40C347C965.
Native 191CF1D06C77CA9A3287200F790AE8F2D0BA2137AE21DCF70A1A0AF8CDB9A329.
Бэкапы: ПК D:/Games/Bloodborne/coop-dev/backups/joined-quit-20261102-010459;
ноут C:/Games/Bloodborne/coop-dev/backups/joined-quit-20261102-010520.
Сейвы/настройки не менялись; VPS не обновлялся. Игровое подтверждение pending.
Лог сборки: bloodborne_pc/out/joined-quit-package-build.log.
Предыдущие записи «исходники» ниже описывают этап до этого деплоя.
## Повторный призыв, блокировка хоста и позиция после меню — 02.11.2026, исходники

После JoinRoom/state6 знак гостя принудительно снимается с подбора; учтён
поздний create reply и повтор при сетевой ошибке. Starting/state4 не удаляется.
Host exit intent удерживает menu brake/load wait до native Continue, а не только
до state0. Native serializer получает исходные карту/позицию/поворот гостя,
привязанные к слоту; живой персонаж/сейвы вручную не перемещаются/не правятся.
Долгий выход: native Stop append FIFO подтверждён eboot; он ждёт текущую задачу.
Связь ~30 s с дублированным summon сильная, старого queue-head в логах нет;
добавлен его точечный лог. Не менять session state вручную и не увеличивать timeout.
Целевые lifecycle/menu/home/trampoline/bell tests и полная /Zs проверка PASS.
Bundled/standalone синхронизированы; не собирали/не устанавливали.
[Подробности и ограничения](fixes/2026-11-02-joined-claim-quit-origin.md).

## Гостям запрещены колокола призыва/подключения — 02.11.2026, исходники

По просьбе пользователя native goods-use result запрещает Зовущий (200,
effect 9000) и Малый звонкий (205, effect 9005) локальному гостю в state 4/6.
Запрет стоит перед native-yes/anywhere и работает независимо от опции anywhere,
для меню и быстрых слотов. Хост/соло, Бланк и PvP-переключение сохранены.
Целевой test_guest_bells исполняет production функцию с обоими значениями
anywhere, разными ролями, исходным native результатом и local/remote: PASS.
Bundled/standalone синхронизированы. Не собирали и не устанавливали.
Это не закрывает серверный повторный призыв уже вошедшего гостя хостом.

## Разобран прогон 00:25–00:35 — 02.11.2026, без правок

Обе машины на последней сборке; собрано с provenance, серверный journal сохранён.
Шесть комнат 109–114 успешно соединялись, шесть выходов завершились. Последний
выход ПК прерван ручным закрытием игры (уточнение пользователя), не считать зависанием.
Найдены: намеренная вторая cross-map загрузка (старый lighting workaround),
повторный призыв уже подключённого гостя из retained claim, 27.9 s native Stop
до вызова LeaveRoom и позднее повторное выставление leave locks хосту.
Связь долгого Stop с незавершённым повторным summon вероятна, точный timer/task
ещё не доказан. HTTP retry один раз сработал; общие TCP-тайм-ауты сохраняются.
Код/сборки/установки/сейвы не менялись. [Разбор](fixes/2026-11-02-run-review-0035.md).

## Выход с блокировкой управления и retry claim установлены — 02.11.2026

Bundled 6d8b109 / standalone 81524e4 / BBGL 7e8594f. Полная сборка
build-coop-package.sh exit=0, release payload/hygiene PASS. На закрытые ПК
и ноутбук установлено по 10 замен; 5223 файла проверены на каждой машине,
client/server manifests PASS. DLL, launcher и native exe совпадают со staging
и между машинами. Сейвы/настройки не менялись, VPS не обновлялся.
Бэкапы: ПК D:/Games/Bloodborne/coop-dev/backups/disconnect-stress-20261102-002324;
ноут C:/Games/Bloodborne/coop-dev/backups/disconnect-stress-20261102-002341.
DLL SHA256 AD0417E81096B4BF33105F82D65D5AAE695BD2ABE4AFE658DB07D3F89FC167A7.
Native SHA256 191CF1D06C77CA9A3287200F790AE8F2D0BA2137AE21DCF70A1A0AF8CDB9A329.
Игровой результат pending. Следующая запись «исходники» — исторический этап.
[Разбор прогона и правок](fixes/2026-11-02-disconnect-stress.md).

## Разрывы/повторный вход и блокировка выхода — 02.11.2026, исходники

Последний прогон собран с обеих машин и сервера: комнаты 105–107 успешно
соединялись после выходов и Blank; последняя 108 осталась пустой, потому что
claim POST не установил TCP-соединение и не дошёл до сервера. Это не прежняя
gонка signaling. В native HTTP добавлены максимум два безопасных повтора
только до отправки claim; причина самих TCP-тайм-аутов пока не установлена.
Перехват Yes перенесён до native save/stage flags; ожидающий выход закрывает
меню и блокирует управление, отмена сохраняет прежние значения блокировок.
Покрыты starting/leaving/failed и уход партнёра во время save. Целевые
menu/trampoline/transport fixtures и syntax check PASS. Не собирали/не ставили.
[Доказательства и границы](fixes/2026-11-02-disconnect-stress.md).

## Прогон 23:45–23:50 и исправление answerer — 01.11, установлено 23:56 МСК

Повторное подключение НЕ прошло. Архив investigate-20261101-2345 содержит
pc/laptop mod, pc-game, laptop-game-online (ротированный last_run.1.log), server.
Обнаружена регрессия предыдущей правки 0964480: новый входящий answerer штатно
начинает Inactive, а StartHandshakeInitiator стал отвергать его вместе с закрытыми.
Клиент создавал новый ID на каждом Offer, не начиная handshake; хост получил
30 s timeout 80552711. Это другой отказ, чем гонка established->pending.
BBGL 9f26442 разрешает новый Inactive, сохраняя защиту Established/dead_fired
и фильтр неактуальных queued activations. Production fixture дополнен этим
входящим сценарием и проходит. Полная сборка/упаковка exit0, release hygiene PASS.
Обе остановленные машины обновлены: по 9 замен, 5223 файла проверены,
client/server manifests PASS; native exe/DLL/launcher согласованы со staging.
Бэкапы answerer-fix-20261101-235512 (ПК), -235533 (ноут) в coop-dev/backups.
Native SHA256 B67E179AB0D2CD60000876F6A9BFF424826EFCF1D41916876A49634089108C87.
DLL SHA256 B8A57192D19682C7A0AD3EC9758DDF156F9E7AD5BECD8C18EDA43367803063CD.
Книга: native wait finished в 23:47:14.980, через 69 ms после Range rows1;
runtime-завершение ожидания подтверждено, визуальное подтверждение отсутствует.
Сейвы/настройки не менялись, VPS не менялся, игру не запускали.
Нужно игровое подтверждение подключения новой сборкой; общий баг не закрыт.
[Разбор](fixes/2026-11-01-activation-race.md).
## Книга и гонка активации — 01.11.2026, установлено 23:43 МСК

BBGL 0964480, bundled 9d992e8, standalone 63b789f. Найдены две ошибки:
- Ranking+2858 — first rank (начальное 0), а не board index 19. Старый guard
  блокировал закрытие плашки; fixture повторял ошибочное предположение.
- Отложенная signaling activation после ResolvePeer могла понизить уже
  ESTABLISHED до PENDING, не очистив established_fired. Повторный CheckAck
  не восстанавливал статус. Теперь текущее состояние проверяется повторно
  диспетчером и под mutex внутри StartHandshakeInitiator.

Новый production-code fixture детерминированно падает на прежнем сетевом коде
и проходит на исправленном; книга проверена с native initializer/predicate и
production trampoline, включая 1/2/5 rows. Provider fixture PASS.
Добавлена ограниченная диагностика четырёх native причин закрытия signaling.
Полная сборка (мод+порт+сервер), packaging/release hygiene PASS, exit=0.
На обеих остановленных машинах replaced=10, verified=5223, manifests PASS;
DLL/launcher/native exe совпадают. Бэкапы activation-race-20261101-234156 (ПК)
и activation-race-20261101-234226 (ноут) в соответствующем coop-dev/backups.
DLL SHA256 BD2430C4E850E0BAF114D0520E957847621E3160FC5BD069CCF3ED31BDDCC689.
Native SHA256 2DC04D463B8C67B43A8CC7AC1C05944F521347055A57D0FD13EDFEA37E3EDA71.
Сейвы/настройки не менялись, игру не запускали. Игровой результат pending.

Следующий пользовательский прогон: открыть/закрыть/снова открыть книгу;
подключить клиента из Сна к хосту в Кейнхерсте; выход гостя в меню и повторный
вход без перезапуска. Зафиксировать роли и время; проверить исчезновение
плашки, загрузку клиента к хосту и повторный вход. Не считать баги закрытыми
до результата пользователя. Сервер VPS не менялся.

Подробный разбор и предложение server event coordinator (НЕ реализовано):
[activation-race](fixes/2026-11-01-activation-race.md).
[Книга, исправление неверной трактовки поля](fixes/2026-11-01-register-loading-dialog.md).
Полные game-логи прочитаны: путь ПК оказался Bloodborne Game Launcher d/twin.
Уточнение к ранней диагностике: успешный архив показывает JoinRoom через 235 ms
после claim без промежуточного delivered create. HTTP polling не является
единственным путём; нельзя объявлять поздний create первопричиной отказа.
## Последние правки установлены на обе машины — 01.11.2026, 22:15 МСК

Bundled d6fb46a / standalone 2aa8c80 / BBGL pin bc56094: прямой выход в главное
меню и предшествующая правка плашки загрузки книги (8fbb19e) собраны и установлены.
Полная сборка build-coop-package.sh exit=0, release payload/hygiene PASS.
ПК: 9 замен, ноутбук: 14; на каждой машине 5223 файла сверены со staging,
client/server manifests PASS; DLL и launcher SHA256 совпадают между машинами.
DLL SHA256: F22A29CA354C2C5358F6C4EB38A9FE6051D341EBEDAC42DC5C0940DB2935B8F5.
Резервные копии: ПК D:/Games/Bloodborne/coop-dev/backups/menu-exit-20261101-221301;
ноут C:/Games/Bloodborne/coop-dev/backups/menu-exit-20261101-221339.
Игры/лаунчеры были закрыты, сейвы/настройки не менялись, игровой результат pending.
Эта запись заменяет статусы «только исходники» и «книга без деплоя» ниже.
[Разбор выхода](fixes/2026-11-01-menu-exit-extra-load.md).

## Лишняя загрузка при выходе — 01.11.2026, только исходники

Выход через System menu теперь после успешного native save и отключения вызывает
OnReturnTitle (event request 2), вместо возобновления MenuMan+250 — триггера
world-stage transition. Покрыт state 0: хост после ухода гостя раньше обходил hook.
Целевой test_menu_quit PASS; bundled/standalone синхронизированы.
Не собирали и не устанавливали; игровой результат pending.
[Разбор и границы доказательств](fixes/2026-11-01-menu-exit-extra-load.md).

## Плашка загрузки книги: исправлено и собрано, без деплоя — 01.11.2026

Пользователь подтвердил открытие книги и список участников, но долго остаётся
«Получение регистрационных данных». Bundled 8fbb19e / pin 09ea94c:
native predicate ждёт готовности реальных строк сессии, игнорируя пустой хвост.
Проверка на настоящем native predicate и production trampoline PASS,
provider fixture PASS, DLL build exit=0. По просьбе пользователя НЕ установлен;
ПК и ноутбук остаются на 91c8743. Визуальная проверка исправления pending.
[Нативная цепочка и границы проверки](fixes/2026-11-01-register-loading-dialog.md).

## Ноутбук обновлён для PvP и книги — 01.11.2026 21:27 МСК

Ноутбук найден в новой LAN: 192.168.1.166, DESKTOP-73Q9JB7; прежний SSH host key
подтверждён строго. Навык ssh-my-devices обновлён, SSH-конфиг не менялся.
Bundled 91c8743 установлен на закрытый ноутбук; SHA256 DLL совпадает с ПК:
9DB925B08B82BBC182EB0BD8E3DE52B701703E1D68C6092A14D852379C44EF76.
Client manifest и метаданные UTF-8 без BOM PASS. Бэкап ноутбука:
C:/Games/Bloodborne/coop-dev/backups/session-register-20261101-212740.
Это заменяет прежний статус «ноутбук отложен». Сейвы/настройки не менялись;
обе машины готовы к пользовательскому прогону, игровое подтверждение pending.
[Описание проверки](fixes/2026-11-01-pvp-dregs.md).

## Сгустки за добивание и книга подношений — 01.11.2026 20:01 МСК

Bundled 91c8743 / pin 6c75ad9: книга ранжирует до пяти участников своей сессии
по native числу сгустков, преподнесённых Королеве (+0xE8), включая нулевых.
PvP: 704 получает только автор смертельного попадания, с native HP до/после,
room/member identity, подтверждением доставки и подавлением повторов.
Исправлен цикл пустой страницы книги; board 20 обслуживается локально.
Целевые fixtures и DLL build PASS; установлено только на закрытый ПК,
SHA256/manifest PASS. Ноутбук отложен по просьбе пользователя, остаётся старым.
Новый сетевой игровой прогон pending; всем участникам нужна новая DLL.
[Детали и границы проверки](fixes/2026-11-01-pvp-dregs.md).

## Книга Нечистокровных: первый прототип — 01.11.2026 17:24 МСК

Bundled c11d31c / pin 4b1a44c: родной Ranking открывается из книги 130,
провайдер подаёт сетевые имена и уровни текущей группы, место по уровню.
Книга добавлена к комплекту после блокнота. Целевые fixtures и DLL build PASS;
установлено на закрытые ПК и ноутбук, DLL SHA256/manifest/UTF-8 без BOM PASS.
Карточки экипировки нет, подписи штатные; native UI требует игрового подтверждения.
[Разбор цепочки и ограничения](fixes/2026-11-01-session-register.md).

## Колокола в уведомлении блокнота — 01.11.2026 16:23 МСК

Bundled 9616dd9 / pin 5097954: при успешном получении блокнота отсутствующие
оригинальные колокола добавляются в ту же native очередь уведомлений.
C++ fixture реальной функции выдачи PASS, DLL build exit=0. Установлено на
закрытые ПК и ноут с бэкапами notebook-popup-20261101-162309 / -162320.
DLL SHA256 совпадает, полный client manifest и UTF-8 без BOM PASS.
Визуальный список/порядок строк и подбор блокнота требуют игрового подтверждения.
[Подробности](fixes/2026-11-01-notebook-popup.md).

## Ноутбук обновлён — 01.11.2026 16:05 МСК

Оригинальные кооп-предметы d659347 установлены на закрытый ноутбук.
DLL SHA256 совпадает с ПК; полный client manifest PASS. Бэкап:
C:/Games/Bloodborne/coop-dev/backups/original-bells-20261101-160501.
Игра не запускалась, сейвы и настройки не менялись. Игровую проверку выполняет пользователь.
Эта запись заменяет статус «ноутбук не обновлён» ниже.

## Оригинальные кооп-предметы — 01.11.2026

Четыре оригинальных goods, выдача после блокнота; отдельный Duel Bell убран.
Bundled d659347: целевая C++ проверка и DLL build PASS, установлен на ПК с
бэкапами, SHA256/client manifest PASS. Ноутбук не обновлён. Игровой контроль pending.
[Подробности](fixes/2026-11-01-original-coop-items.md).

# BACKLOG — актуальный план кооп-мода

Актуализирован 30.10.2026 по T6–T17, истории коммитов и сообщению пользователя:
практически все критические игровые баги исправлены. Основная следующая задача — **чаши**.
T19: пользователь подтвердил прохождение чаш в кооперативе; два остатка входа исправляются T21. Общее подтверждение пользователя
не означает отдельной проверки каждого редкого сценария.

Исходная установленная сборка: T17, `addfd08`, на ПК и ноутбуке.
T19 `c00fa6c` собран и установлен на ПК/ноут — автоматический вход, [код/проверки/границы](fixes/T19-chalice-follow.md);
порт с исправлением signaling `f4f0028`. Подробности окружения — [HANDOFF](HANDOFF.md).
Старый накопительный список сохранён в [истории](history/BACKLOG-2026-10-30-before-review.md).

Статусы: **подтверждено** — есть конкретный результат игры/логов;
**исправлено, контроль** — код и деплой есть, полной игровой проверки нет;
**исследование** — риск или гипотеза, а не доказанный текущий баг.

T20: [ускорение поиска и лимит колокола 5 мин](fixes/T20-matchmaking.md), BBSC `7967976`, порт `b325d1e`.
Установлен на ПК и ноут 30.10 в 21:31 МСК по просьбе пользователя, **без отката сейвов**; игровой контроль ожидается. Событийный брокер пока не реализован.

T21 `d194560`: два исправления входа в чашу, шесть наборов проверок PASS, build exit=0.
Установлена в 21:59, пользователь подтвердил оба исправления.
T22: новый остаток боевого урона; измерительный порт `6672649` установлен на обе машины
в 22:26, требуется короткий бой для локализации задержки. Боевой HP/AI не менялись.

## T25: ключи после загрузки гостя (31.10.2026)

По двум логам друзей (`013312-17200`, `043233-9232`) подтверждены потери
предметов при native reload. В `TickBbscSharedKeyItems` маска `last_applied`
переживала загрузку: повторная выдача ключей/жетонов/инструментов пропускалась.
Теперь маска сбрасывается по `bbsc_load_generation`; выдача ждёт готовности Lua,
отсутствия loading и 3 секунд стабилизации. Неуспешный AddItem не отмечается
успешным и повторяется не чаще раза в секунду. Сборка DLL: exit=0; diff --check
чистый. Тесты и игровой контроль не проводились; сборка не установлена.

Остатки из этих логов: скачки определения слота по mtime (0/1 и 2/3),
завершение загрузки без снимка флагов хоста, незавершённый join и проваливания
через лифт. Причины невидимости и лифта не доказаны; изменения в эти пути не внесены.

## Ближайшая работа

T24: повтор PT-2/PT-9 — после смерти хоста первым клиент загрузился живым,
но остался наблюдателем. По логам исправлен пропуск загрузки между игровыми
тиками через существующий native ReloadFinish; 18 recovery сценариев PASS,
perf policy PASS. [Разбор и игровой контроль](fixes/T24-wipe-spectator-camera.md).

| Приоритет | Задача | Что осталось / критерий завершения |
|---|---|---|
| P0, контроль | T23: возврат из чаши / сейв ноутбука | Host: после сетевого сбоя native state 7, OwnWorldStep повторяется >1 мин. Пробел снятия persistence исправлен `e8994b1`, установлен; конкретный pending task не установлен. Ноут восстановлен из своего `chalice-test-20261030`, 16 SHA256 PASS, плохая копия сохранена отдельно. Проверить игровой вход и возврат. [T23](fixes/T23-chalice-return-and-save.md). |
| P1, главный этап | CH-1: кооп в чашах | Прохождение и оба исправления входа T21 подтверждены пользователем. Новый боевой остаток: удар клиента регистрируется через 2–3 с, у хоста тоже. T22 измеряет native отправку/доставку/чтение; причина ещё не доказана. Затем layer ID, постоянный ID ритуала и расширенное покрытие. «Сейв тест чаш» сохранён на обеих машинах. |
| P0 при повторении | PT-3: GPU TDR | nvlddmkm / LiveKernelEvent 141 воспроизводился и Offline без BBSC, с DLSS/FG OFF. После чистой переустановки своей сборки первый переход в Сон успешен. Повторить маршрут Сон → обратно и выход в меню; устойчивое исправление и причина пока не доказаны. [T17](fixes/T17-event-work.md). |
| P0, контроль исправлений | PT-2/PT-9/PT-12 + T14: смерть и восстановление | T6 подтвердил базовые вайпы, затем были регрессии и исправления T9/T11/T14. Один контроль: оба порядка смерти на боссе, одновременная смерть вне босса, выход домой → лампа и колокол → повторный призыв. В T17 есть предупреждение NowLoading state=3 >30 с, видимый софтлок не сообщался. |
| P1, контроль исправлений | PT-1: ключевые после повторного призыва | T6 подтвердил базовый сценарий, T8 исправил новый вход с фантомной сумкой. T17: шесть goods восстановлены после загрузок, два вида сохранены после краша хоста/возврата. Проверить цепочку новый призыв → загрузка → домой → меню → новый призыв; инструменты мастерской, руны/самоцветы и ключи без дублей. |
| P1, покрытие | Три игрока и обрывы | Выход одного гостя при живом/мёртвом хосте: остальные продолжают; не остаются фантом/камера/неверное число живых и scaling. T8 удаляет life-запись по EOF; привязка relay sender к native member для адресной очистки копии остаётся задачей. Молчаливый обрыв сети проверить отдельно от закрытия процесса. |
| P1, покрытие | NPC и свой прогресс | Личные награды только за свой разговор, два одновременных разговора, разные квестовые стадии. PT-5 («Нечистота») и PT-14 (ранняя белая лента) решены: пользователь подтвердил 30.10. Для остальных NPC-наград остаётся покрытие. |
| P1, покрытие | Свой Сон, Shared Progress, DLC | Свой Сон выбран и реализован; проверить разные стадии Куклы/магазинов, покупки и сохранение. Shared Progress ON/OFF: квесты, ночь, боссы, лифты/рычаги после возврата и перезапуска. DLC: призыв, переходы и босс; полного покрытия нет. |
| P2, контроль | T11/T15/T16: загрузки и взаимодействия | Обычный лут/закрытый сундук, NPC после reload, отменённый/неудачный призыв с закрытием NowLoading, граница Соборный округ ↔ Ярнам без повторных follow; новая поездка хоста всё ещё вызывает follow. Код раскатан, отдельные результаты не записаны. |

## Что можно считать сделанным в проверенных сценариях

| Тема | Основание и границы |
|---|---|
| PT-5, PT-14, PT-10, инструмент рун у друзей | **Решено, подтверждено пользователем 30.10.2026:** «Нечистота», ранняя белая лента, появление в клинике и восстановление инструмента рун на сейвах друзей. Не включать в оставшийся контроль без нового сообщения о регрессии. |
| LA-1/GI-2, WS-2/WS-3: слот сейва и журналы на диске | `566cf7d`, тест 29.10: восстановление после краша. T17: восстановлены 960 групп своего мира и 18 talk-флагов. |
| PT-7/WS-5: стук в окна; PT-11: камера мышь/клавиатура/стик | Конкретное подтверждение пользователя T6. Не означает проверки всех NPC-событий. |
| PT-15: дверь после собаки; ранняя красная лента | Пользователь подтвердил после T7; [T8](fixes/T8-rejoin-quit.md). |
| Дубли обычного дропа | `d2e3ad4`, тест 29.10 №2: дубля нет. |
| Базовые предметы/вайпы у лампы | T6, `e40ede7`, пользователь + логи. Последующие расширенные пути восстановления — в контроле выше. |
| Уход хоста при краше и возврат гостя с предметами | T17: EOF, возврат домой, восстановление мира и предметов подтверждены логами. Лампа/колокол после этого отдельно не подтверждены. |
| PT-4: старая заглушка с логотипом | Устранена в тесте 29.10 №2. Позднее T11/T15 вернули штатный NowLoading для призыва — его завершение требует отдельного контроля. |
| PT-13: ?ActionEventInfo? | Фильтр исправлен в T11, раскатан; визуальное подтверждение не записано. Косметический остаток, не блокер чаш. |
| WS-1: защита своего прогресса чаш | `566cf7d`: область 29 исключена из Shared Progress. Это защита от слияния чужих чаш, а не готовая поддержка бесшовных подземелий. |
| Запуск signaling | `f4f0028`, T12: исправлен deadlock, порт установлен на обеих машинах. T13: отдельный отказ подключения из-за исчерпания UDP-портов MSI Center; перезапуск освободил порты. |
| Снижение диагностической нагрузки | T10/T17, сборки/автотесты/деплой проверены, Research OFF. T17: медиана ПК 59.7 игровых тиков/с, 1.474 мс BBSC; ускорение без сравнимой базы не измерено. |

## Важное, что нельзя потерять перед релизом

- PT-8: жест «отдёрнуть плащ» в инвентаре — вероятный след старой выдачи; проверить на чистом персонаже. Низкий приоритет.
- Исследовательские кандидаты из [FINDINGS](study/FINDINGS.md): загрузка без полного снимка флагов (SN-08/WS-6/WS-7), OR-слияние переключаемых состояний (WS-9), изоляция/доверие relay (SN-02), устаревшие ключи хоста (WS-4). Нужна актуальная перепроверка кода/конфигурации; не выдавать гипотезы за текущие игровые баги.
- Лаунчер: контроль совместимости override нашей DLL при обновлении пакета (LA-3), ограничение роста бэкапов (LA-2/GI-3), чистая установка и восстановление. Свою сборку не заменять upstream. Исходники и воспроизводимый пакет — перед публичной раздачей; push только по просьбе.
- Хост-миграция не запланирована; завершение хоста возвращает гостей в свои миры. Нужна понятная обработка недоступного сервера и его перезапуска.

## Порядок завершения

1. Короткий контроль GPU/смертей/предметов на текущей T17 на копиях сейвов; при отсутствии повторов перейти к чашам, не откладывать их ради косметики.
2. Фиксированная Птумеру от ритуала до следующего слоя; затем идентичность и изоляция двух разных подземелий, корневые чаши и возврат после обрыва.
3. Один объединённый прогон трёх игроков, личных NPC-наград, Сна/DLC и длительного прохождения; закрывать пункты по конкретным результатам.
4. Чистый релизный пакет своей сборки, совместимость версий, бэкапы/восстановление, инструкция с оставшимися ограничениями.

## Startup TXT gate removed (31.10.2026)

`f9447b4`: removed the blocking LICENSE.txt / NOTICE.txt / SUPPORTERS.txt
content check from the DLL. Missing or modified companion notices no longer
disable BBSC or show a startup error. Packaging license files are unchanged.
## Launcher profile layout (31.10.2026)

BBSC_DATA_DIR redirects mod logs, persistent journals and bbsc-launch.ini into the
launcher's AppData profile. Binaries remain in the launcher installation. Without
the variable the standalone BBSC layout remains compatible. Build and local profile
checks accompany the launcher ZIP; no deployment or gameplay test is implied.

## Native menu exit follow-up (01.11.2026)

Guest staying connected in title / delayed disconnect after Continue: Lua-only
exit hooks missed the native confirmation path. Implemented save-gated native
menu exit, with both global and per-viewport results deferred until successful
native save completion; failures cancel the exit. See
[implementation and checks](fixes/native-menu-save-exit.md). DLL build and
production-fixture/trampoline/post-load checks PASS; deployment and gameplay
confirmation are pending.

01.11 02:58 follow-up: 02:47 laptop logs showed the generic-dialog hook was
never called. Corrected to actual System Exit Game Yes callback (01C0D0C4,
MenuMan+250), traced from the port's real row opener and relocated vtable.
Targeted fixture/build passed; corrected DLL installed on both PCs. See
[updated native-menu notes](fixes/native-menu-save-exit.md). Gameplay pending.

01.11 03:03 run confirmed by user and logs: client native save succeeds before
disconnect; title released after state 0, own world and 8 quest flags restored,
taken-item record retained, no save errors or delayed kept-session cleanup.
Native menu exit is confirmed in this two-player scenario; see
[run evidence](fixes/native-menu-save-exit.md).
