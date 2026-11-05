# Explicit host load follow — source fixed, gameplay open

The investigation below is historical. This change has not been built or deployed.

Host TickBbscFollowBroadcast records bbsc_load_generation plus initial map/position/heading after confirmed native completion and valid transform. It repeats this immutable record with every position message, preserving it while walking. A newly completed generation bypasses the ordinary500ms send cadence. Packet silence, delayed delivery and movement no longer determine arrival for updated peers.

Follow kind1 retains the34-byte prefix, then the24-byte dungeon key only on chalice maps, then a24-byte Arrival (u32 generation/map and four floats). Lengths are58/82bytes. Shared bbsc_follow.h codec is used by all three receivers and both senders. Unknown kinds, partial/oversized tails and invalid nonzero arrival records are rejected before host discovery. Kind0 legacy30/34/58-byte messages retain old inference and debounce. Party relay is opaque to this tail; no Party/server deployment is needed. Both gameplay peers must update for explicit metadata; mixed old/new chalice transport is not supported as a validated configuration.

Updated guests bypass2500ms mismatch debounce only for a fresh, unconsumed explicit completed load into the advertised map. The first eligible250ms game-thread check can request follow, after required flags/identity arrive. No promise of250ms total latency: network scheduling, world state and local readiness still apply. The host's loading time and the guest's own load remain sequential.

The5000ms guest safety interval is unchanged, by user's final instruction. It now also observes completed native generation and pending world-construction/reload callbacks: loading suspended between ticks cannot evade the guard. Death, initial summon ownership, world/dungeon readiness, retry limits and walking rules remain in force. No attempt was made to lower crash protection.

Validation: tools/test_follow_transition.py executes production broadcast, receive and follow tick; confirms immediate explicit follow when safe, stable arrival despite walking/repeated packets, consumed arrivals, old debounce, flags/death gates,5000ms native-generation/pending-callback protection, ordinary/chalice codec round trips and malformed rejection. tools/test_follow_arrival.py, tools/test_chalice_scope.py and tools/test_relay_dispatch.py PASS; the latter verifies new metadata through actual role/session dispatcher and rejects foreign/truncated frames. MSVC-target /Zs for bloodborne_re.cpp, mod/bbsc_relay.cpp and core/bbsc_relay_client.cpp exit0. Script under parent out/coop-dev/runs/follow-delay-20261104/syntax.cmd. These are code checks, not gameplay confirmation. No build/deploy, save/settings/game-data writes, process stop, commit/pin/push.

---

# Follow delay investigation — 04.11.2026

Read-only PC twin / laptop test logs. Latest short starts18:56–19:01 contain no follow/load completion events; laptop current last_run.log was0bytes at collection19:10 onward. Latest evidenced transition session is18:24–18:37, before18:53 DLL deployment. Do not claim new DLL gameplay validation.

Evidence: parent out/coop-dev/runs/follow-delay-20261104/{pc-timeline.txt,laptop-timeline.txt,laptop-last_run.1.log,laptop-last_run.2.log}. PC source D:/Games/Bloodborne/twin/last_run.1.log; laptop C:/Games/Bloodborne/test/last_run.2.log, strict SSH/scp over known Tailscale host. No saves collected. Cross-machine absolute differences are approximate: clocks show subsecond skew; same-client durations are exact to logged timestamps.

Host only broadcasts settled own-world map/transform after native loading flag clears, every500ms. Guest polls250ms, requires2500ms stable mismatch, waits5000ms since last observed own load, optionally up to4000ms for world flags. These waits are conditional and must not simply be summed.5000ms guard documents a real crash from issuing another load during wipe recovery.

Dream return: host completion/broadcast18:36:00.996; guest request18:36:03.761; guest arrival18:36:18.378. Approx2.8s from host completion to request,14.617s client request-to-arrival. Mensis: host18:32:18.753, guest request18:32:21.104, arrival18:32:29.743 (8.639s local load).

Additional delay before follow: host Byrgenwerth18:26:29.538; guest18:26:30.071 says host walked/no reload, only18:26:36.839 requests follow. Host Lecture18:31:43.191; guest18:31:44.358 says walked/no reload, requests18:31:51.345. The latter follows guest's previous load completion18:31:44.065 approximately; includes post-load protection. Exact packet timing for false walked classification is unrecorded.

Code cause candidate: OnBbscHostFollowPacket infers arrival_by_load from receive silence>1500ms; map change alone does not set arrival metadata. TickBbscFollowHost suppresses reload for resident target without this classification. Logs prove initial no-reload decisions; missing raw packet timing prevents proving why the inference failed. Use explicit host load generation/completion metadata to remove this ambiguity if implementing later; retain safe guest readiness guards.

No product changes, tests, build, deployment, game control, save/settings writes, pin/commit/push. Investigation remains OPEN; latest deployed DLL has no transition evidence in collected recent starts.
