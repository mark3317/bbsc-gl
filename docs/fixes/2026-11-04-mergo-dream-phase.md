# Mergo: shared Dream finale with personal services

Status: SOURCE FIXED; not built/deployed; gameplay OPEN.

User reported an unburned guest workshop after jointly defeating Mergo's Wet Nurse,
and explicitly requested shared finale. Own-Dream mode suppressed the entire v2
Dream snapshot and retained the guest's own global phase, even though the m21
final-boss battle flags and shared ending/NG+ machinery already existed.

Latest laptop last_run.log records follow to Dream at19:30:33.339, own-Dream skip
before load and at character construction19:30:34.760; arrival19:30:37.980.
Shared progress12601800 is applied only during the home load19:31:05.224.
PC rotations currently end18:57 (last main gameplay18:37); laptop ends19:34.
Do not assume these differently timed files provide a matched final host trace.
Evidence: parent out/coop-dev/runs/mergo-dream-20261104, laptop raw rotations
and filtered PC/laptop timelines. Live9462 values were not logged.

Read-only original m21 EMEVD confirms9462 selects workshop models/effects/gate
in12100300/12100310/12100400. 1028..1030 select Gehrman's final story stage
(12100143..145). Sender now includes v2 Dream snapshots in own-Dream mode too.
Guest selectively borrows only9462 and1028..1030, before follow construction and
at character creation, then refreshes during Dream ticks. Existing fresh-snapshot
wait also covers own-Dream loads (same bounded wait). Own values use the existing
own-world journal; shops, gifts, cords, NPC quest families and other bits are not
copied. Final-boss battle flags retain their existing narrow synchronization.
Once an ending is pending/playing, phase writes stop; existing host ending playback
and guest home/NG+ completion remain authoritative. Both peers need the updated DLL
for phase metadata. No new wire version or Party change.

Validation: tools/test_dream_phase.py executes the production phase writer and
checks native EMEVD dependencies, guest4/6 and excluded roles, both phase directions,
fresh/missing/wrong-map snapshots, ending hold, preservation of every unrelated bit
and original journal values. PASS. Production tools/test_follow_transition.py PASS.
MSVC-target /Zs of main TU and two relay TUs exit0. These are code checks, not a
DLL build or gameplay confirmation.

Requested endgame snapshots completed with exit0 while games were stopped:

- PC D:/Games/Bloodborne/coop-dev/saves/endgame-mergo-20261104 (32 files), source
  D:/Games/Bloodborne/twin, confirmed by newest launch header/save slot. Settings
  still points at an older LocalAppData twin; that older save was not substituted.
- Laptop C:/Games/Bloodborne/coop-dev/saves/endgame-mergo-20261104 (37 files), source
  C:/Games/Bloodborne/test, confirmed by latest launch header/save slot.

Both contain complete savedata including SPRJ0005.sce_sys and existing own-world,
bell-pending, shared-progress, item-ledger metadata. No restore, live-save edit,
settings/game-data write, process stop, commit/pin/push.
