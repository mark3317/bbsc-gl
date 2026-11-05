# Every retained death uses native processing — 04.11.2026

Status: SOURCE ONLY. No DLL build/deploy, restart, real save/settings/journal edits,
pin update, commit or push. Existing games were not stopped. In-game confirmation
of the death text and poison/other status reset remains OPEN.

## Latest run and scope

User reports that a subsequent guest death has no «Вы погибли» and retains
poison/other effects; requests the original game handler for every death.
This supersedes the earlier text-only workaround in
`2026-11-04-repeat-client-death.md`, installed at 12:28 before this run.

Read all three current Player 1/2/3 profiles from the 12:32 launch, 60 FPS,
upscaler/frame generation off. Snapshots are in the parent repository at
`out/coop-dev/runs/repeat-death-effects-20261104/pc`. Games were still running
at collection (12:40 MSK); all three entries have ChangedDuringCopy=true.
These are live snapshots, not final game logs. BBSC detailed death diagnostics
were off, so they cannot establish exact first/second death times or the
individual effect flags. Do not infer the affected client number from its profile.

The source did prove different paths: first native death ran the original
SoloPlayDeath/PartyGhostDeath chain and final step; repeated HP death called a
standalone text event followed by BeginBbscCoopDeath, bypassing that chain.
Giving this substitute more time could not make the two paths equivalent.

## Original game code checked read-only

Original CUSA03173 1.09 ELF in parent `out/register-study.elf`:

- Map initialization 0137D8D3..0137D91B registers death group99999 for local
  entity10000: `OnEvent_4000` through01329B70 (once=false) and
  `OnEvent_4000_Hp` through01329D30 (once=true, threshold0.0, event mode+8A=0).
- Binding at0138DA4F maps OnEvent_4000 to013813D0. This native dispatcher chooses
  the original host/guest death scripts; the HP callback alone is insufficient.
- Contrary to the old mod comment, PartyGhostDeath_wait at01382070 submits
  native YOU DIED through0132EAD0 at013820DD. The mod's entry-hook text injection
  is not required to run the native guest sequence.
- Native DeleteEvent0132F030 retires event/condition entries for one supplied
  group. Group99999 identifies these detectors; death continuation timers4000,
  text listeners and unrelated map/NPC event groups are not retired.

## Implementation

After a retained native final death step, remember actor/global/load generation.
Once the same actor is revived in place and the old death guard is cleared,
use native DeleteEvent and the two native registration APIs to recreate only
the original detectors. Do not rerun map initialization or call callbacks with
fabricated death arguments. First life and genuine loads keep their ordinary
native initialization. Host/guest, boss/wipe/invasion decisions and the existing
retained-session respawn remain downstream of native death processing.

Each accepted registration is remembered; declined registrations retry only the
missing half at most every500ms. A rapid death during a partial failure can
complete the missing registration, still through native event dispatch. Context,
actor/load/session replacement discards stale attempts; title/quit/loading and
missing managers prevent calls. Native API prologues are checked before use.

Removed the standalone death-text injection, artificial repeat-effect timer and
watchdog handoff to BeginBbscCoopDeath. The watchdog now only reports a stalled
native handler. The mod does not implement a separate poison/effect-removal list:
the same original death sequence owns those semantics on every life.

## Verification

- `tools/test_repeat_death.py`: extracted production registration and lifecycle,
  three retained host and guest lives, one registration per life, partial failures
  and rapid next death, actor/global/load/session/quit/title/manager guards PASS.
  Its fixture deliberately supplies no synthetic text/death/penalty entry stubs;
  the lifecycle cannot bypass native dispatch to such an entry.
- The same test checks original ELF call targets, entity/group/once arguments,
  native API signatures, the OnEvent_4000 binding and native guest YOU DIED call.
- `tools/test_death_hotpaths.py`: inventory, cache and Dream guards PASS; obsolete
  text-injection assertions removed with the deleted implementation.
- `tools/test_death_accounting.py`: existing native drop/restock control PASS.
- Complete `bloodborne_re.cpp` BBSC_MOD syntax check: exit0.

The fixture checks registration/control flow, not actual native character effects
or visible UI. A later game run must confirm first/second/third deaths under poison,
the same native text/effect duration, native status resets and normal retained
co-op/boss/wipe behavior. Do not call the gameplay bug closed by these checks.
