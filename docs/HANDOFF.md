## 03.11.2026 — resident summon queue completion; ready for build

Latest17:44 run still blocks next guest despite open role mask. P2/P3/P1 finally
show3 actors at17:54:50 after a long delay with first guest still present. Added
host-only native identity-bound completion18777D00 for an already created,
arrived6/6 cooperative insertion task and matching live actor/full user+character
identity. Original destructor/unlink/count/backoff own completion; unfinished and
foreign requests remain. Corrected queue diagnostic to SosStatus[rbp-6F0], not
candidate manager. Direct queue removal/parallel-request bypass rejected: native
has one active request/result context and live+queued admission reservations.
Production policy + exact native completion and gate fixture PASS, five roles,
unrelated pending retained,21 rejection cases; full game TU syntax PASS.
Build/deploy/gameplay pending. See fixes/2026-11-03-resident-summon-request.md.

## 03.11.2026 — 17:16 second guest review: residual native co-op masks

Individual joins and Blank host release confirmed in the new run, but a waiting
second guest gets no claim until the resident guest leaves, across all host roles.
Fixed two missing FIVE_HUNTERS covenant co-op masks at01873086/018793B9; original
native executable blocks reproduce the residual exclusion and pass with actual
production patches (both paths,256 slot combinations, other role bits preserved).
Added change-only slot/ready-mask/queued-count observation; historical logs lack
these fields, so contribution to the live block is not yet proven. Capacity,
readiness and cooldown retained. Targeted mask/cooldown/matchmaking tests and
full BBSC_MOD TU syntax PASS. Source only; no new build/deploy/launch.
See docs/fixes/2026-11-03-second-guest-slot-masks.md. Three-player entry remains open.

## 03.11.2026 — serverless-party, эксперимент подготовлен к игре

Отдельный parent worktree `bloodborne_pc-serverless-party`, ветки
`experiment/serverless-party` родителя и подмодуля. База 572e066/151e24c +
скопированные локальные правки, исходные деревья сохранены; чужие правки
не включены в коммиты эксперимента. Протокол unanimity + durable journal,
независимые процессы, embedded compatibility в существующем runner BBGL,
нативные bell gates до side effects, сохранённый direct VPN UDP.
10 сценариев процессов, adapter/WinHTTP/trampoline/menu-exit проверки PASS;
DLL и frozen launcher build exit=0. Отдельные тестовые установки ПК+ноут,
копии start-clinic-teststart, LAN invitation; основные сейвы/установки/VPS/
роутер/firewall не менялись. Игры не запускались, **игрового подтверждения нет**.
Сценарий, пути и границы: [отчёт родителя](../../../docs/experiments/serverless-party.md)
и [протокол](../experimental/party/PROTOCOL.md). ACK сетевого компонента не
означает exactly-once применение игровых эффектов после краша; VPN/NAT между
разными провайдерами и каталог чаш ещё не проверены/не перенесены.

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

## Исправлена кодировка метаданных на ноутбуке — 01.11.2026

После deploy Windows PowerShell 5 записал client/bundle.json и SOURCE.json с BOM.
Строгий JSON reader лаунчера (UTF-8) такой файл не принимает. Оба файла с бэкапом
перезаписаны UTF-8 без BOM; чтение скачанного manifest штатным json.loads/read_text
PASS, все hashes client manifest PASS. Игру не запускали; повторный запуск проверяет пользователь.
При следующих деплоях JSON писать через UTF8Encoding(false), не Set-Content -Encoding UTF8 на Windows 10.

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

# HANDOFF — актуальное состояние на 30.10.2026

> **T23:** у хоста возврат из чаши застал session state 7 после сетевого сбоя;
> OwnWorldStep зациклился, точная ожидаемая задача неизвестна. Исправлен пропуск
> снятия persistence при native leaving, включая load-step fallback.
> Мод `e8994b1` собран/установлен на ПК и ноут, 7 проверок и 12 SHA256 PASS;
> [причина, границы и сейв](fixes/T23-chalice-return-and-save.md). Нужен игровой контроль.
> Ноут **восстановлен** из собственного `chalice-test-20261030`: 14 save + 2 metadata
> SHA256 PASS. Проблемная копия сохранена в `coop-dev/saves/before-t23-chalice-load-20261030`.
> Сейв ПК и исходные снимки не менялись. Порт остаётся T22 `6672649`.

> **T21 подтверждена пользователем:** прямой призыв в чашу и вход из Сна работают.
> Новый остаток: урон клиента мобам в чаше регистрируется через 2–3 с, у хоста тоже.
> [T22 — измерение задержки](../../bloodborne_pc/docs/coop-combat-latency.md), порт `6672649`.
> Причина/исправление урона пока не установлены. Измерительный порт `6672649`
> собран и установлен на ПК/ноут в 22:26 МСК (SHA256 `AEF3575C0B1C55CECB3779B8F156B091AAE4437BC8C3707ABDD13A91CF56D6DB`, обе проверки PASS).
> Тесты: bounded capture/Windows sink и 540 настоящих UDP доставок PASS. Мод T21 не менялся;
> не откатывать сейвы и не объявлять урон исправленным до результата прогона.

> **Обновление 21:59 МСК:** по просьбе пользователя T21 мода `d194560` и сетевой диагностический порт `030b2f3` установлены на ПК/ноут. 14 SHA256 PASS. Сейвы и настройки не изменялись. Старые записи ниже об отложенной установке относятся к прежнему состоянию. T20 подключение и лимит 5 минут подтверждены пользователем; причина одностороннего freeze пока не установлена. Новое сглаживание движения не реализовано.

> **30.10, уточнение пользователя:** «Нечистота», ранняя белая лента, появление в клинике
> и инструмент рун на сейвах друзей **решены**. Старые записи ниже — история, не открытые баги.
> T19: [автоматический вход в чашу без выхода из сессии](fixes/T19-chalice-follow.md).
> Пользователь подтвердил прохождение чаш в коопе. T21 исправляет два остатка:
> [прямой призыв в чашу и промежуточную загрузку Сна](fixes/T21-chalice-entry.md).
> Для прогона пользователь выбрал текущие testHost/test и создаст чашу в игре; откат не нужен.

> T20 `7967976` + порт `b325d1e` установлены на ПК/ноут 30.10 в 21:31 МСК.
> [Поиск/лимит колокола](fixes/T20-matchmaking.md), 14 SHA256 PASS; сейвы и настройки не тронуты.
> Игровой контроль ожидается.

> **«Сейв тест чаш» сохранён отдельно на обеих машинах:** `chalice-test-20261030`.
> [Точные пути и состав](fixes/T21-chalice-entry.md#сейв-тест-чаш--сохранить-для-будущих-прогонов).
> Не перезаписывать и не откатывать автоматически. T21 `d194560`: установлена
> 30.10 в 21:59, пользователь подтвердил оба сценария входа. Сейвы не менять.

**Основной план:** [BACKLOG](BACKLOG.md), этапы и чаши — [PHASES](PHASES.md).
По сообщению пользователя практически все критические баги исправлены; основной следующий
этап — чаши. Ревизия документов не заменяет отдельного подтверждения редких сценариев.

- Исходная установленная версия: **T20 `7967976` + порт `b325d1e` на ПК/ноут**.
  T19 runtime bridge подтверждён пользователем: чаши проходятся в кооперативе;
  прямой вход/двойная загрузка исправляются T21.
- ПК: чистая переустановка своей сборки, совпадающей с ноутом, выполнена 30.10 около 16:50.
  Первый последующий переход в Сон успешен. Прежние TDR воспроизводились также Offline
  без BBSC и с DLSS/FG OFF; причина не установлена. Нельзя объявлять GPU-проблему закрытой по одному успеху.
- T17: гость после краша хоста вернулся домой, восстановлены свой мир/квестовые флаги и предметы.
  Это конкретное подтверждение recovery, но не проверка всех вайпов, лампы/колокола и трёх игроков.
- Чаши: базовый кооп подтверждён; T21 — два сценария входа. Persistent ritual ID,
  точный layer ID, разные генерации/обряды и три игрока остаются в покрытии.
- Тестовые user_dir: ПК `D:/Games/Bloodborne/testHost`, ноут `C:/Games/Bloodborne/test`.
  `ddd` — прохождение с друзьями; без просьбы не откатывать. Снимок ПК «в лесу» — `forest-host`.
- Использовать свою сборку лаунчера; не заменять upstream. После успешной сборки раскатывать
  на остановленные ПК/ноут автоматически; работающую игру не завершать. Откат сейвов — отдельная просьба.
- Сначала проверить вход в восстановленный слот ноутбука и возврат хоста из
  чаши в Сон. Затем вернуться к трём ударам клиента T22; боевой тест не состоялся.

## История сессий (ниже — не текущий план)

Записи сохранены как доказательства. Старые «не раскатано», «ждёт теста», список
коммитов/путей и ближайшие задания действуют только на момент соответствующей сессии.
Для текущего статуса использовать таблицы BACKLOG и PHASES выше.

### Предыдущая сводка

> **Launcher source preference:** use the user's own build (as on laptop), never
> replace it with upstream unless explicitly requested. Independent fork planned.
> PC clean reinstall completed 30 Oct 16:50: 5102 laptop-matched runtime files,
> T17, mods/settings/saves preserved; old folder backed up. See [T17](fixes/T17-event-work.md).


> **T17 deployed PC + laptop:** event-driven reward/drop/cutscene/departure
> notifications, numeric scaling/cache and research-only diagnostic scans (`addfd08`).
> Build exit=0, zero warnings; 12 deployed-file hash checks PASS; concurrency,
> scaling and existing recovery/follow checks PASS. Research OFF, saves unchanged.
> User reports gameplay generally works. Run 20261030-161747: PC crash coincides
> with nvlddmkm 153 + WER LiveKernelEvent 141/Blackwell at 16:27:49; GPU TDR
> confirmed, root cause unresolved. Guest returned home and retained trip items.
> PC median 59.7 game ticks/s; no matched baseline for speedup. See [T17](fixes/T17-event-work.md).


> **T16 deployed PC + laptop**: consume host arrival after sharing map, preventing repeated
> follow loads on Cathedral Ward border. Code c75b1d6, tests PASS, build exit=0.
> Host crash confirmed Windows GPU TDR 141/nvlddmkm Blackwell, not fixed by this patch.
> See [T16](fixes/T16-follow-border.md). Saves unchanged.

> **T15 deployed to PC + laptop**, override and active-package hashes verified.
> See [T15](fixes/T15-loading-and-NPCs.md). Gameplay confirmation pending.
> **User preference:** after future fixes and successful builds, deploy immediately to
> PC/laptop where the game and launcher are stopped. Do not terminate running games;
> report devices skipped. Save rollback still requires a separate request.


> **T14, 30 October: post-load/session recovery deployed to PC + laptop by user request.**
> Latest laptop log confirms dead guest after wipe load, then home state=0/own_world=1
> with phantom type=1 (bell rejected player type). Cancel kept-death override before
> teardown; reconcile local character/camera after completed loads independently of
> remote creation; normalize phantom at home; dead/missing guests can return home.
> Override and active-package hashes verified on both machines. No save/settings changes.
> All 15 fixture scenarios pass; final mod build exit=0, no warnings.
> Code `8ff3435` + `7ed971b`. Details/hash in
> [T14-post-load-recovery](fixes/T14-post-load-recovery.md); gameplay confirmation pending.


> **T13, 30 October: join failed because MSI Center exhausted PC UDP ports.**
> User-authorized MSI Center restart freed 16,308 sockets; game STUN now reaches
> VPS as twin:3658. Retest join. Laptop crash separately confirmed nvlddmkm TDR/
> LiveKernelEvent 141 with upscaler/FG OFF; cause unresolved. No new code deployed.
> See [T13-connect-and-laptop-TDR](fixes/T13-connect-and-laptop-TDR.md).

> **T12, 30 October: PC startup fixed in PORT f4f0028, installed/verified on PC + laptop.**
> Signaling initialization rollback deadlocked joining a dispatch worker while
> owning its mutex. Removed unused ioctl socket; release lock before workers.
> T11 DLL + Research OFF reaches title menu; left running, no world loaded.
> See [T12-startup-signaling](fixes/T12-startup-signaling.md).

> **T11, 30 October: build 8373921 deployed/verified on PC + laptop; Research logs OFF.**
> PC restored forest-host (testHost, slot 1); current PC save subsequently copied to laptop test by user request (19 files verified, including journals).
> Host-first wipe spectator cleanup, resolved banner draw filter, native chest
> availability and immediate native summon loading screen. See
> [T11-test-regressions](fixes/T11-test-regressions.md). T10 test had Research logs
> enabled (168/168 hooks); production trace reduction was not exercised.

> **T10, 30 October: performance/notification audit, deployed to PC + laptop.**
> Diagnostic-only hot hooks are opt-in; obsolete boss-banner transport removed;
> reload-safe param slot cache, dead shop guard removed, personal-event policy
> unified. Keep connection/departure and PvP notices. See
> [T10-performance](fixes/T10-performance.md). `d101121`: mod build exit=0, zero warnings;
> regression checks passed. Deployed/verified on PC + laptop by user request; gameplay/FPS verification pending.

> **T9, 30 October: boss wipe regression confirmed in logs.** Client watchdog revived
> in place at 01:07:12, before PartyGhostDeath_2 at 01:07:13; no full client reload.
> Unified watchdog/native death state, latched boss-at-death, actual load-generation
> check, HUD cleanup after reload/return home. See `docs/fixes/T9-boss-wipe.md`.
> Code `12984a9`: build exit=0; deployed/verified on PC and laptop. SHA256
> `68943CD98A535BCEB9771F5B5DB9FCFC3DD696EDA50747D5ABECD1DE23F514AF`.
> Gameplay confirmation pending. Current saves and `forest-host` remain untouched.

> **Запомненный сейв «в лесу» (30.10):** снимок **`forest-host`** на ПК,
> `D:\Games\Bloodborne\coop-dev\saves\forest-host`.
> Источник — `testHost`, активный слот **1 по BBSC**; хост в **Запретном лесу**,
> лампа **2702950**. По просьбе «откати к сейву в лесу» использовать именно этот
> снимок на ПК, не `start-clinic-teststart` и не `before-amelia-host`.
> Сохранены весь SPRJ0005/метаданные, bell-pending и item-ledger; 14 файлов сверены,
> SHA256 — `forest-host/sha256-manifest.json`. Ноутбук не откатывался.
>
> **Контроль без FG:** пользователь сообщил, что игра шла нормально, но выход хоста
> в меню снова завершился крашем. В 00:42:52 — nvlddmkm 153, WER 141 / Blackwell,
> `frame_gen=off` подтверждён в ini; DLSS upscaler остаётся включён.
> Поэтому FG не является необходимым условием наблюдаемых сбоев; причина не установлена.
> Прогон `20261030-003555`, подробности — `docs/fixes/T8-GPU-crash.md` § «Контроль без FG».

> **30.10, T8 GPU:** два TDR RTX 5070 на ПК-хосте с DLSS FG (00:21 и 00:28),
> WER LiveKernelEvent 141 / nvlddmkm.sys. Разбор — `docs/fixes/T8-GPU-crash.md`.
> На ПК для контрольного теста выключена только Frame Generation (`frame_gen=off`),
> DLSS upscaler и ваншот оставлены; сейвы не откатывались. Связь именно с FG пока гипотеза.
> После краша на ноуте сработали уведомление об уходе хоста, завершение сессии и возврат
> домой; доступность лампы ещё не подтверждена пользователем. Мод остаётся 260b64f.

> **T8, 2026-10-30:** T7 подтвердил дверь после собаки и отсутствие красной ленты.
> Остались ранняя белая лента (авто-pickability перекрывает запрет скрипта), потеря
> ключевых на новом призыве (очищенный журнал + фантомная сумка), завершение при меню/краше.
> Исправления и доказательства — `docs/fixes/T8-rejoin-quit.md`. Мод + relay-сервер;
> перед изменениями VPS его исходник сравнен с репо: различались только окончания строк.
> Код `260b64f` (включает e9baa51/d6e4ff7): сборка `exit=0`, 8 предупреждений,
> установлен на ПК и ноут; SHA256 `13B6AFF1A75A2D18D06B9E56EAABDA96C48F47246A503ECDCBD4F7872B94487D`
> совпадает во всех активных копиях. Сервер обновлён, сервис активен, TCP 20444 слушает;
> бэкап `/opt/bbsc/backups/t8-20261029-211454`. На обеих машинах чистый `start-clinic-teststart`,
> 14 файлов сверены; журналы сохранены как `*.before-t8-*`. Сейвы до отката:
> ПК `_auto-20261030-001559`, ноут `_auto-20261030-001602`.
> Прогон `20261030-001822` начат; ждём игрового теста, поведение ещё не подтверждено.

> **T7: лента до квеста и дверь с собакой.** Причины найдены в host-only событиях
> 12410702 и 12410748. Исправлены локальные квестовые события (16 по данным игры)
> и ложная ретро-выдача по служебным флагам ItemLot (красная лента 72410410).
> Подробности, ограничения и тест — `docs/fixes/T7-quest-gates.md`.
> Код `d68d03f`: сборка `exit=0` (8 предупреждений), установлен на ПК/ноут;
> SHA256 `DD48F3C5B6A54997A6F36279BDC605AAD1D3CC623A365A56EA9B9B60EC30EA03` совпадает.
> На обеих машинах восстановлен `start-clinic-teststart`, 14 файлов сверены;
> поздние журналы отложены в `*.before-t7-*`, сейвы до отката — `_auto-20261029-233803`
> (ПК) и `_auto-20261029-233810` (ноут). Прогон `20261029-233825` начат, ждём теста.

> **Тест 6, 2026-10-29 23:00–23:22 МСК:** `e40ede7` собран и установлен на ПК/ноут,
> хэши совпадают. На обеих машинах восстановлен `start-clinic-teststart` (персонаж `testStart`).
> Пользователь подтвердил предметы после загрузок/дома, стук, оба порядка смертей на боссе,
> клавиатуру и стик камеры. Логи собраны: `runs/20261029-225307`; детали — `docs/fixes/T6-results.md`.
> Осталось `?ActionEventInfo?` у гостя при возрождении (P3). Life-членство, одновременные
> NPC-действия, три игрока и длительное наблюдение остаются отдельными проверками.
> Ниже сохранена история; формулировки «не раскатано/не проверено» про e40ede7 и T5
> заменены этим результатом в пределах перечисленных сценариев.

> **Продолжение T5:** штатный NetworkSync отключён для трёх обработчиков стука;
> вайп берёт карту+позицию из follow хоста; возрождение другого гостя не считается возрождением хоста.
> Доказательства адресов, ограничения и дополнительные проверки — T5-results §8.
> Игровой проверки и деплоя не было.

> **T5, 2026-10-29:** правки предметов, смертей, точки гостя, NPC и SDL-ввода камеры.
> Сборка `build/mod/` успешна (`exit=0`); подробности, ограничения и чек-лист — `docs/fixes/T5-results.md` §7; полный аудит 507 пар
> (194 события) — `docs/fixes/T5-event-owners.txt`. Деплой и игровой тест не выполнялись.
> Не считать пункты проверенными в игре. Отдельно проверить одновременные NPC-действия
> и выход живого участника при мёртвом хосте.

Последнее обновление: 2026-10-29 (сессия «K2 предметы гостя, PT-9, смерти на боссе», затем T4 этапы 1–3).

> **2026-10-29, T4:** по тесту 4 (`docs/fixes/T4-results.md`) сделаны этапы 1 (`659b826`: спам лога Сна, возврат
> предметов поездки после каждой загрузки и дома, свой мир сразу при загрузке после вылета, катсцена один раз) и
> 2 (`3081a08`: профайлер `BBSC perf:`, сброс лога раз в 250 мс, исследовательские логи под «Research logs» —
> `docs/fixes/PERF.md`). Этап 3 — только исследование Сна: `docs/fixes/DREAM.md`, рекомендация — вариант (а)
> «гость видит свой Сон» — **пользователь выбрал (а), сделано** (`SHADPS4_BBSC_DREAM_OWN`, по умолчанию вкл., `DREAM.md` §5).
> Не раскатано и не запушено. Чек-лист теста — T4-results §6.

> **2026-10-29, позже:** после теста 3 (`docs/fixes/T3-results.md`) собрана сборка A+B: мод не удаляет и не блокирует предметы; дома только лог; выдача «положенного» и ретро — при принятии призыва в своём мире; исследовательские логи ключевых предметов; правки шторки и обложки; лог ввода камеры. Не раскатана. Чек-лист — `docs/fixes/K2-items.md` §10, разбор — `docs/fixes/K2-snapshot-plan.md` §4.
Начни с этого файла, затем `docs/BACKLOG.md`, `docs/fixes/K2-items.md`, `docs/RESEARCH-NOTES.md` (раздел 2026-10-29).

## 1. Где всё лежит сейчас

| Что | Состояние |
|---|---|
| Ветка `mark/bbport-fixes` | коммиты сессии: `2d3e0c9` (журнал предметов), `d2e3ad4` (дубли дропа), `6d62363` (ключи + проверка при входе), `33a8751` (PT-9 kept-home), `dd57483` (смерти, заглушка, мышь камеры), `0bfbc0a` (слежение за ключевыми дома, Сон после вайпа, I/J/K/L), плюс `41e2ad0`, `3a095c2` (A+B), `659b826` (T4 этап 1), `3081a08` (T4 этап 2, perf) и коммит документов. **Запушено до `2d3e0c9`, остальное — нет.** |
| ПК (хост) | раскатан `dd57483` (не последний!). **user_dir лаунчера переключён на `D:\Games\Bloodborne\testHost`** (было `ddd`; бэкап `%APPDATA%\bbport-launcher*\settings.json.bak-coopdev`). Перед игрой с друзьями вернуть `ddd`. |
| Ноут (гость) | раскатан `dd57483`. Журналы прошлых прогонов отложены: `...\bbsc\guest-items\taken-sd1-1.bin.bak-k2test`, `...\bbsc\item-ledger\ledger-sd1-1.bin.bak-k2test` (на ПК — `ledger-sd1-{0,1}.bin.bak-k2test`). |
| Снимки сейвов | `k2-before-test` на ПК (testHost) и ноуте (test) — состояние до тестов K2; `_auto-*` — автоснимки перед откатами. |
| Прогоны | `bloodborne_pc/out/coop-dev/runs/20261029-055243` (тест 1), `runs/20261029-040355` (тест 2, имя в UTC). |

**Важно про окружение этой сессии:** Claude работал прямо на mark-pc (Windows, Git Bash/PowerShell), а не в Linux-VM. `coopdev.sh` рассчитан на VM (ssh к `mark_pc`), поэтому шаги делались вручную:
`powershell -File bloodborne_pc\tools\coop-dev\coopdev.ps1 -Action <status|deploy-mod|save-snap|save-restore|set-user-dir|collect> -Install D:\Games\Bloodborne\bbport-coop ...` для ПК;
для ноута — `scp` скрипта и сборки в `C:\Games\Bloodborne\coop-dev\` + `ssh local_pc powershell -File ...coopdev.ps1 -Action ...`. Начало прогона (`run.txt`) и сбор логов VPS — вручную (см. `cmd_test` в coopdev.sh).

## 2. Что сделано и проверено

| Тема | Итог | Проверка |
|---|---|---|
| Повторная выдача «Нечистоты»/Посоха Лиги хосту (PT-5) | флаг получения своей награды (6676/6678) больше не откатывается охраной NPC-флагов; повтор одноразового уникального лота блокируется (K3) | причина CONF по логу хоста 27.10; повтор в игре ещё не проверен |
| Журнал предметов (K2) | `item-ledger/ledger-<user>-<slot>.bin`, CHECK-строки `BBSC CHECK FAIL/OK <класс>` | работает: тесты 29.10 |
| Дубли дропа с врагов | BBSC не выдаёт `isGuestDrop` (флаконы, пули) — их игра кладёт на труп; самоцвет из лота — одной ванильной наградой записи | тест 2: дубля нет |
| Ключевые предметы гостя пропадают (PT-1) | T4: игра восстанавливает фантомную сумку на **каждой** загрузке в мире хоста и дома; снимок не найден. `659b826`: возврат подобранного в поездке после каждой загрузки (3 с) и дома (5/30/60 с), `K2-lost-at-load` / `K2-lost-on-trip-home … put back` | **не проверено** (T4-results §6) |
| Выход печатью без загрузки домой (PT-9) | защита SN-kept-home; в тесте 2 выход прошёл нормально | триггер не пойман повторно |
| Заглушка с логотипом (PT-4) | BBSC больше не открывает экран загрузки сам | тест 2: заглушки нет |
| Камера наблюдения | мышь — работает (тест 2); I/J/K/L — исправлено в `0bfbc0a` | клавиши и геймпад не проверены |
| Мёртвый гость, хост не перезагрузился 45 с (PT-2) | гость сначала выходит из сессии, потом своя перезагрузка | не проверено |
| Вайп → Сон охотника (PT-12) | откат смены точки возрождения на лампу Сна, пока мёртв | **не проверено** (`0bfbc0a`) |

## 3. Открытые вопросы (по приоритету)

1. **Механизм отката инвентаря фантома.** ⚠ Поправка 2026-10-29 (`docs/fixes/K2-snapshot-plan.md`): откат **не** «целиком» — в том же сейве шкатулка этой поездки есть, пропала только лента (goodsType 1); снимок `0x0131E5C0` — это мир, не инвентарь; защита могла пропустить удаление (молчит вне окна 8 с). Главный кандидат — обработчик сообщений инвентаря `0x014D3DC0` (сообщение 25 чистит сумку, 24 возвращает ключевые по списку). План — исследовательская сборка с логами (этап A там же). Исходная запись: CONF по сейвам: после конца сессии игра восстанавливает инвентарь гостя из снимка, сделанного при входе, целиком (ни одного вызова 0x014D94A0/0x014DAB20), в плавающий момент (тест 1 — сразу при 6→0 без загрузки; тест 2 — позже 5 с после загрузки домой, но до сейва через 28 с). Пропадают ключевые предметы (лента 4903); флаконы/пули/осколок/шкатулка остались — проверить, все ли goodsType 1 или «предметы, полученные фантомом». Пользователь хочет **не выдавать ничего дома** — нужен настоящий фикс: найти снимок (кандидаты: `0x0131E5C0` «freezes own world into the save snapshot», `global+0x1698/+0x16B8/+0x16D8`, сейв-писатель `0x0156AA50`) и либо дописывать подобранное в снимок, либо не давать восстанавливать. Тогда убрать слежение дома и защиту на 0x014D94A0/0x014DAB20 (она ни разу не сработала, а висит на горячих функциях).
2. **Кто меняет точку возрождения на Сон при вайпе** (`global+0x1528`, ~5 с после смерти хоста). Кандидаты из комментария `TickBbscRespawnPointWatch`: 0x012F8259 (lamp update), 0x019423A0 (travel), 0x0131E4A0, 0x01312FF0, 0x01321440, 0x01338340 — поставить хуки с логом вызывающего.
3. **PT-9: что запускает решение «покинуть комнату»** (`0x01941C20` OwnWorldStep, stage request 4, без lua-события, сеть в порядке). Сейчас сессия завершается (`SN-kept-home`); лучше было бы вернуть гостя к хосту. Смотреть captures `OwnWorldStep` / `Persist.SkippedCleanup` при повторе.
4. **PT-10:** хост после перезахода в точке старта (клиника Иосефки). В том запуске было два персонажа (слоты 0 и 1). Нужен повтор.
5. Самоцветы/руны гостю через ванильную награду в мире хоста — путь не проверен (`K2-award-nothing` = запасной путь BBSC).
6. **Сон у гостя** — вариант (а) «свой Сон» сделан, ждёт теста; после теста удалить старый код Сна хоста (`DREAM.md` §5).
7. **Производительность** — по первым строкам `BBSC perf:` из теста перевести дорогие тики на 100–500 мс (`docs/fixes/PERF.md` §5).
8. Из BACKLOG: PT-6 (катсцены дважды — сделано в `659b826`, ждёт теста), PT-7 (стук в окна NPC), PT-8 (жест в инвентаре), WS-5, PT-3 (GPU TDR).
9. Друзья с сейвом `ddd`: инструмент мастерской рун у гостей — обход «инструменты как общие ключи» оставлен; ретро-починка сработает только если у них записался `guest-items/taken-*.bin`.

## 4. Решения пользователя (держаться их)

- Предметы у каждого игрока **свои**, подбираются сразу в мире хоста; **минимум выдачи гостю за действия хоста**; у гостя и хоста равные права.
- **Ничего не выдавать гостю после возвращения в свой мир**, если это возможно; проверка «все ли предметы есть» — при подключении к хосту. (Сейчас дома есть тихий возврат подобранных ключевых — вынужденно, см. §3.1.)
- Подарки разговоров — только за свой разговор (руна Валтра не раздаётся гостям, если вступил только хост).
- Ретро-починка: ключи, инструменты, значки, чаши (не расходники, не квестовые предметы для NPC).
- Повтор одноразового лота: блокировать + `CHECK FAIL K3-repeat`.

## 5. Ближайший тест — `docs/fixes/T4-results.md` §6 (последний коммит ветки)

Ниже — старый план для `0bfbc0a`, оставлен для истории.

### 5.0 (устарело) Тест сборки `0bfbc0a`

Раскатать `0bfbc0a`, откатить сейвы к `k2-before-test`, отложить `guest-items`/`item-ledger` гостя (как в прошлый раз), хост — **слот 1**.
1. Гость подбирает Белую ленту → выход печатью домой → 2 мин стоит. Ждём `K2-lost-on-trip-home … at home N s … put back` (N — момент отката) и ленту в инвентаре; затем выйти в меню и перезайти — лента в сейве.
2. Вайп на Чудовище-клирике: гость умирает первым (камера: мышь, I/J/K/L, стик), потом хост. Ждём `CHECK FAIL DEATH-dream-respawn` у хоста и пробуждение у лампы Центрального Ярнама, не в Сне.
3. Повторная загрузка Запретного леса хостом с вступлением в Лигу — руна «Нечистота» не множится (если дойти).
Логи: `grep -h "BBSC CHECK\|BBSC ledger\|BBSC items\|respawn point" bbsc-mod-*.log`.

### T11 follow-up: copy PC forest save to laptop
User requested the current PC save on the laptop. Source snapshot
`pc-forest-transfer-20261030-111920` created from PC testHost; restored to
`C:/Games/Bloodborne/test/savedata/1/CUSA00207/SPRJ0005`.
Save/system metadata and current own-world, bell-pending, item-ledger, guest-items,
shared-progress, kit-repaired directories synchronized; missing source journals
become empty on target to prevent old guest recovery from overwriting imported state.
19 files verified by SHA256. Laptop's old save and all journals backed up in
`C:/Games/Bloodborne/coop-dev/saves/before-pc-forest-20261030-111954`.
Both games were closed. Mod and Research settings unchanged.
