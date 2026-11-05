# Shared finale, fallen party members and first audience

Source checks PASS; build/deploy status tracked in HANDOFF. Gameplay remains OPEN.

## Latest evidence

PC actual BB_USER_DIR is now LocalAppData/Bloodborne Game Launcher/twin, not the
older D:/Games/Bloodborne/twin. Laptop uses C:/Games/Bloodborne/test. Both stopped.
Raw logs: parent out/coop-dev/runs/gehrman-finale-20261104/pc and laptop.
Guest died19:51:07.880; group victory/reward12101800 at19:51:26.353; native
BlockClear2 at19:51:31.363; automatic respawn19:51:34.090. Host sent ending
21000020 at19:51:29.616; no guest receive/play/ending journal line follows.
Guest TCP relay rx stops near19:48:42.933, well BEFORE either death or ending;
outgoing native guest traffic and host incoming traffic continue. No PeerLeft
until manual/native room leave19:54:55. Host proceeds to clinic intro19:52:56.
This is not evidence that death alone caused packet loss. Exact Party in-memory
peer error was not retained after shutdown, so the precise live queue fence is
not proven. Do not attribute every lost packet to a measured backlog overflow.

## Changes

Party previously permanently fenced a peer on a full128-frame outgoing queue,
silently discarding every later one-shot cutscene. Enqueue now waits for capacity
without holding engine/native bridge locks; outgoing sequence/order are retained.
Known network failure plus a full backlog still isolates that peer, preserving
healthy recipients; the existing10s deadline remains. RPC listen backlog128 fits
the16 concurrent relay workers. A healthy slowed peer receiving400 full snapshots
then the native96-byte ending gets all frames in order. Negative control restoring
the old immediate-overflow policy loses the finale on that same fixture.

Guest ending requests remain queued until actor/loading/death-curtain state is
ready. Existing boss-victory respawn/penalty logic recovers a fallen participant,
then releases the spectator camera. Host native terminal events12100000/12100002/
12100180 pause only AFTER their actual victory/submission predicate until this
same recovery is ready, before the movie/credits/cycle increment. Dead host is
never revived merely because a boss is still being fought. Native guest requests
cannot select a competing ending. Completion still requires an observed local
movie start/finish, native disconnect, own-world journal drain and confirmed save;
the absolute host cycle target prevents duplicate increment on recovery.

Before first audience, native12100800 hides barrier2101800/SFX2103800 only for
the host; guest fog entry12104811 needs intro12101802 and fight12104800. A guest
now locally opens just that barrier using a fresh authoritative m21 snapshot
until the first intro. No fight/intro/progression flag is fabricated. The barrier
returns to native fog handling as soon as host intro completes; subsequent wipes
and loads retain ordinary fog. Defeated bosses do not have fog forced back on.
Final talk t210306 remains disallowed; ordinary Gehrman talk210305 is also blocked
for guests during burning-Dream9462. Only host can choose submission/refusal.

## Validation and restore

- party/test_finale_relay.py: native TCP bridges + real RPC + slow healthy ingress,
  ordered400 snapshots and finale, reverse guest traffic PASS; old-overflow negative
  control fails delivery as expected.
- DynamicPeerFailure tests (crashed peer isolation and expiry) PASS; repeated-world
  PvP/kill-receipt transport regression PASS.
- tools/test_shared_finale_runtime.py executes production host event gate, actor
  recovery, receipt/dedup/replay, movie completion and home NG commit for all three
  endings, fallen host/guest, delayed actor/curtain, journal drain and save ACK PASS.
- tools/test_dream_first_audience.py executes production geometry policy against
  original native EMEVD dependencies: host/solo excluded, fresh/missing snapshot,
  first entry, intro/wipe/load/final victory, no progress writes, talk restriction PASS.
- Original endings/site inventory, transition-door pass and full MSVC-target syntax
  checks PASS. No gameplay claim from fixtures.

User explicitly requested endgame rollback. Full current savedata and BBSC
own-world/bell-pending/shared-progress/item-ledger were copied before restoring
the previously requested endgame-mergo-20261104 snapshots:

- PC backup D:/Games/Bloodborne/coop-dev/saves/before-gehrman-rollback-20261104-200959;
  restored into current LocalAppData/Bloodborne Game Launcher/twin.
- Laptop backup C:/Games/Bloodborne/coop-dev/saves/before-gehrman-rollback-20261104-201001;
  restored into C:/Games/Bloodborne/test.

Both restore scripts exit0 with stopped games, checked absolute target boundaries,
complete savedata including sce_sys and matching progress metadata. Existing
endgame snapshots and older D:/Games/Bloodborne/twin remain unchanged. No settings
or original game-data edit, process termination, commit/pin/push.
