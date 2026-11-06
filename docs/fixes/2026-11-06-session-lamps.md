# Session-wide lamp discoveries — 06.11.2026

User requirement: whoever lights a lamp opens its travel destination for the
whole session. Chalice discoveries belong to the host ritual; they must not
unlock the guest's home cups.

## Cause and correction

Map snapshots were tied to the resident map owner. A lamp lit by another player
was not a session-wide fact for peers in other locations. Generic chalice copy
also deliberately preserved personal travel flags, and a slot/map ID alone
cannot distinguish two generated cups.

Use the existing WorldControl envelope, Lamps kind10, with a compact additive
mask and the complete existing world/map/dungeon/ritual scope. Existing native
single/value flag hooks enqueue actual discoveries. Any current session member
can report these, independent of NPC ownership. Only the host distributes
canonical discoveries. Pending proposals repeat until a canonical mask covers
them; the host repeats known masks for late arrivals/packet loss. Old ritual
incarnations and foreign sessions cannot unlock replacement cups.

The mask represents native lit7800+20*i and headstone7810+20*i flags. All44 base/
DLC lit flags match the read-only original common7000 event parameters. New
ordinary discoveries enter the existing additive shared-progress journal.
Chalice discoveries remain in session memory under the host ritual identity,
projected at native altar selection and immediately before native layer rows.
The guest's personal group is backed up before projection or native writes;
both lit and destination flags are excluded from its home progress merge.
The scoped m29 snapshot replaces previous-cup lamp bits instead of preserving
them as though they were the same dungeon. Existing native altar progress,
original native menu rows/warp/animation and save restoration remain the owners
of their respective operations. No direct warp, new UI rows or real save edits.

## Validation and limits

New tools/test_world_lamps.py executes production functions with allocated
memory: non-owner guest discovery, host relay, two other-map guests,44 ordinary
lamps and both setter widths,10 dungeon lamps, trusted snapshot recovery,
wire roundtrip, retry/ack/duplicates, separate channel/ritual masks, personal
backup and home-journal exclusions, stale ritual/foreign sender/world/malformed
rejection. PASS. Existing native altar fixture extended with actual12907 group:
scoped m29 clears previous cup lamps while retaining the personal backup. PASS.
Travel, actual native menu trampoline, shared progress policy, chalice scope
and full MOD syntax checks PASS. No live process, save or game-asset writes.

Build/deployment/startup tracked separately in parent out/coop-dev/runs/
session-lamps-20261106/run.md. Gameplay OPEN: both roles light a new world lamp
and a host-cup lamp; all session peers see destinations through their native
headstone/altar, then leaving restores guest personal cup discoveries. Also
check switching between two host cups sharing m29 templates.

Coordinated DLL built/installed00:31 MSK, exit0; two profiles started00:31:55 (14124/21528), both loaded the installed DLL. Backup and exact scope in parent run.md above. Gameplay remains OPEN.
