> 07.11: Hall-only fallback заменён чтением исторических ламп через native mapper.
> См. [новое исправление](2026-11-07-chalice-native-lamp-catalog.md); игровой результат OPEN.

# Guest host-cup menu lamp leakage — 06.11.2026, SOURCE corrected; gameplay OPEN

## Implemented after user clarification

User clarified: incorrect rows occur before the host enters/lights the first
lamp; guests should see only the Hall of the Seal when no lamps are known.
This supersedes the broader initial proposed catalog reconstruction below.

BbscWorldSelectLampMenu now replaces BOTH lit and menu-unlock bits for guests
even when the selected ritual has no confirmed discovery mask. Missing and
explicit-zero masks expose only the original unconditional Hall row. Personal
bits are backed up by the existing projection path. Host native unknown-state
view is unchanged. Confirmed discoveries use the existing canonical session
mask with full world/dungeon/ritual identity.

BbscWorldAltarLampUnlocked independently checks that same scoped mask when
QueueBbscWorldTravel admits a guest layer request. The Hall remains allowed;
unconfirmed destinations cannot be authorized by stale personal native flags,
even if those flags are rewritten after menu construction. Host travel retains
its original native flag check. No new UI rows, warp/animation changes or wire
format changes. Broader transmission of historical unobserved host lamp state
was not implemented: the requested fallback deliberately shows the Hall until
the existing session pipeline confirms that ritual's lamps.

Validation PASS: production lamp fixture (all10 stale personal bits, absent/
zero mask, pending-only proposal, first confirmed discovery, replacement
ritual, different world, personal backup, host fallback); production travel
queue with actual scoped lookup and an intentionally all-true personal flag
getter (Hall accepted, locked layer rejected, confirmed layer accepted).
Restoring old menu behavior and separately bypassing the new admission check
both FAIL these regressions in allocated memory, without reverting source.
Real Windows menu trampoline and native host-helper fixtures PASS, including
read-only original1.09 byte/ABI checks. Original seven altar scripts/ten layer
choices and native lamp/travel ESD checks PASS. Full MOD/relay syntax exit0,
existing CRT warnings; build/guest-cup-menu-syntax.log. Diff whitespace PASS.

No DLL build/install, game termination or real save/settings/game-asset edits.
Gameplay/visual confirmation remains OPEN: guest opens an unvisited host cup
with no session lamp data -> only Hall; entering Hall works; host lights lamp
-> reopen menu and see confirmed destinations. Switching cups must not carry
the previous cup's list. HEAD/pin4989896 unchanged, no mixed commit or push.

## Earlier investigation (historical)

User reports P1 guest sees personal-cup destinations in the host cup menu,
can travel to unavailable lamps; the dungeon itself is correct. Screenshot:
Pthumerian Labyrinth, Hall, Layer1/Heart, Layer2/Heart and Layer3.

Collected live P1/P2 run_20261106_014900.log in parent
out/coop-dev/runs/guest-cup-menu-20261106/pc; 2 files, warnings0,
both ChangedDuringCopy=true. P1 guest/P2 host, installed01:48 run.
Source HEAD and parent pin4989896; shared dirty tree preserved.

## Evidence

- P1 01:56:35.884, 01:57:24.570, 01:58:50.649 and 01:59:33.537:
  native layer menu slot1, host channel0x81fce924a8ab2, personal_state5.
- P2 01:57:22.060 selects slot1/ritual34; native stage01:57:26.122
  point2902950 (Hall).
- P1 01:59:35.700 selects the SAME slot1/ritual34. At01:59:39.862
  request2902951 accepted, original flag72100301 released39.864,
  native stage39.880. Borrowed loader injected40.444:
  channel2286771891767986, revision34, layout0x1d0a5a00.
  Dungeon event admission01:59:44.676. This confirms host ritual loading,
  not accidental personal dungeon loading. The accepted destination alone
  does not prove that specific lamp was locked for the host.

## Source findings and limits

BbscWorldSelectLampMenu in bbsc_world_lamps.inc replaces runtime lamp flags
only if bbsc_world_lamps contains that exact world/dungeon/ritual scope.
Missing scope explicitly retains native current flags. Thus guest personal
or previous-cup flags can survive this boundary. Zero discoveries are not
sent by TickBbscWorldLamps, and host Dream seeding covers ordinary lamps,
not all catalogued ritual discoveries. A missing map entry is not proof of
an authoritative empty ritual.

QueueBbscWorldTravel in bbsc_world_travel.inc validates non-Hall layers via
global12907810+20*layer; it does not independently verify selected host
ritual progress. A stale menu flag can therefore authorize actual travel.
Existing test_world_lamps covers switching between TWO KNOWN masks, not
unknown/zero host ritual versus a progressed personal cup.

No per-ritual mask/row-condition dump exists in this capture. The exact
producer/read path of the extra screenshot rows and native visual mismatch
remain unproven. The missing-scope path is a source-backed explanation,
not an observed dump of the live flags.

Initially proposed correction (superseded by user's Hall-only fallback): derive a complete authoritative host ritual lamp view
from original altar progress, preserve known-zero versus unavailable, replace
personal bits before native list construction and validate layer admission
against that same ritual. Preserve native menu/travel/animation and personal
cup state. Merely clearing unknown masks would hide valid host lamps.

No gameplay code changes, tests, build/deploy, game termination or save edits.
