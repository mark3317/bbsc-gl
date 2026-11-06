# 06.11.2026 — Central Yharnam lower elevator plate: investigation OPEN

User: P1 cannot depress the plate while the Gascoigne-bridge elevator is at
the bottom. P1 is guest, P2 host in the current 01:49 run. No behavior fix,
build, deployment or gameplay confirmation performed.

## Collected evidence

Parent `out/coop-dev/runs/elevator-plate-20261106/pc/collection.json` maps
game-7 to P1 and game-14 to P2. Both run_20261106_014900 logs collected;
2 files, warnings0. P1 changed during copy; these are live snapshots.
HEAD and parent pin both 4989896fd19fb9b9dd908d52c345a62b3b82b6c6;
existing dirty source preserved.

- P1 02:35:16.553 / P2 02:35:16.565: event12410323 bank2005[6]
  commands for2411317/2411318.
- P2 02:36:23.117 / P1 02:36:23.185: same commands from12410322.
- Relay queues in this interval are empty with recent receive/progress.
  No evidence of a general relay stall in this interval.

Original1.09 m24_01_00_00.emevd.dcx read only from installed game:
event0 initializes lift2411320 with events12410321..12410325.
Parameters:12415350,12410350,12410351,12410330; trigger regions
2412322 for12410322 and2412321 for12410323; ObjAct flags12410320/12410321.
Both movement events combine flag prerequisites with an OR of
bank3[2](inside,character10000,region) and bank5[2](ObjAct flag), then
request object animations, wait on bank3[7] for the region, restore lever
activation and clear the busy flag. Thus plate entry and lever interaction
are distinct trigger paths, although they share the movement event.

## Limits and next discriminating observation

ObserveBbscNativeWorldCommand deduplicates by(instance,instruction) per load;
it logs bank2005 and selected bank2004 commands, not the bank3[2] condition
result or bank2003[18] object animations. These lines do NOT identify who
triggered the lift, whether by lever or plate, nor prove that the lower
plate's condition was evaluated correctly. Absence of subsequent lines is
not proof of inactivity. Exact root cause remains unproven.

Need a bounded trace of12410322/12410323: resolved region/character,
condition result, flags12415350/12410350/12410351/12410330, movement/idle
animation entry and region-clear wait, correlated with the lower-plate
attempt and actual native role. Do not globally force region checks true,
guess a host-only gate, or infer a permanent busy flag from these logs.
No saves, settings or game assets changed; games not terminated.
