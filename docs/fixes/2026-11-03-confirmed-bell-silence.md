# Confirmed Beckoning silence and ownership release — 2026-11-03

23:05 run: P2 owns generation21. Final room removed at23:07:17.818 (revision205),
but owner remains P2 until title exit23:09:03.963 (revision206). Native bell diagnostic
continues host=true at23:07:18 despite state0. No host Blank callback/cancel was logged.
Evidence: parent out/coop-dev/runs/blank-host-review-2305/pc and
out/coop-dev/runs/blank-silence-20261103/player-*-party-events.jsonl.

Static native path: menu entry302110 installs callback01BC22F0. Its confirmation
continuation uses vtable05341300 (+10 ->01BC6BE0), which writes1 to
[[05562878]+474]. This bypasses goods111/201 execution hooks. Hook the exact
10-byte store at01BC6BE7, retaining the original store and return. Atomic flag
hands the confirmed action to the game tick: erase Beckoning9000, PartyCancel,
and use existing empty-room native Stop/cleanup. Remaining guests are retained;
party release still requires native idle plus finalized empty membership/room.
Opening or cancelling the menu does not call the confirmed continuation.

The private loopback tick optionally returns a fourth finalized unowned generation
(bell_release=true); old two/three-field replies still work. A client that saw the
remote start shows the stop once on that generation's finalized release. Unknown,
stale, network-loss and nonfinal state cannot generate a stop. No shared network
protocol/reducer changes; no VPS deployment needed.

User-approved Russian strings, exactly:
- В мире раздаётся звон Зовущего колокола
- Звон Зовущего колокола прекращён

Validation: production host Blank tick fixture (idle, retained guest, native drain),
exact native store through actual trampoline, production notice tick, real WinHTTP
parser old/new/malformed replies, three-process notice RPC/legacy and host rotation
regressions PASS. Game validation remains pending after deployment.

## 04.11.2026 — notification wording and punctuation (source only)

Russian and English single-sentence mod notices omit their final full stop.
Original bell search/discovery, arrivals and invasion wording is restored where
its meaning still applies to seamless co-op. Multi-sentence notices and search
ellipses are retained; covenant discovery warnings remain in their existing form
(the requested exclusion of «Слышен перезвон…» is preserved). Both generators
share tools/gamedata/notice_text.py; menu help and item descriptions keep their
punctuation. Verified 224 entries per language, original text correspondence,
name/boss tags and inline notice punctuation. No build, deploy or game test.
