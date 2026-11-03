# 04.11.2026 — personal quest death and NPC treasure prerequisites

Status: source corrected; real native predicate/trampoline and production-function fixtures PASS; full BBSC_MOD translation-unit syntax PASS. No product DLL build, deployment or gameplay run in this task. User saves/settings and game files unchanged.

## Cause and strength of evidence

The mod separates personal NPC quest flags from the host world, but permits selected host-only quest workers to run as a guest. Those workers consume the native death state of the shared/replicated actor. Native bank4[0] has no knowledge of the guest's personal quest phase: a dead actor can therefore satisfy a death worker although this player's state dispatcher would hide that actor. The worker advances the personal quest and can cause a forced NPC treasure or a direct automatic drop. Retaining the resulting award after changing from guest to host does not establish an independent host-side grant.

Concrete Gilbert chain from original CUSA03173 1.09: entity2410781/NpcParam109100 -> lot29010/GemGen100502, receipt50001300. Guest-enabled12410761 consumes death and sets1245.12410760 hides the actor in1240..1244, enables it in1246, and forces treasure in1245.1246 was absent from personal flag protection. A single permission change to12410760 would only alter its initial dialogue resets, not repair this authority mismatch.

The fixture executes the COMPLETE native CharacterDead evaluator0179F940 including its switch table, with a fake replicated dead actor and initial personal1240. Original code returns true. Through the production trampoline and production guard it returns false; valid1246/1245 and genuine alive/dead outcomes are retained. This reproduces the unsafe code path, not the undocumented network history of the old run. Latest old PC diagnostics were disabled; which exact input first changed in that run cannot be proven retroactively.

## Correction

- Generate ordered NPC state prerequisites from original EMEVD, including native first-match semantics, AnyOn ranges and resolved InitializeEvent parameters. Explore unknown subconditions conservatively: deny only when every possible path keeps the actor inactive. Unknown/default actor state and opaque child effects are never guessed.
- Validate the reviewed shared-tail workers: child activation of a parent actor must first select a parent-permitted personal state. Separately derive two secondary actors from their positive quest waits and native death terminal states.
- Gate positive native death predicates before a guest quest worker can advance the wrong personal quest. Do not fabricate death; alive tests, edge predicates, host/offline behavior, ordinary enemies and the feature-off path remain native.
- Gate automatic guest death delivery and native forced NPC treasure. Resolve actor pointers with native013C97A0; Chr+278/+27C are multiplayer area IDs and are NOT used as actor identity.
- Derive receipt-to-source associations from original MSB/NpcParam/ItemLotParam. Guard native item enable, the existing periodic hide-only pass, guest award and direct lot delivery. A shared receipt is allowed if at least one legitimate source state allows it. The value of a receipt flag alone never authorizes a reward.
- Keep every state used by these gates personal, including previously missed1246 and analogous stages. Unrelated condition checks use a cheap known-entity prefilter; no native NPC lookup in the per-frame condition predicate.
- Reuse the existing bank2004 hook for forced-treasure filtering, preserving its original free-bell refund filter and using the native OFF path when denying item visibility. Never globally enable treasures. No inventory removals or retroactive save/quest rollback.

## Coverage

28 concrete NPC actors, 19 reviewed state/activation controllers, 24 receipt/source associations. All identified guest-enabled literal NPC-death -> forced-treasure chains are covered except2400700, the reviewed ordinary present-from-start NPC path (no future hidden quest variant). The generator asserts this coverage, so a newly enabled death worker cannot silently escape the same review.

| Actor | Original controller | Allowed-state review |
|---|---|---|
| 2400730 | 12400500 | 1181, 1184, 1185, 1186, 1188, 1191, 1183 |
| 2400732 | 12400500 | 1189, 1189 |
| 2400750 | 12400520 | 1224, 1222, 1230, 1231 |
| 2400755 | 12400610 | 1205, 1206, 1207, 1210 |
| 2400760 | 12400590 | 1340, 1341, 1342 |
| 2400762 | 12400590 | 1343 |
| 2400763 | 12400590 | 1344, 1345, 1346, 1347 |
| 2400765 | 12400560 | 1161, 1164, 1165, 1166, 1167 |
| 2400770 | 12400900 | 1304, 1305, 1312, 1303 |
| 2400775 | 12400900 | 1308, 1317 |
| 2400900 | 12400650 | 1369, 1368, 1362, 1363, 1364 |
| 2400901 | 12400655 | 1370, 1371 |
| 2400902 | 12400650 | 1372, 1369, 1368 |
| 2400903 | 12400650 | 1371, 1370, 1369, 1368 |
| 2410770 | 12410830 | 1228, 1229, 1235, 1236 |
| 2410771 | 12410830 | 1228, 1229, 1235, 1236 |
| 2410781 | 12410760 | 1246, 1245 |
| 2410900 | 12410800 | 1369, 1368, 1367, 1366, 1365, 1360, 1361 |
| 2410901 | 12410809 | 1363, 1364, 1365, 1366, 1367, 1368, 1369 |
| 2500790 | 12500050 | 1348, 1349, 1350, 1351 |
| 2700755 | 12700700 | 1200, 1201, 1202, 1203, 1208, 1209 |
| 2700912 | 12700901 | 1800, 1801, 1805, 1790 |
| 2800670 | 12800911 | 1300, 1301, 1311, 1315, 1313, 1314 |
| 2800671 | 12800911 | 1310 |
| 3400902 | 13400950 | 1720, 1725, 1710 |
| 3400903 | 13400950 | 1721, 1726, 1711 |
| 3500900 | 13500950 | 1722, 1727, 1712 |
| 3500910 | 13500960 | 1760, 1761, 1750 |

Other original forced-treasure event definitions are retained with their native conditions. Some are generic enemy/corpse or boss paths, some use an actor already guarded by another reviewed controller; opaque multi-event effects are not broadly enabled or rewritten. This audit does not claim a live full-game quest playthrough.

## White/red ribbons and map treasure

White ribbon is the separate12410702 / object2410851 / SetTreasureState2005[4] path. Its original hide-until1273 rule and caller-specific hidden-object tracking remain. The production periodic pass was exercised: it never enables a disabled quest treasure or closed-chest pickup, respects script hides, preserves a legitimate enable, handles taken flags and recycled numeric item IDs. Red-ribbon gate72410410 remains in the generated40 scripted-lot flags; existing retro logic must not infer receipt from it. The new NPC gate does not turn either availability gate into proof of acquisition.

## Validation

- `BB_GAME=<original dvdroot_ps4> python tools/test_quest_rewards.py ../../out/exit-study.elf`: PASS. Complete native death evaluator + production trampoline/hook; initial/no-state/mixed-state rejection, all generated actor states, valid late deaths, feature-off/host/unrelated paths, automatic drop, forced treasure, native/network visibility, normal late enable, ribbons/chests/taken/recycled-item paths. Extractor tests retain potentially legitimate conditional paths and reject unknown defaults/callees. Guard flags checked sorted/unique/count-correct and complete.
- `quest_reward_rules.py --check`: PASS against original EMEVD/MSB/NpcParam/ItemLotParam. `quest_event_rules.py --check`: PASS, existing16 personal events/40 scripted-lot gates unchanged.
- `test_hook_resume.py`: PASS (production trampoline); `test_cainhurst_reveal.py`: PASS (personal NPC protection direct regression).
- Full `bloodborne_re.cpp`, BBSC_MOD C++23 syntax: exit0; `git diff --check`: exit0.

## Gameplay check after a coordinated build

Use a clean TEST character/profile copy, not a rollback of the user's live save. At initial personal phase, join/rejoin and exchange host role: no Gilbert rune/glint or future quest corpse reward. At legitimate transformed/dead phase: Clawmark remains obtainable once. Check an ordinary enemy drop, legitimate NPC death reward, white ribbon before/after1273, unopened chest and a normal pickup. Already incorrectly earned inventory/quest state is deliberately not deleted by this patch.

RangeState.AnyOn=2 was cross-checked with the primary Soulstruct Bloodborne enum definitions: https://raw.githubusercontent.com/Grimrukh/soulstruct/master/src/soulstruct/bloodborne/events/enums.py . Actual rules and tests use the local original game data.
