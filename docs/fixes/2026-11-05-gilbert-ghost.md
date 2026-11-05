# 05.11.2026 — Gilbert ghost / personal NPC native event authority

Status: SOURCE corrected, gameplay OPEN. User explicitly clarifies Gilbert must
be absent for BOTH players at this stage; quests remain personal. No new
Gilbert/stage/visibility predicates, actor writes, or shared quest flags added.

## Correction and validation

The existing local-event catalogue included Gilbert's personal flag workers
12410761/62/63 but omitted original state dispatcher12410760. The same gap
affected all19 previously reviewed personal NPC dispatchers (28 actor variants).
They could still send native channel31 progress, carrying an instruction index
and condition results from another player's execution. Flag protection alone
does not isolate that native event execution.

The event generator now reuses those existing original-data controller identities
and includes them in the EXISTING native event localization. Catalogue50->69;
all40 scripted lot flags unchanged. No added runtime decision about NPC stages:
original EMEVD conditions, character/object instructions, AI authority, native
CHR initial admission and existing reward guards remain unchanged. Source game
files were read only. Both roles use the existing localization before event steps.

- New tools/test_personal_npc_dispatch.py FAILS old production catalogue.
  Corrected production PASSes all19 controllers, every fixture instruction,
  reused instance and shared boss/ordinary-event exclusions.
- The test executes COMPLETE ORIGINAL1.09 native progress sender012EE540 on
  allocated memory. Unlocalized controller sends channel31; production-localized
  controller sends none. Only native external transport/member/global storage
  are fixture stand-ins; original sender branches/packet construction execute.
  Production localization changes only event+78, no actor/stage mutation.
- quest_event_rules.py --check against original game data PASS;
  test_personal_reward_authority.py and test_scripted_pickups.py PASS.

This reproduces and corrects a native event-authority gap; the old live logs do
not prove which exact incoming event instruction exposed Gilbert in that run.
Gameplay remains OPEN: guest enters first with Gilbert absent by personal quest,
then host arrives; absent on BOTH screens throughout, no invisible attacks.
Do not claim the streaming wait fix alone covers this case.

Build/deploy/start status is recorded separately in HANDOFF and parent run notes.
No save edits, game-asset writes, running-game termination or push.

## Earlier live diagnosis (historical source-only status)

Collected both current profiles with collect-logs.ps1, exit0, 2 files, warnings0:
parent out/coop-dev/runs/gilbert-enemy-20261105/pc. Both files have
ChangedDuringCopy=true: live snapshots, not final logs. P1 guest run222014;
P2 host run222015. Shared source HEAD/pin db9a6b9; working tree already contains
other ongoing changes. Installed session started22:20, before later source-only
streaming correction. Do not assume current dirty source is installed.

User observes: guest enters Yharnam and sees an unresponsive, unhittable beast
at Gilbert's window; after host arrives it attacks the host on the guest screen,
while absent on the host screen. Actor identity2410781 is inferred from location
and report, not an entity ID captured by this run's logs.

Latest matching travel sequence (MSK):

- Guest native world ready m24_01 load17 at22:50:28.686; AREA/arrival22:50:33.754.
- Host AREA/arrival m24_01 load13 at22:51:11.293.
- Host native CHR initial applied22:51:11.357 from owner c6b2815f (P1 guest),
  request4; native world ready at the same time. Host arrival therefore did not
  simply make the session host the map-state provider.
- Earlier same-order arrivals22:22:07.398 guest /22:22:28.763 host similarly
  show host receiving native initial state from guest22:22:28.823.
- Guest talk t241319 records1245=1 at22:22:07.551 and again22:24:57.711 /
  22:33:19.660. These are earlier writes, not a full current flag snapshot.

Original controller12410760 disables beast2410781 for1240..1244 and1245;
1246 enables it.1245 is the terminal death/treasure branch. Original behavior
was previously inspected in fixes/2026-11-04-early-rune-host-exit-review.md;
current generated quest rules retain first-match conditions. Thus the earlier
guest1245 writes support an absent beast, not an expected living personal NPC.

## Source investigation and limits

BbscWorldOwnership applies one map authority to all awake non-player characters
(Doll exception), without separating personal quest NPCs. ChooseOwner retains
a present resident. Native initial/replication and personal NPC event visibility
therefore intersect at this actor. Personal quest protections/reward guards
alone do not establish identical native actor enable/death state on both peers.
This is a concrete boundary to investigate, not a proven execution trace of
the ghost or proof of a specific flag overwrite.

Latest guest load17 already logs native world ready BEFORE host arrival. Its
initial inert beast cannot be diagnosed solely as waiting for visitor bootstrap;
the existing streaming-superset correction does not prove this case fixed.

Logs do not capture2410781 enable/disable, draw, AI ownership, HP, native state
changes, or full1240..1259 at the reported instant. They establish travel order
and provider, not which operation exposed/reactivated the beast. Next diagnosis
must correlate native actor state with12410760 and the personal quest flags,
including first entrant alone and later host arrival. Expected result: absent
on both screens, with no attacks/collision/rewards from an absent actor.
