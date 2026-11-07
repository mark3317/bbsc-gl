# 06.11.2026 — native NPC baseline, guest deny list and Dream scan removal

User requested v1.2-level performance, removal of expensive post-release
processing, retention of lamp travel for everybody, then explicitly approved
default-allow local host interactions with a deny list: ending/NG+, host cup
deletion/replacement and whole-session termination remain host-owned.

## Concrete regression found

Compare actual release bdd59b7 with current TickBbscDream. In1.2,
StartBbscToolScan was conditional on !BbscDreamOwnEnabled(). Removing the
own-Dream mode made that call unconditional on entering the host's Dream.
Its detached worker called FindInMemory three times, once per tool, searching
every committed readable region up to1TiB (8 hits maximum, not8 pages).
memchr/memcmp touch those regions, including mapped/shared allocations.
The worker is outside BBSC per-frame scopes. Low callback times therefore
could not rule it out; disabling independent NPC hooks did not disable it.

This is a specific newly activated full-process traversal, consistent with
the guest-only working-set expansion (~3.6→13GiB PC, ~3.2→14GiB laptop) and
CPU/memory contention. It does NOT prove a private heap leak, nor assign all
observed FPS loss to this one worker. Corrected gameplay measurement is OPEN.

## Removed work / original path

| Boundary | Before | Now |
| --- | --- | --- |
| Guest enters host Dream | 3 global memory scans, retained byte-patch sites, detached worker | 0 scans, 0 worker, no ESD byte patches |
| Workshop tools | periodic tool-site repair, workbench flag-grant callback | existing f47 result boundary, exact current native arguments only |
| Talk access | several allow lists, per-talk logging/state, repeated workshop snapshot/flag work | f19 native gate + one deny-list decision |
| Local type0 condition | allow-list searches and cached condition pointers | checked current event identity + deny list; native bit result |
| Native End/Jump host/client predicate | per-pickup/travel/kidnap EVD rewrites | one scoped native condition hook; original branch/End/Restart retained |
| New independent NPC pipeline | installed by default | not installed/ticked by default; original1.2 NPC path |
| Unrelated flag write | repeated live role checks for lamps/altars | integer/range predicates reject before querying role |

Workshop access still requires the host's actual tool flag. Only exact
f47(3,4102/4103/4104,0,1,0), the appropriate t210692/t210699, local actor,
Dream guest state, matching native frame and a6-element native argument
reader are accepted. Original1.09 leaves integer variants at RBP-1E0..220;
the callback reads5 existing16-byte variants. It neither grants an item nor
rewrites ESD. Unsupported argument types/shapes retain original behavior.

The native host/client predicate017B21A0 is overridden ONLY for bank1003
callers, exact native vtable0532D270, a current resolved allowed event and
requested state0/1. It writes original condition result bit+10; bank1003
reads that bit, not RAX. Other predicate states and network/authority callers
remain original. Type checks change only entity10000/type0; NPCs, other
entity/type predicates and actual session state are unchanged.

GuestAccess::EventAllowed denies3503,12100000,12100002,12100180,
12104800,12104850. Unknown identity is not permission to bypass the list.
Gehrman210305's ending phase and210306 keep the original talk block.
Empty/unknown host cup menus keep their host block. Existing native guest
altar menu/removal fences, altar-write protection and session-owner protocol
are retained. No blanket role change is applied to NPC simulation or saves.

NativeNpcSync now defaults ON when the variable is absent. Explicit
BBSC_NATIVE_NPC_SYNC_TEST=0 retains the old independent NPC pipeline for
diagnosis. Default capabilities fence mixed NPC modes. Default mode omits
block/history/HP/packet/ownership/wake and per-peer maintenance hooks/ticks,
uses exact1.2 LocalEvents50 and legacy player recovery/scaling. Travel,
presence, lamp catalog, native lamp animation/load/warp and local command
isolation remain enabled. This is NOT a complete1.2 source rollback.

Altar dirty detection still includes9020..26 and mounted lamp flags129078xx,
not just94xxxxxx records. Host-vs-guest inventory rules remain separate from
the host-interaction deny list.

## Verification

- test_guest_access: actual f19, type0 and shared native host/client callbacks;
  default allow, exclusions, malformed/unknown context, NPC/remote/host
  negatives, original ELF stack ABI/vtable/result-bit instructions PASS.
- test_world_travel_native: actual ESD entry/result, workshop predicates,
  both actor contexts, malformed count/frame/arguments, native travel PASS.
- test_native_npc_sync_mode: full mode0, native mode1 and UNSET/default;
  actual install+2000 ticks, no new NPC calls, lamps retained, LocalEvents50,
  mixed-peer fence, native pre-event bootstrap PASS.
- test_lamp_dream_returns, test_world_altars_native, original ESD survey:
  46 ordinary/DLC+10 chalice lamps, both roles, snapshots/local commands,
  catalog/getter ABI and host selected-altar/lamp dirty writes PASS.
- test_native_transition_access + original EMEVD, test_snatcher_abduction
  +original EMEVD, test_cainhurst_reveal, test_dream_finale_static PASS.
- test_scripted_pickups and test_event_identity_hotpath in explicit full
  NPC mode0 PASS; native-mode localization is verified separately above.
  test_death_hotpaths and production Windows trampoline test_hook_resume PASS.
- Final DLL build exit0,8 inherited warnings; input metadata unchanged during
  final build. No broad discover or real save/recovery tests.

Historical fixture assertions expecting an EVD rewrite/allow list were updated
to the new contract. During development the full-mode pickup test was first
run with the newly changed default, then selected explicitly as mode0. A wrong
original-data root was corrected and only the asset survey rerun. No failed
attempt is counted as PASS.

## Installation and next measurement

Seven-file fast delta installed on PC exit0: three mod files, bundle/SOURCE,
Party compat and chalices (direct runtime dependencies over the1.2 install).
Backup D:/Games/Bloodborne/coop-dev/backups/native-access-v120-20261106-214414.
Original1.2 and prior new-build logs preserved before replacing binaries.
User profiles/settings/saves, game assets, HEAD/pin and other chats' changes
preserved; no games terminated, no laptop/VPS changes, no commit/push.

Run parent out/coop-dev/runs/native-access-v120-20261106. Player1/2 launched
21:44:30 MSK, same process-only uncap/165 and profile diagnostic settings.
Startup/gameplay status is recorded in run.md; FPS after join still OPEN.
The same1.2 scenario must confirm FPS and memory before calling this resolved.
