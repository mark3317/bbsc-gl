# Lifecycle routing and native Stop — 2026-11-02

## Evidence and limits

Source run: `bloodborne_pc/out/coop-dev/review-20261102-0159`, PC PID 31380 and laptop PID 308, build 01:42:37. Prior chronological review: `2026-11-02-run-review-0159.md`. PC/laptop clocks differ by about 0.8 s: durations below use a single machine clock.

Guest confirmed-menu to native title-request intervals were 17.053 s and 12.951 s. Save completion was about 110 ms; actual native LeaveRoom was only 125/82 ms before title-request. The delay is before LeaveRoom, not evidence of a slow server LeaveRoom. The old queue snapshot cannot identify the internal Stop phase. New phase logs are necessary to attribute the full delay on a real run. Title-request is not the time the menu becomes visible.

## Changes

* Central protocol type registry with compile-time uniqueness: chalice mount moves from 0x2B to 0x2D. 0x2B remains Register, 0x2C RegisterKill. The actual shared relay/P2P dispatcher previously consumed mount as register and discarded it. Both machines must run the new build; old mount senders are not wire-compatible.
* Host-only game packets require the current host and session. Server peer-count control is accepted only from the relay server. Leave packets have exact length. Host discovery remains available while the joining guest has no known host, so locking a native/public-server host still works.
* Gate initial chalice summon at native function entry 0131E5C0, BEFORE world snapshot and reload phase 3. Do not merely log missing context in the later 01928987 initializer and continue destroying the old world. Context is checked at most 10 times/second only while a summon is deferred; no HTTP polling is added. Release once the scoped context exists. Quit/role/host changes cancel it; 15 s without readiness queues the common departure owner. Departure processing precedes release on the same frame.
* Native Stop task 0xC: signature-checked hooks at C98110, C9B960 and CC53C0 log phase transitions. C9B960 is the member-drain phase. At 2 s, expire the active task's own deadline under its existing controller lock, selecting native C9BA10 cleanup. LeaveRoom and its completion remain native; no fabricated state 0, task deletion, or timeout applied to unrelated requests. Static chain: Stop -> C98110 -> virtual 78/80 -> C9B680/C9B740 -> C9B960 -> virtual 88 -> CC53C0/CC53F0 -> LeaveRoom -> CC54F0 -> C9BBE0. A stuck earlier operation or network completion is not covered by the two-second member-drain bound.
* One owner observes the transition to session 0 and schedules cleanup. The stuck-lock watchdog no longer re-arms it after cleanup. A skipped native send-home releases leave/death locks on the next game tick after its caller returns, removing an artificial second of delay.
* Native loading-screen close is requested once while state is 1/2; states 3/4 are observed until state 0. Native close 0176D3C0 clears fade/interpolation fields, so calling it every tick while already closing restarted this work. This is a confirmed code defect; its share of the observed 30 s UI delay needs the next run.
* Never revive at the corpse as a fallback: the log showed Y=-1500.17 and another death 0.5 s later. Guest in-place respawn also requires the host's area and ready chalice revision. Missing safe lamp/living partner or unfinished world transition falls through to the existing real-load recovery.
* Revealing the guest world now requires finished native load, living player, host area, correct chalice revision, and reconciled item generation. The existing 75 s cover limit cannot expose an invalid world; failure of world OR inventory readiness queues common return-home cleanup. Quit bypasses the readiness barrier.

## Event ordering and expected behavior

| Case | Before loading / teardown | After native completion |
|---|---|---|
| Guest normal join | Existing own-world/origin journal and item barrier; lock host | Reconcile current generation; place in host world; reveal only when ready |
| Guest joins chalice | Same journal; wait for scoped mount before snapshot/phase 3 | Inject host context during native initialization; require matching revision before reveal |
| Host lantern/chalice/Dream transition | Existing scoped follow owns guest transition; stale revision cannot complete it | Guests arrive in host destination; no premature in-place revive in old world |
| Guest leaves, host leaves, confirmed loss | Common departure work; suspend persistence; native Stop and remote teardown | Guest returns to own origin; host remains in own world; terminal cleanup once |
| Confirmed menu exit, including chalice/death/leaving | Existing quit intent takes priority, journals saved, native Stop | Native title request; no guest-world detour; own prejoin origin retained for Continue |
| Death outside boss | Existing immediate revive path chooses loaded safe lamp/partner | If unsafe, one existing real reload; no corpse fallback |
| Boss death with living partners | Existing spectate policy retained | Wipe/recovery keeps existing echo/restock ownership; this change does not add another deduction |
| Delayed context plus departure | Process departure first; cancel deferred summon | No late entry into the departed host's world |
| Missing context / readiness timeout | Cancel through common departure, not fabricated success | Return home; confirmed menu still wins |

## Validation

Production-function fixtures pass: `test_stop_phases.py`, `test_relay_dispatch.py`, `test_chalice_scope.py`, `test_load_readiness.py`, `test_native_leave_release.py`, `test_post_load_recovery.py`, `test_menu_quit.py`, `test_hook_resume.py`, `test_boss_load_cleanup.py`, `test_home_return.py`. Coverage includes exact 2 s boundary, task reuse/readonly/unrelated tasks, close handshake, mount/register dispatch, role/session filtering, malformed/truncated packets, cancelled chalice entry, world/item generations, same-area resident versus other-area maps, return-home and quit ownership. No game or saves were used by fixtures.

## Still unproven / open

The first non-chalice join published the sign at 01:46:30, received aimed placement at 01:46:40, closed native signaling at 01:46:46, and received the claim only at 01:47:01. Existing interval writes did not make this create cadence two seconds. Static inspection distinguishes broker +190 (own-SOS refresh setting) from +194 (initial own-SOS lifetime, default 30 s); blindly shortening +194 would change lifetime, not prove a polling fix. Do not mark this initial-join race fixed, and do not re-enable a blocking HTTP repeat loop as a substitute. HTTP connect timeouts also lack a demonstrated causal link to Stop.

Live verification remains: both roles' menu exits (including already leaving), host departure during deferred chalice join, guest joining host chalice then host lantern exit, boss wipe/non-boss death, and first connection from different maps. Capture Stop phase elapsed times and title-request/menu-visible separately. A successful build and installation are not proof of these runtime results.
