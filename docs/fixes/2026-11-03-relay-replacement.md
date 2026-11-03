# 2026-11-03 — TCP relay recovery and stale departure correction

## Defects fixed

The03:05–03:12 game run had a real overlap: persisted VPS log shows old host
endpoint:51488, replacement:51153, then the old socket expires after381s
(4098 frames, Linux ETIMEDOUT). This is the extra fourth connection observed
in journal counters. Both guests subsequently process host departure and Stop.
The original TCP timeout's cause is still unknown; this change makes recovery
safe rather than disabling socket timeouts or suppressing all native stops.

Every server connection now gets a monotonic connection_id. A newer connection
that identifies the same(sender,session) supersedes the older incarnation.
Superseded sockets cannot forward stale game/control envelopes (including
SessionLeave), cancel the newer connection's departure decision, or announce
PeerLeft when their own delayed EOF finally arrives.

EOF/error without an existing replacement opens a10s reconnect grace window.
A valid envelope for the same identity cancels it; another player/session cannot.
The callback verifies pending-object identity and current replacement under the
registry lock before enqueueing a single party-scoped PeerLeft. This also makes
an already-running cancelled callback harmless. An obsolete still-open socket
cannot hide genuine departure of the latest incarnation. Pending records are
removed on cancellation/expiry; no polling or per-frame timer creation.

Genuine explicit SessionLeave packets remain immediate. Transport-only losses
are declared after10s if recovery does not occur (2s reconnect delay + connect +
existing periodic beacon). Game-native deadlines and UDP routing are unchanged.

Diagnostics: conn ID, endpoint, sender/session, close reason, superseded,
waiting-reconnect, cancelled-reconnected, suppressed-stale-leave and actual
notify-peer-left/recipient count. Client DLL logs server PeerLeft acceptance vs
explicit SessionLeave, so the next stop can be tied to its control source.
Server persistent /opt/bbsc/logs/gameserver-*.log must be collected as well as
journals: the previous journal snapshot omitted relay connection print records.

## Validation

Bundled production departure tests:11 PASS. Includes prior host/guest party
scoping, duplicate EOF, unidentified/solo, changed party; replacement before EOF,
replacement after EOF, racing cancelled callback, old state and SessionLeave,
genuine newest-socket loss despite older socket, wrong identity/session and
replacement of the pending decision. No waits in fixtures; actual callback runs.

Real TCP connections from this PC to public77.73.67.175:20444, ephemeral random
identities only (no accounts/DB/saves): old connection stale SessionLeave rejected;
replacement survives old EOF; reconnect after EOF survives beyond the10s timer;
final departure notifies exactly once and only its party. All PASS. Server log
records suppressed-superseded, cancelled-reconnected and one notify recipients1
for test party bba28bb1. tests/test_relay_vps_reconnect.py is an opt-in live test,
not a local-path substitute. Logs: out/test-relay-replacement.log,
out/test-relay-vps-reconnect.log, out/test-relay-vps-reconnect-server.log.

Native port unchanged; bundled DLL build exit0 with four existing warnings.
Fast package build/deployment status appended below. VPS Python
compile0, backed up /opt/bbsc/backups/relay-replacement-20261103/bbsc_gameserver.py,
updated only bbsc_gameserver.py and restarted only bbsc-gameserver; active.
No game launched, no settings/saves/database/firewall/SSH changed. Dirty trees
preserved, no commit/pin/push. Game confirmation and rejoin still required.

## Build and installation completed 03:30 MSK

Fast full package exit0, archive dist/bbgl-1.1.0-windows-x64.zip. Native build
was correctly skipped (no native changes). Seven-file PC delta: three mod files,
client bundle.json, coop/SOURCE.json, BBSC-GameServer.exe and server bundle.json.
Backup D:/Games/Bloodborne/coop-dev/backups/relay-replacement-20261103-20261103-033031.
No running game/launcher. VPS was updated and real-TCP tests passed against the
new deployed service. Game confirmation pending: hold6–7min and alternate guest
leave/rejoin while another remains; no game test claimed complete by fixtures.
