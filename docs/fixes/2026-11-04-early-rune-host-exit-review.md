# 04.11.2026 — early rune and host exit review

Status: investigation only. User reports an early rune beside the window/lamp and
host appearing at the game start behind Iosefka's closed room after menu exit.
No code/build/deploy/settings/save changes. Logs copied to parent
out/coop-dev/runs/early-rune-host-exit-review-20261104 (text logs only).

## Latest main-profile evidence

Actual user_dir from settings and launch header is LocalAppData/Bloodborne Game
Launcher/twin. last_run.log runs from about 00:30 to 00:56:32 MSK, runner28424
exit0. Diagnostics are disabled. No BBSC item/quest/quit/placement trace exists
in this log. last_run.1.log at00:24:28 is a startup WinError32, not a completed
previous game. D:/Games/Bloodborne/twin/last_run.log ends00:58:18 and has no Party
launch header; it is a separate run and must not be merged with the co-op one.
Neither latest file proves the rune identity, its gate state or clinic spawn.

## Last two local three-player runs

23:23 and23:43 runs are a different test cohort, in Old Yharnam (map17000000).
Player2 latest: native menu confirm23:45:05.404, native save complete and Stop
23:45:05.460, final party leave and OnReturnTitle23:45:08.014, own-world character
creation23:45:28.286. Previous: confirm23:25:20.078, title request23:25:21.498,
character creation23:26:05.093. These traces show character construction after a
title request; they do not observe a Continue press, absence of input, actual
title arrival or final coordinates. Do not infer automatic clinic respawn from
this line alone.

Both runs explicitly log title submission WITHOUT world reload. The previously
removed StageTransition call (2026-11-03-host-title-world-reload.md) therefore
cannot by itself explain the latest report. Installed DLL timestamp00:14:36.
The user-reported host exit regression remains OPEN; old fixture success is not
live verification. Further isolation needs the actual native title request/
StageFlow acknowledgement and competing load origin, plus destination placement.

## Early rune

Exact item and observing role remain unknown; clarification requested. Read-only
original m24_01 EMEVD confirms Gilbert-related1120..1124 progression and9800 gate
in12410733. This is NOT evidence those flags were incorrectly set in this run.
Current TickBbscGuestItemsPickable only hides taken/script-hidden items and does
not force disabled items on; the old blanket-enable mechanism has already been
removed. Do not reapply that historical fix or change all quest flags without
matching the reported item. Need item lot/object, host vs guest visibility and
its script/quest gate at time of appearance. No real save was read or modified.

## Follow-up: user identifies Clawmark

User confirms rune name: След когтя / Clawmark. Observing role remains unknown.
Read-only item data maps Clawmark name offset4 through GemeffectParam to lots
51000 (GemGen100501, get flag50003100),29010 (100502,50001300),34020/34040
(200000,50001820), and chalice sources. These are different tiers/sources;
name alone does not identify the exact awarded lot. NpcParam6340 references
lot51000. No matching actual award is recorded in the latest PC log.
Do not confuse Central Yharnam map treasure2410640/GemGen102903 with this rune:
its effect1134002 has name offset25, not Clawmark offset4.
Current guest enemy-death hook queues native NpcParam lots for dead non-bosses;
matching the actual enemy and death origin is required before attributing the
reported early rune to that path. No production change made on this evidence.

## Follow-up: both host and guest observed the rune

User confirms Clawmark appeared for BOTH host and client. This makes a defect
limited to guest-only automatic drop delivery insufficient to explain the whole
report. Prioritize the actual host-side source/quest state and native drop or
map item visibility, then compare guest behavior. This does not prove that the
host's progression was corrupted, that both got the same lot, or that either
actually picked it up: user's answer establishes both observed availability.
Exact runtime gate/death source remains unrecorded with diagnostics disabled.

## 04.11 follow-up: guest-only origin remains possible; source audit

User qualifies prior observation: the host had also been a client, so BOTH
observations do NOT establish two independent host/client grant paths. Earlier
host-source prioritization is superseded; guest-only acquisition is plausible.

Correct specific source from original game data: m24_01 NPC entity2410781,
modelc1091 / NpcParam109100 -> ItemLot29010 -> GemGen100502, Clawmark,
receipt flag50001300. Previous references to lot51000/NpcParam6340 and Gilbert
flags1120..1124 identify other NPC chains and are NOT the matching window source.
Those were name-only candidates, not identification of this rune source.

Actual script conditions:
-12410762 handles Gilbert progression1240..1246 from time flags9800..9802 and
personal dialogue72410504; the transformed phase ends in1246.
-12410761 waits for entity2410781 dead, clears1240..1259, sets1245 and saves.
It is in BbscGuestGiftEvents, so guest type0 gating is overridden.
-12410760 selects character state:1240..1244 hide the beast,1246 enables it,
1245 disables it and executes2004[37] ForceCharacterTreasure(entity2410781).
Its initial host-type check jumps over talk resets to label0; it does NOT gate
this entire state/treasure body. It is not a local event (network-sync setting
is not overridden). Adding it to LocalEvents alone is not a proven correction.

Concrete production mismatch: BbscNpcQuestFlags includes1240..1245 but NOT1246,
although12410762 writes1246. KeepBbscNpcOwnBits/RevertBbscNpcOwnFlags therefore
do not protect that phase as personal state. This is a confirmed coverage gap,
not proof it produced the early drop in the reported run.

Guest automatic death delivery: NoteBbscGuestEnemyDeath is called at native
KillRewardEntry018C5070, requires guest host-world/type1, non-player, excluded
actor bits clear, valid native row, non-boss; queues the first two NpcParam lots.
It does not independently check Gilbert quest stage, whether the entity was
legitimately enabled, HP, or pre/post transformation. TickBbscGuestDrops requires
still a living loaded guest. GiveBbscGuestDrop uses item weights, receipt flag,
and native guest-goods duplication guard; gems/runes go through native award.
No separate quest-stage check exists there. This is reliance on native death
caller correctness, not proof that absent/hidden entities trigger that caller.
Pickup/award hooks likewise trust the native/script source for availability;
retro repair is goods-only and is NOT a direct Clawmark grant path. Rune award
receipt and home-award fallback can outlive the guest role; role change alone
does not imply a second grant.

White ribbon analogy:12410702 controls an MSB object/treasure via2005[4]; the old
periodic pickability repair overrode explicit hiding. Current pass only hides,
so that proven old mechanism is absent. Gilbert is an NPC treasure/death branch,
which the SetTreasureState caller-specific hidden-item hook does not validate.

Data/source assertions PASS; output in parent run/code-conditions.txt. No code,
product build/deploy or save change. Open runtime questions: did1245 become true
prematurely, did native ForceCharacterTreasure run under a mismatched/shared
state, or did the native death reward path queue29010 for a hidden actor?
Need trace of source event,1240..1246, actor state and actual lot award to decide;
existing latest PC log does not contain those observations.
