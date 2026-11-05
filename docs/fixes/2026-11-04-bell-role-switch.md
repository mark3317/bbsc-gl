# 04.11.2026 вЂ” host-to-responder switch leaves Party ownership latched

Historical investigation below; superseded by the source fix and deployment record appended here. Gameplay remains OPEN.

Evidence: parent `out/coop-dev/runs/join-failure-20261104-2051` contains PC and laptop game-log snapshots, rotations, collection provenance and Party journals/events. Games were running during collection; current game logs are partial snapshots, not final logs. Party snapshots were collected separately afterwards. No saves/settings changes, game termination or journal repair.

Both DLLs report version 1.1.0 built Nov 4 20:17:07. PC twin PID18108; laptop test PID6272. Parent gitlink and BBSC HEAD remain 0ddb1d4; pre-existing working changes retained.

## Timeline (MSK)

- Laptop20:46:53.915: Beckoning acquires its own world, generation2 revision9. No native room, pending admission or joined members.
- PC20:47:02.665: Beckoning acquires its own world, generation19 revision146.
- Laptop20:47:26.475: native bell trace changes from host=true/responder=false to host=false/responder=true, state0.
- Laptop20:47:31.518: responder sign published=true; subsequent refreshes continue every2s. No confirmed Beckoning silence or ownership-release event appears in this interval.
- PC20:47:03.559 and20:48:04.026: sign_search reports laptop no_sign. No claim or JoinRoom occurs.
- PC20:47:58.427: confirmed Beckoning silence; Party releases at20:47:59.005, then reacquires at20:48:03.969, generation20 revision148. Laptop remains owner of its independent home, generation2 revision9.

## Cause and limits

Both devices discover each other. PC receives laptop presence but its sign is masked: DynamicEngine.dispatch('presence') returns a real local sign only when home.owner is None (and attachment permits the sender). Installed dynamic.py on both devices has the same ownership gate. The laptop home journal still has its own owner, room=None and empty pending/joined, despite the native responder bell and published sign. This establishes why admission cannot start; native UDP negotiation is not reached.

The failure is a missing release during the Beckoning-to-responder transition. The logs establish the transition and missing release, but not the exact menu/item action which caused it. Do not characterize this as proof that the confirmed Silence callback itself failed: no callback was captured on laptop. Existing native retirement requires host-state observation; this run remains state0 during the empty host search. A safe fix must cover an acquired-but-never-hosted empty world without interpreting death/loading or passive bell expiry as permission to tear down an occupied session.

Temporary workaround to validate: explicitly silence the laptop Beckoning Bell before ringing Small Resonant Bell (if necessary ring Beckoning again, then choose silence using Silencing Blank). Wait for the role release, then ring Small Resonant Bell. This workaround was not performed or game-confirmed in this investigation. Do not delete journals or reset saves.

## Source fix and targeted verification

User clarified that BOTH devices initially rang Beckoning. Fix covers this collision as well as manual Beckoning-to-Small-Bell switching.

- Dynamic presence advertises a host separately from responder signs, only with a fresh native observation and durable ownership. A closed room/title exit is not an advertised host. Occupied worlds keep host presence across loading even when native bell/role momentarily clears.
- On each native observation, the DLL sends the actual Small Resonant Bell effect as well as existing life/load/population evidence. A fresh living, nonloading single-player responder in native0/2/5 explicitly releases a previously acquired EMPTY search. No inferred expiry, missing actor or timeout authorizes this release. Room, pending/joined admission, staged mutation or attachment blocks it.
- On world load, the game thread checks the cached host hint, allowing3s for discovery after readiness. If a host exists, it uses the original native Small Resonant Bell item entry (goods205, argument17) once. It preserves already active manual bells/invasion searches, loading, death, established sessions and title transitions. No network I/O occurs on the frame thread.
- The native tick availability and /party/acquire both reject starting a second host while a fresh remote host is known. For simultaneous empty host searches, an occupied host wins; otherwise the stable player identity breaks the tie. An established local room never yields. The loser cancels its native Beckoning search, waits for durable release and then starts native responder search. Before issuing a yield hint, Party fences new room creation/claims for that generation, so a late game tick cannot cancel a newly accepted guest.
- Optional host_check tick extension adds a fifth integer (0 neutral,1 remote host,2 yield empty search) after existing availability/cancel/notice/release fields. Older two/four-field replies remain accepted; both devices need the updated DLL+Party for the new behavior. Legacy fixed-roster local-three behavior is unchanged.

Validation: six real-loopback DynamicEngine+Compatibility cases PASS (including claim/JoinRoom); production native role fixture PASS (initial/late discovery, collision, one cancellation, native responder, death/load/member/title fences, preservation of manual bells); native tick and deferred item fixtures PASS. Fourteen existing dynamic tests PASS. Five production WinHTTP cases PASS, including host-hint parsing and the actual responder observation. Initial WinHTTP fixtures had obsolete3-argument observations and lacked the aimed-placement link stub; fixtures corrected and affected cases rerun PASS. No live saves or settings were used.

Build/deployment record: parent out/coop-dev/runs/bell-roles-20261104-2108/run.md. Gameplay confirmation remains required.

## Installed21:07MSK

DLL build exit0; unchanged build inputs. Identical seven-file DLL+Party delta copied to PC and laptop, both deployment commands exit0. Backups: Bloodborne/coop-dev/backups/bell-roles-20261104-20261104-210659(PC) and210719(laptop). No game launch or process termination, no saves/settings writes. Gameplay OPEN.

## User gameplay confirmation

04.11.2026: user reports the PC+laptop run works correctly ("прогнал все работает ок"). Reported bell-role/host-check scenario confirmed; this does not confirm unrelated finale/NG+ behavior.

## Reverse switch regression — 04.11.2026, latest21:27/21:29 run

User requested Small Resonant Bell -> Beckoning must stop responder search and own the host role, blocking Beckoning for others.
Laptop run_20261104_212705.log:21:36:40.769 acquire ticket24 granted, native21:36:41.244 reports host=true/responder=false. But laptop Party events queue responder_released_empty_search21:36:40.773 and release revision21 at21:36:40.824, before the next native host sample. PC then acquires21:36:48.370. This proves a stale responder observation revoked the newly acquired generation. PC run_20261104_212922.log and both Party snapshots collected under parent out/coop-dev/runs/responder-to-host-20261104; copied live game logs are partial snapshots. Laptop bell-excerpt.log preserves the independent filtered read.

Fix: require observed Beckoning in the exact owner/generation/room scope before automatic responder release. Acquisition clears that witness, withdraws the previous sign, and advertises reserved host intent before native animation/effect application. Old Small Bell create callbacks cannot republish while locally owning. Explicit cancellation can drain even if native Beckoning never applied. Upon a granted native action, erase Small Bell9005 before applying native Beckoning; failed erasure retries without activating both bells.

Eight targeted real-RPC/Compatibility cases and the production deferred native item fixture PASS. Covers stale pre-grant responder samples, blocked peers before the first Beckoning sample, late sign refresh, cancellation before any host sample, reverse/manual switch, collision, pending admission and lifetime/erase-failure fences. The previous host->Small fixture now republishes its sign after durable release, matching periodic native refresh; the affected case rerun PASS. Gameplay confirmation is separate.

Reverse-switch DLL build and both seven-file delta deployments exit0 at21:47MSK; both launchers opened/responding, no game started. Backups and validation recorded in parent responder-to-host-20261104/run.md. Reverse-switch gameplay remains OPEN.

## Return-home auto-ring regression, installed22:01MSK

Laptop latest run_20261104_214815.log:21:52:19.484 native guest6,21:52:42.141 native return0 after Blank,21:52:55.552 world-load host check explicitly starts native Small Bell again. This confirms an automatic re-ring after return, as clarified by the user; it is not solely retained pre-join effect state. PC/laptop partial live logs and Party snapshots retained under parent out/coop-dev/runs/return-bell-20261104.

Native successful guest6 now consumes9005 by effect erase only, deferred during loading/death/curtain. Does not call Stop/Blank/PartyCancel or change membership. Return clears any native-restored residual effect once. Completed guest visits suppress automatic Small Bell on home return and later personal travel within this game process; fresh startup discovery and explicit simultaneous-host yielding retain their behavior. Host availability checking remains active. Later deliberate manual Small Bell use is preserved.

Compatibility JoinRoom withdraws the search sign; joined or consumed late create requests cannot republish it. The new observed native responder-off personal return clears consumption; a later responder-on allows manual search again. Older fixture clients without native observations retain compatibility.

Validation:9 real RPC/Compatibility role cases PASS; production native role fixture PASS, covering join4 vs established6, loading/death/guest respawn, return/erase failure, subsequent personal travel, manual ring and preserved collision/initial-load checks. DLL build exit0; source inputs unchanged. Six-file delta deployed PC/laptop exit0. Backups Bloodborne/coop-dev/backups/return-bell-20261104-20261104-220119(PC),220136(laptop). No launch/process stop or real-save/settings changes. Gameplay remains OPEN.

## Multi-case gameplay review22:04–22:11

Latest22:00:29 DLL:6 guest joins and6 returns confirm consumed Small Bell / no automatic re-ring. Menu, Blank, kick, host exit and role exchange succeed; both journals end empty. Separate OPEN mismatch reproduced: after last-guest teardown, fresh native0/bell=true can retire Party ownership after3s, so active Beckoning and advertised authority disagree. No two Party owners were observed; native-effect overlap and simultaneous presses are not ruled out by that. Also17 expected HTTP keep-alive resets print unhandled tracebacks. No product changes in this review. Details parent out/coop-dev/runs/connection-matrix-20261104-2212/run.md.

## Idle-host/HTTP fixes installed22:27MSK

Drained empty searches with native Beckoning active and no explicit release intent retain their owner through native0/2/5. An outstanding staged dynamic admission prevents treating a world as a drained search. Same-generation host readmission works without ringing again; remote can_beckon/acquire remain blocked. Explicit cancel/expiry keeps normal release. Old occupied-room recovery remains unchanged, including residual-bell recovery and Dream-load guards.

HTTP.handle catches only reset/abort/broken-pipe connection endings outside respond(); unexpected handler failures still reach server diagnostics. An I/O-failed response marks close_connection instead of waiting for another keep-alive request.

Both new real-loopback regressions failed before the fix. Afterward13 bell-role/HTTP cases and4 targeted static/dynamic recovery/load cases PASS. One initial parallel fixture invocation collided on its fixed loopback port; affected2 cases rerun sequentially PASS. Python compile and minimal Party package exit0. Only coop/party/compat.py updated on PC/laptop, both final deploy exit0. No DLL/native/launcher source changes or binary rebuild; existing22:00:29 DLL retained. Backups under Bloodborne/coop-dev/backups/idle-host-http-20261104-20261104-222706(PC),222738(laptop). No game launch/process termination or real-save/settings edits. Gameplay OPEN.
