# 2026-11-03 — death-text deduplication, TCP connect recovery and hot paths

Status: source corrections and targeted fixtures PASS. Full fast package build
exit=0; PC installation exit=0, 5219 selected files copied at 00:14 MSK.
PC backup: D:/Games/Bloodborne/coop-dev/backups/death-http-perf-20261103-20261103-001347.
VPS Python gameserver updated. No games running during installation. File audit,
SHA256 and verify-release disabled as requested. Player 1/2/3 entry points retained.
Gameplay/UI and actual per-frame improvement remain unconfirmed.
Build log: bloodborne_pc/out/build-death-http-perf-20261103.log.

## Double YOU DIED

The 23:49–23:59 run submits two accepted death-text events on P2, at
23:58:13.980 (HP fallback) and 18.487 (late native PartyGhostDeath).
RaiseBbscDeathText now shares an accepted-event flag across both producers.
Rejected/invalid events do not consume it. The lifecycle clears the flag when
alive, loading or outside the session. A late native step cannot re-arm it.
This does not skip the native death script or alter wipe/death penalty rules.
Visual behavior and the complete gameplay scenario still need user validation.

## HTTP connection timeouts

The native log error=14 is cpp-httplib ConnectionTimeout, before HTTP dispatch,
not an HTTP response/read timeout. The native game sets 15000 microseconds;
the existing port rounds this to one second. That timeout remains unchanged.
Previously only seamless summon /request retried a failed TCP connect. All
private game API requests now opt into the same bounded policy through a
separate X-BBSC-Connect-Retry marker; summon semantics are not added to auxiliary
APIs. At most two retries. Never replay after read/write/SSL error, any HTTP
response, or success. Known public-server routes do not receive the marker.
The retry runs in the existing native HTTP worker, not the game tick.

VPS runs Python 3.12.3; ss showed accept backlog 5 on 20443, 50 on shadNet
31315. QuietHTTPServer now sets request_queue_size=128. In a controlled
loopback test with accept held, old queue admitted 5/24, production new queue
24/24. Global Linux counters before deployment: ListenOverflows=0,
ListenDrops=16 (historical, not scoped to this run). Thus accept saturation is
a reproduced capacity defect, NOT a proven explanation for all observed SYN
connect failures or the two broker 31315 failures. Intermittent network loss
cannot be separated from host scheduling with the existing evidence.

VPS live source exactly matched pre-edit bundled source. Backed up to
/opt/bbsc/backups/death-http-perf-20261103, installed new Python source and
restarted only bbsc-gameserver. Syntax compile passed, both services active;
20443 backlog now 128. External 24-request ss.info burst (12 workers) from this
PC: 24/24 HTTP 200, 0.792 s total. No account/database/firewall/SSH changes.
Native shadNet and its listener were not modified/restarted.

## Per-frame work

- Memory region cache 16 -> 128 entries, retaining the same 250ms permission
  lifetime and per-thread ownership. Last-hit fast path avoids a full scan on
  consecutive IsValidMapping/QueryProtection/field reads. A 48-region repeated
  fixture drops VirtualQuery calls from 480 to 48, with expiry and invalid
  addresses tested. This is an operation-count result, not an FPS benchmark.
- Inventory membership copies bucket/chain/slot fields from already validated
  spans rather than checking identical memory twice. Membership collision,
  carried/storage split, empty/absent items and malformed/cyclic chains tested.
  Collision fixture needs eight guard calls versus fourteen in the old helper.
- Dream player-type condition copies fields from its validated 0x30 span;
  production callback fixture covers guest, type 0/1, allowed/refused event,
  non-guest, invalid pointer and null registers.
- Quest event lookup no longer validates write permission on every read-only
  event step. Actual writes still use WriteValue and its permission guard.
  Existing cache identity, row, file and load-generation checks remain.

The old logged 4–5ms/frame estimate includes traced native work and Windows
scheduling across three local games. No claim of a measured FPS increase from
these source/fixture results. No reduction in gameplay tick cadence or network
queue/timeout limits, no new persistent game-pointer cache.

## Validation and provenance

Bundled fixtures PASS: test_death_hotpaths, test_repeat_death,
test_http_accept_burst, test_runtime_perf --npc-only, test_guest_bells,
test_summon_cleanup, test_hook_resume. Native test_summon_connect_retry PASS
(bounded recovery and no ambiguous POST replay). NPC-only mode avoids running
unrelated save/backup fixtures. These compile isolated test executables only;
full production build/installation status is separate below.

Both source trees updated without replacing their unrelated differences.
The existing working trees have extensive prior changes. Isolated cached-patch
checks fail against HEAD because surrounding source depends on those changes;
no broad commit or pin update was made. Before-text snapshots and focused
patches are retained in bloodborne_pc/out/coop-dev/changes-20261103.
The build includes prior source-only stale-claim timestamp / Stop observer
corrections from 23:47. It is a working-tree build, not a clean-commit release.
No user saves/settings/game data modified and no games launched by this task.
