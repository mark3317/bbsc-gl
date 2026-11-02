# Home Shared Progress policy audit — 01.11.2026

Previous implementation OR-merged all kind-1 map bits at home. Live world sync
protects 789 NPC flags, but that protection was not applied by home merge.
Likewise, map kind 1 includes combat start / event completion bits, not just
durable doors, lamps and boss victories. The 04:21 run re-created Cleric Beast's
gauge one second after a second home merge set 20 map flags.

Read-only scan of CUSA03173 1.09 event scripts: boss gauge events 2003[11]
with enabled=1, their event completion IDs and literal map-flag conditions
(3[00]). Exclude candidates below map offset 4000, preserving defeat flags
(e.g. 13201802). Result: 63 encounter candidates across base game/DLC and
chalice templates. Reproducible inventory: tools/gamedata/boss_progress_flags.py.
For Cleric Beast, 12414702 starts AI and gauge when 12414700 OR 12415400 is
set. All three are excluded from the host's home merge, not from live session
sync. This also makes first-encounter triggers personal when brought home;
the client's own previously seen intro state is preserved.

Home merge now rejects known NPC flags, known personal map-event completion
flags and the 63 encounter flags. The filter is at consumption, so old pending
journals receive the same policy. No removal of existing local bits and no
save rollback. Personal talk journals still apply the client's actual actions.

Kept: explicit global boss victories/night progression, durable map doors,
shortcuts, lamps, world progression. Existing exclusions remain: Dream and
chalice world progress, kind-5 pickups and kind-6/7 NPC/object states. The
live host world still governs play while summoned. No broad numeric range
deletion: unknown world flags stay unchanged to avoid breaking travel/events.
The explicit global progression lists were retained; further cuts need a
specific demonstrated personal-event conflict.

Logging now records individual newly applied map flag IDs at each home merge.
The old runs contain counts only; their exact 20 changed IDs cannot be inferred
as proven from the timing. General classification of every world flag remains
incomplete; this is a bounded correction, not a claim of an exhaustive audit.

Code: standalone 7f49c5e, bundled abb159d, BBGL pin 105ef52.
Targeted production mask test PASS: all known encounter/NPC flags rejected,
defeat/ordinary progression retained, all 10,000 Central Yharnam bit positions
checked, own bits preserved. No broad tests or changes to live player saves.
Bundled DLL build exit=0; installed on both stopped computers at 04:30.
Override/active files and entire bundle manifest hash verification PASS.
DLL SHA256: 6BC11F201D3855229A19FAF3140AAA732AC5501620C8EC15A763AAE6CB156F22.
Backups: PC `D:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-043022`,
laptop `C:/Games/Bloodborne/coop-dev/backups/boss-load-20261101-043028`.
Gameplay confirmation pending: wipe, host exits first, guest home with no gauge;
real next encounter must enable its gauge. Personal NPC actions must remain own.
