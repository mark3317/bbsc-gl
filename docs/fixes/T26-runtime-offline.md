# T26 — dormant BBSC-GL and runtime offline switching (ROLLED BACK)

Date: 2026-11-01. Experimental Windows BBport build, CUSA03173 1.09.
User requirement: declining in-game network login must remove BBSC frame-hook costs.
No saves, game data, server or launcher configuration changed.

## Implementation

- Startup verifies the image and waits for GlobalState (BBport's import linking has
  completed by then). Only sceHttpCreateRequestWithURL is wrapped. The coordinator
  waits on an event; no game detours, pad wrapper, relay, P2P or polling guards are
  installed/running while the user plays offline from a cold start.
- An actual `/basic_utils/login` request wakes the coordinator and waits until all
  installers finish. Activation errors refuse the request rather than allowing an
  incompletely installed co-op session. Hooks are installed before character loading.
- Every detour, patch-table write and seamless byte edit records its first original
  and current enabled bytes. OFF restores original instructions, including the
  game-tick detour; ON reuses the existing trampolines without re-running one-shot
  installers or allocating another trampoline area.
- Code writes validate protections/preimages, pause the current process's other
  threads, check their instruction pointers against changed instruction ranges,
  write/flush, then resume. Conflicting third-party bytes refuse the transaction.
  Trampoline storage stays allocated for the process lifetime, including OFF.
- Callback leases let active hook/P2P/HTTP/slot-guard work finish before removal.
  Dormant workers wait on an event. Relay is disconnected, P2P socket/peers and HTTP
  claim state are cleared, native imports/window procedure restored.
- OFF is requested only after a known offline (`GlobalState+0x1590 == 0`), unloaded
  character, inactive native session state has remained stable for two seconds.
  Loading must be finished. If a confirmed return-to-title request was observed,
  a fast offline Continue can finish parking in the subsequently loaded own world;
  a guest world or a mere connection loss without the title transition cannot.
  No disabling on a network failure in a loaded world. A recent login gets 10 s
  grace; a login that never reached online gets 60 s before idle-title shutdown.
- The active-only watcher runs at 500 ms. Dormancy has no periodic watcher.
  Login/deactivation arbitration prevents a new login racing idle-title shutdown.

## Validation

Native `tools/test_runtime_gate.cmd` builds the production runtime and trampoline
code. It exercises cold dormancy, an event-blocked worker, a blocked actual login,
real hook dispatch, 50 OFF/ON cycles under four concurrent executable-code callers,
byte-exact restoration, zero offline callbacks, atomic refusal of foreign-byte
conflicts and failure of an unready login. It also checks the title/session/login
grace policy. Existing `tools/test_perf_policy.py` passes.

Final code commit: `ed6a58b`. Production build: exit=0, no warnings. Production
DLL load/dormant rewrite-export smoke test: PASS. Final native runtime test: PASS,
50 cycles and 321,985,467 concurrent fixture calls (this is not an FPS measurement).

Installed on this PC at `D:/Games/Bloodborne/Bloodborne Game Launcher/coop/client/bbsc`.
DLL SHA256: `319CF86B19C5EAF1E439AC69164267F1251E0BE350334A8CA2F833B3FAD98920`.
All three installed files match build hashes. Previous files preserved at
`D:/Games/Bloodborne/coop-dev/backups/T26-runtime-20261101-003638`.
Test bundle: `build/t26-runtime-20261101-003638.zip`. Laptop/server untouched.
Active user_dir remains `C:/Users/markn/AppData/Local/bbgl/twin`, launcher play_mode
remains Offline. Player selects Co-op manually for this test; no settings/saves changed.

## Still requires player validation

- Whether this game's actual menu uses the intercepted login route at the expected
  moment, and whether its local-character pointer clears at the offline title.
  Both determine the real UI transition; native fixtures cannot prove them.
- Cold offline vs ordinary launcher Offline: same scene/settings, FPS and frame-time
  consistency. Then online -> title/offline -> same scene, followed by online again.
- BBport's networking backend is still configured by the co-op launch. This change
  removes BBSC detours/workers; it does not promise that unrelated native networking
  backend overhead or total memory use equals a process launched without BBSC.
- Re-entry uses existing session cleanup and static state, as across normal title
  returns. Guest own-world/shared-progress recovery and another summon need a real
  co-op test. Never interpret a compile/native test as a proven safe guest roundtrip.
- The event-only bootstrap targets BBport's once-linked imports. Stock shadPS4 can
  relink imports later and is outside this experimental build's validated scope.

Log markers: `RUNTIME DORMANT`, `RUNTIME ON`, `RUNTIME OFF`, or `RUNTIME: ... refused`.
Only `RUNTIME OFF` confirms a fully restored and parked runtime.

## Installation correction

Launcher initially rejected the test because client/bundle.json still contained
release hashes. Preserved that original manifest with the rollback binaries,
updated the three BBSC hashes and test source label, and verified all 10 client
files with launcher bbport_bundle.verify: PASS. Test archive includes the matching
installed-client-bundle.json. No integrity check was disabled.

## First player run and laptop deployment

Player reported apparent success. Inspected the current profile (renamed to
`%LOCALAPPDATA%/Bloodborne Game Launcher`) and mod log
`bbsc-mod-20261101-004018-17160.log`, plus twin/last_run.log.

- 00:40:27.226: DORMANT, zero game detours.
- 00:41:03.263: 31/31 selected RE hooks installed, other functional hook groups
  also report installation; no installer/signature/transaction errors.
- 00:41:07.139: ON, 776 owned code bytes, relay connected immediately afterward.
  Actual game-tick, cinematic, NPC/Dream, inventory and pickup handlers appear in
  log/perf counters; HTTP wrapper caps messages/bloodstains and native requests
  carry the seamless and summon-polling headers.
- 00:42:29.691: OFF, original instructions/imports restored and workers parked.
  No subsequent game-handler messages until reactivation.
- 00:42:52.166: ON again in the same process; relay reconnects, HTTP rewriting and
  real functional hook/perf counters resume. No repeated installer run needed.
- Process ends through the normal PC menu Quit Game path. The run contains one
  echo-HUD warning, unrelated to runtime activation; no runtime refusal/errors.
- The 17.9/s sample after reactivation includes the dormant/menu gap in its 49 s
  wall-time denominator. It is not evidence of a 17.9 FPS rendering regression.
- Session state stays 0 (solo); actual two-player summon/world sync is untested
  in this run. Exact ordinary-offline FPS equivalence remains unmeasured.

At the user's request, deployed the **same tested binaries**, not a rebuild, to
laptop `C:/Games/Bloodborne/bbport-windows/coop/client/bbsc`. Game/launcher were
stopped. Preserved previous three files and bundle.json in
`C:/Games/Bloodborne/coop-dev/backups/T26-runtime-20261101-004652`.
Updated laptop-local manifest hashes and verified all 10 bundled client files.
DLL SHA256 matches PC: `319CF86B19C5EAF1E439AC69164267F1251E0BE350334A8CA2F833B3FAD98920`.
Laptop saves/settings and server unchanged.

## Clean laptop launcher installation (explicit user request)

Replaced the old portable laptop launcher with the current clean BBGL package
`bbgl-1.0.0-live-graphics-20261031-98b421c-windows-x64.zip`, overlaid with the
same tested T26 binaries and matching client manifest. New executable:
`C:/Games/Bloodborne/Bloodborne Game Launcher/Bloodborne.exe`.

Removed the explicitly requested old installation `C:/Games/Bloodborne/bbport-windows`
and the old Local/Roaming `bbport-launcher` profiles. Checked absolute removal
paths, no overlap with preserved game/test, no reparse points or unexpected
embedded saves. Old installation was removed only after staging and full
post-move verification. Updated the Desktop shortcut to Bloodborne Game Launcher.

Preserved `C:/Games/Bloodborne/test` (6,354 files) and `game` (28,851 files):
complete relative-path/size/write-time inventories unchanged; all 16 actual
savedata files SHA256 unchanged. Fresh `%LOCALAPPDATA%/Bloodborne Game Launcher`
settings contain only game_dir -> game and user_dir -> test; old preferences,
accounts and local configuration were not migrated.

Verified all 5,223 installed file hashes and both co-op bundle manifests. The
new packaged executable's hidden smoke check imports Qt 6.12.0 successfully,
passes the release payload/hygiene verifier, and confirms the fresh game/test
paths. No game launch or save write. Deployment proof and inventories remain at
`C:/Games/Bloodborne/coop-dev/fresh-launcher-t26-20261101` on the laptop.

## Regression: user reports OFF ineffective on both machines

Latest paired run: PC `bbsc-mod-20261101-005906-20032.log`, laptop
`bbsc-mod-20261101-005859-17100.log`; collected under build/t26-switch-failure.
Real co-op session is now evidenced: PC state 3, laptop state 6, world/item sync,
combat and wipe/reload recovery handlers execute.

User reports mod remained active after selecting offline on both machines.
Laptop eventually logs OFF at 01:07:54.573 (after native leave/own-world recovery
and pending progress merge); no later ON appears in that run. PC eventually logs
OFF at 01:08:42.741, then ON at 01:08:45.548. PC last_run.log independently shows
another `/basic_utils/login` request at 01:08:45.347..552. This proves the HTTP
bootstrap reactivated the runtime; it does not prove that the user selected
online. Current activation equates any login request with online intent.

The logs do not record the exact user's menu-choice time or the coordinator's
raw online/character/loading/title fields. Therefore the exact reason for delayed
parking on each machine cannot be established from this run. Do not claim all
OFF transitions are reliable based on the previous solo test. Activation must
be distinguished from incidental/retry login traffic, and title/offline choice
needs a reliable observable event; avoid adding per-frame offline hook overhead.
No new code or binaries deployed during this log inspection.

## Explicit rollback requested by user

The runtime switching experiment is cancelled. Restored every changed emulator/
and tools/ path to pre-T26 commit `0612586`; removed runtime source/header and
its test files. Launcher code/installation remains current and unchanged.

Restored original pre-T26 bbsc.dll, bbsc-launch.exe and mod.json on both PC and
laptop, using the preserved original PC payload, and restored/recomputed bundle
integrity manifests. All 10 files verify on both machines. DLL SHA256 on both:
`D55F47985882094D6810D882B82193794A332AE7372C845FAB193E6EAB690142`.
The build/mod outputs also contain the restored original binaries (copied, not
newly compiled). Experimental binaries remain only in historical test archives
and rollback backups, and are not the installed/default build.

PC experimental backup: `D:/Games/Bloodborne/coop-dev/backups/T26-before-rollback-20261101-011607`.
Laptop experimental backup: `C:/Games/Bloodborne/coop-dev/backups/before-runtime-rollback-20261101-011629`.
No running game was terminated. Saves, game content and launcher preferences
were unchanged. Behavior is the previous separate Offline and Co-op launch modes.
