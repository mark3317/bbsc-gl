# 05.11.2026 — Gilbert ghost / personal NPC native event authority

Status: installed4989896 FAILED the reported gameplay check. Further native
continuation isolation corrected in SOURCE; exact live scene/gameplay OPEN.
User explicitly clarifies Gilbert must
be absent for BOTH players at this stage; quests remain personal. No new
Gilbert/stage/visibility predicates, actor writes, or shared quest flags added.

## Further diagnosis/correction: native remote continuation bypass

User clarifies spatial dependency: first resident was far from the lamp;
entrant saw Gilbert and a closed door. When the resident approached, Gilbert
disappeared and door opened without animation. Do not infer a legitimate
personal stage difference or add stage predicates from this observation.

Both current230550 profiles recollected under parent
out/coop-dev/runs/gilbert-native-stage-20261105/pc (2 files, warnings0,
ChangedDuringCopy=true). Read-only process samples in that parent run resolve
2410781 through original native entity-table layout: personal1240=true,
1246=false, native backread-off Chr+28=1, activation current/requested0/0 in BOTH
processes. Original MSB confirms c1091_0000 at Gilbert's window. These samples
are later than the reported frame; resource/draw allocation alone does not prove
visible rasterization. No live process memory or save writes were made.

Concrete uncovered original1.09 control flow:

-012EE540 sends kind1 channel31 condition progress and checks event+78.
-012EE660 sends kind2 timed continuation unconditionally, ignoring+78. Native
 bank1000 timed wait dispatch calls it at017C7C2B. Native restarts can also
 restore+78 after the mod's pre-update localization.
-012EE420 virtual receiver (event vtable05366880+28, resolved read-only) accepts
 kind2 even for a local event, writing source+60, pending step+4C and the condition
 bitmap at[event+20]. It has no+78 test.
-012ECE95 compares current step+48 to received step+4C and sets native mode2
 (execute command) even if the local condition result was FALSE (mode0).

This is a reproduced cause of personal conditional execution bypass; flags can
remain personal/correct while remote event execution authorizes the command.
The prior test exercised ONLY012EE540 with a stable+78=0 and missed this path.
The captured old live logs do not identify which packet/instruction caused the
specific Gilbert or door frame. Do not claim complete live causality from the
fixture alone; the new diagnostics are needed for that association.

Correction in emulator/src/core/bbsc_personal_events.inc:

- Both native emitter entries suppress only the EXISTING personal-event
 catalogue while personal quests are active (host/join/guest). Native local
 branches, waits, actor commands and quest flags are untouched.
- Original channel31 native Receive callsite012F1744 wraps the SAME01789200
 receive, consuming personal kind1/2 records before event application. Native
 reliable transport/ACK/sequence assignment is unchanged. Up to8 queued personal
 records can drain per call, then the next normal native frame continues.
- Shared door/boss events, malformed/unknown messages, feature-off and offline
 behavior remain native. No new NPC identity or stage allowlist is introduced.
- Existing timeline switch controls bounded per-load transport/event/native
 command observations. Character5/29 results log native backread/activation;
 object2005 commands and changed snapshot flags record world-state application.
 Log operands are observations only, never decisions about appearance.

Validation: tools/test_personal_event_transport.py executes COMPLETE original
012EE660 and012EE420, original012ECE95 decision instructions and REAL production
Windows send/receive trampolines on allocated memory. BEFORE isolation, event
net=0 still sends, receiver changes pending step/bitmap, FALSE condition becomes
execute mode2. AFTER isolation, personal input cannot reach native application
and the false local condition remains false. Both message kinds/all69 events,
host/join/guest, reset+78=1, feature-off/offline/shared door, malformed data and
bounded drain PASS. Existing personal NPC dispatcher, scripted pickup and native
bootstrap fixtures PASS. Full BBSC_MOD/relay syntax PASS. No product DLL build,
deployment, restart or gameplay assertion: both game processes remain running.

## 23:09 host-only Yharnam return: symptom persists after installation

User reports Gilbert appeared for the host after load. Both fresh230550 logs
collected in parent out/coop-dev/runs/gilbert-host-followup-20261105/pc, 2 files,
warnings0, ChangedDuringCopy=true. P1 guest / P2 host; both35/35 hooks at start.

Host requests2412951 at23:09:01.852; native world-ready m24_01 load3 at
23:09:02.713; AREA23:09:06.749 / arrival23:09:06.750. Guest remains Dream
after23:07:25.130 through collection23:09:52. There is no native CHR-initial
application log for host load3, whereas earlier host Dream load2 logs it normally.
This is not the previous guest-first/resident-provider arrival sequence.

No current1240..1259 snapshot, original12410760 instruction trace or2410781
enable/backread/AI trace exists in this capture. Appearance is user-observed;
exact actor identity and state transition are not independently logged.
The event-localization correction below does NOT establish a fix of the reported
symptom; gameplay failed. Need investigate local quest-state restoration and
native controller/actor lifecycle, without added stage gates or forced hiding.
No new behavior changes, build/deploy/restart, save or game-asset writes.

## Earlier correction and fixture validation (gameplay insufficient)

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

Deployment: own source4989896 / parent pind77cae9 plus completed shared dirty
source (provenance source_dirty=true). DLL/delta/deploy exit0. Parent run:
out/coop-dev/runs/personal-npc-2p-20261105. Backup:
D:/Games/Bloodborne/coop-dev/backups/personal-npc-2p-20261105-20261105-230526.
Player1/2 wrappers launched23:05:26; both fresh230550 logs report35/35 hooks,
independent enemies/travel=true23:05:51. Two native game processes started;
this establishes startup, not the reported scene's gameplay outcome.

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
