# Independent travel — development branch, 05.11.2026

## 05.11.2026 — native travel events and pre-event native admission

User requires original stone/lamp animation, loading and admission to the
already-resident player's world; chalice transition also failed in last run.

Travel now releases the original LOCAL native EMEVD command after destination
state is available. Original12107000/common7200 own animation, native wait,
menu completion and WarpNextStage_Bonfire. Removed direct StageTransition,
forced summon coordinates, manual respawn/aux writes, mass trigger clearing
and artificial enemy aggro. Native12107100 selects/prepares an occupied altar
and clears its first-half flag before ESD can request a layer; it is no longer
short-circuited. Four audited native travel events use native local sync and
verified EndIfClient->WaitFrames(0) in loaded memory; no game asset is edited.
Event identity is cached per native load, not linearly rescanned every frame.

Native WarpNextStage_Bonfire is now a functional entry hook. Arm the existing
native FirstSync reinsertion at the game's actual stage request, AFTER its
animation. Travel capability requires that hook. Ordinary host/guest bonfire
point selection uses the native path; no coordinate approximation. Native
completion generation is recorded before destination event updates.

The existing native event-update hook now holds destination instructions until
owner flags, complete enemy state (for an existing ordinary-map owner), and
native member FirstSync/CreateWait are ready. Apply flags ONCE before original
initialization, not after its cutscene/doors already started. Suppress new AI
authority and owner snapshot capture until the scene is ready; subsequent event
changes are not rewound. New travel prompts wait for that admission as well.
Native historical death seeding remains for newly streamed copies, without
position warps; live positions/combat remain the native owner's responsibility.

A movie/heartbeat pause no longer erases residency, changes the existing owner,
hides teammates or counts them as dead. Observed map load/leave/native departure
still changes residency. Curtain visibility is not a map departure. Cached world
responses preserve the actual owner's sequence/epoch; never invent a higher
coordinator sequence which would reject later legitimate owner updates.

Chalice geometry IDs now resolve to native m29_00 event-state scope, distinguished
by complete dungeon key and host ritual. A first unvisited ritual is initialized
by the game's own mounted host altar record, not unrelated live m29 flags. A
resident ritual requires its current owner's state. Personal altars/home policy
unchanged. Fixtures cover native FirstSync wait, missing/old owner state, story
before events, no repeated initialization, mounted ritual identity, silence and
explicit departure, actual native event release and animation-before-warp assets.
35 functional baseline sites; original native entry bytes/trampoline and targeted
fixtures PASS. New DLL build/deploy/start/game verification recorded separately;
all preceding gameplay failures remain OPEN pending the next manual run.


Final source c5b3b54: DLL rebuild and isolated-stage delta exit0. Backup
independent-native-arrival-20261105-194509. Requested two-profile startup
19:45:09 MSK: P1 run_20261105_194536.log/native16036, P2 run_20261105_194532.log/
native14328. Both enemy/travel hooks ready, local relay connected; no startup
fault. Native menu opening, independent return, actual models and late-join enemy
state still require manual gameplay confirmation. Main installation unchanged.
Evidence: parent out/coop-dev/runs/independent-native-arrival-20261105.

Altar menu follow-up: checked original installed m21 ESDs read-only. t210050
uses c1_78; t210060..210110 use c1_79 for occupied as well as empty altars.
The previous79->no-op rule directly blocked ordinary altar menus. Occupied
host altars now map BOTH78/79 to native headstone41 using their ten existing
layer choices; empty/unknown host altars reject both. Host native UI unchanged.
Production callback tests occupied79/empty79/host78 PASS. Original seven ESDs
validate native command IDs, ten layers and exact72100420..426 selection flags.
No game scripts edited. This supersedes the earlier claim that79 is empty-only.

## 05.11.2026 — late arrivals and native presence/travel corrections

User run19:09-19:29 failed: absent host model/name remained, host could not see
arriving guest, guest lamp return failed, host repeatedly returned to Dream
about7s after Yharnam arrival (also solo19:24:02->19:24:09). No crash; old MODEL
visible messages were not proof of a rendered mesh. Both games later closed.

Source changes:
- Native018C6390 presence switch replaces the insufficient render-byte hide;
  pair disable/enable and reconcile every remote actor even without an insert
  task. Retain native binding and bounded reconstruction. Render log now says
  repair requested, not visibly confirmed. The previous blanket avoidance of
  the native switch was too broad; its native cleanup needs paired enable.
- Observe completed load generation and curtain in presence before map ownership
  or rendering. Game tick may miss the entire load; the old map/visit must not
  authorize actors or capture Yharnam enemies into Dream's snapshot. World capture
  additionally requires agreement with the native current map and no load.
- Native c1_11 has an executor flag-range gate before SetFlag. A scoped visitor
  lamp request may pass that native gate to the local travel interceptor. Both
  host and guest use independent native stage requests. Consume invalid travel
  contexts locally, never broadcast them into another player's native event.
  Intercept before personal journal hooks; one-shot travel flags are excluded
  from quest journaling/replay and cleared through native SetFlag before a trip.
  This removes competing old event requests; the precise earlier solo loop cause
  was not conclusively observed and must be rechecked in game.
- Enemy messages assemble atomically with separate sequence/epoch fences; retain
  streamed-out kills. A follower seeds newly streamed actors once per visit and
  owner epoch only after complete flags/enemies. Use native HP/warp and native
  ForceCharacterDeath018BF9A0 with native2004[4]'s no-reward bit21 for historical
  dead actors; never just leave a live-looking inert actor at HP0. Existing map
  owner remains selected while present; native HP/hit routing stays in charge.

Targeted production fixtures PASS (travel range/host+guest commands, missed-load
presence, all-actor hide and reunion, multipart enemy reorder/incomplete/stale
state, native no-reward death and one-time baseline, altar and authority). MOD
syntax PASS; original ELF validates17 hook spans/7 calls; trampoline PASS.
Code/build/deploy/game results are separate: new gameplay confirmation OPEN.


Build/deploy/start result: source f8e7bf6 DLL build and isolated-stage delta
both exit0. Backup independent-player-lifecycle-20261105-190858. Two profiles
started19:08:58 MSK; native processes16252/12892, fresh run_20261105_190922.log
(P2) and run_20261105_190926.log (P1). Both report enemy/travel hooks ready and
local relay connected. Startup succeeds; actual co-op interaction/model/flicker
confirmation remains OPEN. No computer-use, save edits, or game termination.
Evidence: parent out/coop-dev/runs/independent-player-lifecycle-20261105.

## 05.11.2026 — Dream lamps, command ownership and per-peer model lifecycle

18:39 check: no-follow remains confirmed, but guest headstone list is empty,
altar does not respond, host prompt flickers and guest model is missing after
host reunion. Read-only flags show guest normal lamps unset while host lamps
are set; occupied altar record already agrees. Runtime respawn guard also
repeatedly reverses the guest's independent lamp selection.

Normal lamps now enter the existing shared kind1 progress journal; the host
catalog supplies only their live Dream bits, without copying personal services
or chalice lamp namespace. Ordinary received map snapshots also contribute to
the existing shared progress/reward path. Commands resolve the actual native
executor's talk record, with load-generation fencing, instead of the last
unrelated evaluated device. Independent mode retains native selected respawn
point and full native auxiliary word; prejoin home backup remains unchanged.

Every remote peer has an identity/visit-bound render lifecycle. Removed native
SetDisabled on players: it unlinks attachments, so toggling it cannot restore
a model. Use native member setter and bounded native insertion task transition;
wait for native activation/model readiness before restoring visibility. Native
physics reset/idle are retained only for a confirmed alive peer's stale death
visual. Legacy overlapping self/remote repair is skipped in independent mode.
No HP/type writes or custom mesh creation. Minimal draw/fade/death-bit repair
remains where no safe player-oriented native wrapper has been established.
The event revive wrapper013CBAD0 handles local-player global state or script
IDs below10000; it is not a safe generic replacement for remote PlayerIns.

Targeted production fixtures PASS: player lifecycle (four peers, load/address
reuse, apart/reunion, death, bounded retries), altar/shared progress, command
context, respawn guard, member binding, presence bridge and authority callbacks.
Full MOD syntax PASS. Build/deploy/start and gameplay are separate pending steps.
User preference: favor native game functions over duplicate manual handlers.


## Third gameplay check: actual device actors and competing state

18:25 run reaches active18:26:26. P1 travels out/back and to a chalice, P2 stays
in Dream; user confirms independent separation. P2 takes Dream authority and
restores30 enemies without the previous Warp fault. Both native exits0 after
explicit host leave18:35:49, no relay drops/new native faults. Stubbed NP/SSL
messages are existing API placeholders; guest own-world warning belongs to
recovery from the preceding crash, and leave warning to the eventual home load.

Read-only inspection of guest talk210000 shows its evaluator at1013BD9A30 points
to device actor1013BD9940, distinct from local player1013C69060. Real devices
were excluded by actor==local. Guard now permits audited non-remote actors,
retaining rejection of resident remote PlayerIns/quest scripts/empty host altars.
Fixture uses a separate device object and still exercises remote-player rejection.

Host prompt flicker is reported, not captured visually. Competing writes were
found: owner snapshot echoes reapplied to their producer, Dream services replayed
twice every500ms (also from enemy messages), and native host object corrections
could reset another map owner's objects. Dedicated Dream phase stays host-only,
flag application rejects owner echoes and enemy packets, native2F corrections
are owner-only. Visual result remains OPEN. Catalog/gate readiness gains one-shot
timeline records, not per-frame logging. Targeted production fixtures/syntax PASS.
Evidence: parent out/coop-dev/runs/independent-dream-devices-20261105-1830.

Fixa904d93 DLL build/delta exit0; isolated staging backup
independent-dream-devices-20261105-183835. P1/P2 restarted by request18:39 MSK,
fresh run_20261105_183901.log / run_20261105_183858.log confirm34/34 baseline
and both independent hook sets ready, local relay connected. Native5772/27776.
New travel/prompt visual result OPEN; no computer-use or game inputs sent.

## Second gameplay failure: lamp dispatch ABI and aligned Warp

Both profiles negotiate active18:15:12 after the room fix; guest lamp requests
remain absent. Original203AD60 has `R12=RDI` (output variant) and `R15=RSI`
(condition evaluator). R12 is not an evaluator, despite the prior comment/test.
Scoped talk checks therefore never admitted guest lamps. Capture the actual
R15 evaluator identity/actor at entry, before switch scratch-register reuse;
f14/f26/f47/f52 hooks now use that thread-local context. Test fixture corrected
to the real native calling convention, including clobbered R15 at common exit.

Both CPU crashes are the same new takeover defect: P2 at18:15:47, P1 at18:16:05,
native01517213 (`VMOVAPS [RDX]`), return018CD62C, bbsc.dll13F136 (our virtual Warp
call). RDX ends608/9B8,8 mod16. Position and rotation arguments require16-byte
alignment. Both are explicitly aligned now; new production fixture invokes a
SysV Warp stand-in with actual VMOVAPS and checks scaled HP/dead/no-warp paths.
These are concrete CPU faults; no GPU attribution is needed for these exits.

Production ESD ABI/takeover fixtures and full MOD syntax PASS. Build/deploy and
new gameplay result are separate. Evidence in parent
`out/coop-dev/runs/independent-lamp-crash-20261105-1817`.

Fixd6bd1f6: DLL build/delta exit0; isolated staging updated18:24 MSK, backup
`D:/Games/Bloodborne/coop-dev/backups/independent-lamp-crash-20261105-182403`.
No automatic game launch this diagnostic turn; new gameplay result OPEN.
Additional original ELF relocation proof: evaluator vtable0535AAB0+10 points
to203AD60, whose203AD74 bytes4989D64989F74989FC save RSI->R15/RDI->R12.

## First gameplay failure: native room binding (18:04 MSK)

P1 hosted/P2 joined successfully, but P2 followed the host Dream->Central Yharnam
at18:04:15; no independent activation. Read-only inspection of the actual
bb-probe children7572/35600 confirmed staging bbsc.dll loaded and send/lamp
hooks patched. The local native MemberId endpoint fields+30/+34 are zero; remote
+30 is127.0.0.1. They are network address/port, despite the historical register
field names `room/member`, and cannot identify a world.

Correct binding is the actual64-bit Matching2 room at
`[image+05540290]->+18->+400`, identical in both processes. The bridge now reads
that existing native controller field, preserves it during transient loads, and
uses the full64-bit room in presence/control v2. Old versions fail closed. The
fixture executes this actual pointer chain with a zero local endpoint and checks
cross-room differences in the upper32 bits, rather than stubbing an invented
nonzero local member room. Added release-visible timeline gate diagnostics.
This corrects activation; a new game result is still required.

Fixf398e01 built and staged exit0, both old profiles closed by user. Restart
18:13:39 MSK; P1 run_20261105_181406.log/P2 run_20261105_181403.log confirm
both new hook sets ready, plus34/34 baseline hooks and local relay connection.
Backup independent-native-room-20261105-181339. Native activation/admission after
restart remains to be observed; no computer-use or game input sent.

Branch (parent and BBSC): `codex/independent-world-travel`, based on BBSC `bdd59b7`.
User authorized implementation and a two-profile launch on this PC.

## Native integration, second gate (17:58 MSK)

Implemented: negotiated independent travel; per-place native enemy ownership,
HP source and hit routing; host-ordered scoped flag/enemy snapshots; host altar
catalog and guest-only native layer selection. Code/fixtures are ready for a
DLL build and two-profile connection test. Gameplay is not yet confirmed.

`bbsc_independent_world.inc` owns native channel boundary hooks (before reliable
sequence assignment), awake-enemy words, activation around same-place players,
off-map actor hiding and scoped reinsertion. The host coordinates leases even
while its own game thread is loading. Scope includes room, map, complete decoded
layout proof and per-slot ritual incarnation. Leases never migrate the session
host. Presence freshness gates actors; transient loading does not re-enable follow.

`bbsc_world_state.inc` reads all seven complete native altar records using the
same four read-only getters as the stage loader. It does not need a cached
FormData pointer or a visit to each dungeon. Guests journal personal altar groups
before installing the host's live Dream view; cached personal ritual pointers
are not replaced. Native progress-bit proposals are accepted only from the
current scoped owner and acknowledged by the host catalog. Enemy snapshots hold
up to1024 records and include HP, transform and active fighting state for takeover.

`bbsc_world_travel.inc` allows audited original lamp/headstone talks and occupied
host altars. R12 supplies the real ESD talk identity, R15 supplies the actor.
An explicit local request waits for the host's destination snapshot before a
native kept-session load. Actual altar command order is slot first, layer second;
the first half must not start travel. Guests use the original headstone list
command with the altar ESD's ten layer entries; special creation/removal UI is
unavailable. Host ritual changes fence old requests and return stranded visitors
to Dream. Personal inventory rewards and native root generation remain native.

Death/spectating/scaling, remote cutscenes and retained actor tasks are filtered
by place. Initial native admission and host exit retain their existing ownership.
Both peers must negotiate the capability before follow is disabled or lamps open.

Targeted validation PASS: world presence/model/bridge, relay dispatcher, chalice
scope, follow transition, actual native authority callbacks, actual native altar
getters/progress/view, actual ESD/travel callbacks and production hook trampoline.
Original1.09 ELF matches16 new hook spans and7 callable prologues. Full MOD syntax
check PASS. These fixtures use synthetic memory and never edit real saves.

Required in-game observations: admission and capability activation; separate
maps/fights and reunion; damaged enemy takeover; guest selection of a host cup
while host is elsewhere; restored personal cups on leaving; host departure.
Build/deploy/launch results will be appended below separately.

## Agreed behavior

- Party membership survives individual lamp travel between regions.
- A guest remains in the host's world when visiting the Dream: the guest sees
  and travels through the host's chalices. Returning to the personal world shows
  that player's own altars. Personal chalices are never overwritten.
- A host travelling elsewhere leaves the remaining players where they are.
  Host game exit/crash still ends the native session; host migration is separate.
- Personal loot/reward rules and native root-chalice generation stay in place.

## Source comparison

Yharnam Together `c1288b523aa7b4b07c348288b56a54a9627ae727` and the source asset
attached to CLSAMG22/BBSC v1.0.0 (`SOURCE-COMMIT.txt`:
`e995c21f6131b154dbeee3e756421ca55dfce2bf`) have identical travel, join, enemy HP,
altar, and packet-route implementations in the files inspected. The tag's Git
tree (`4f11faf`) is the old follow-host architecture; use the release SOURCE asset.
Credit: CLS_AMG and the Yharnam Together contributors, GPL-2.0-or-later.

Their native session is kept across loads; remote insert tasks are reconstructed
on meeting. Their server selects an enemy owner per map and routes native game
channels. Their team altars replicate rituals to teammates, which is incompatible
with the agreed personal-altar model and must NOT be copied unchanged.

## Native build and startup

Final native build exit0; delta preparation/copy exit0. Code73d84d3, packaged
source5c42b3b (documentation-only successor). Existing isolated staging updated,
main D: installation unchanged. Backup:
`D:/Games/Bloodborne/coop-dev/backups/independent-native-20261105-180114`.
Existing Player1/2 shortcuts launched18:01:14 MSK. Fresh native logs:
P1 `run_20261105_180143.log`, P2 `run_20261105_180138.log`, under each profile's
`user` directory. Both report34/34 baseline selected hooks and a connection to
their local compatibility relay. This does not establish player-to-player
admission or native independent travel. User explicitly declined computer-use
and will inspect gameplay manually; no game-window inputs were sent.
Parent record: `out/coop-dev/runs/independent-native-20261105-1800/run.md`.

## Historical first integration gate

- `bbsc_world_presence.h`: fixed-size/versioned presence wire format, room/world
  scope, finite-position validation, loading/playing/leaving states, monotonic
  visit/sequence fences, border hysteresis, freshness and five-player bounds.
- Deterministic coordinator-side owner selection, retaining a present owner when
  the host returns. This rule is NOT wired to native AI yet.
- Native channel-policy rules scoped by world/place, with dungeon identity AND
  ritual incarnation. They are NOT attached to native send/receive yet.
- `bbsc_world_altars.h`: whole-catalog guest view, host-only updates, monotonic
  ritual/revision fences and FormData validation. Pure model only: no live altar
  replacement, serialization, native menu wiring or persistent writes yet.
- Runtime game-tick publication through existing SHAD/P2P transport, packet ID
  `0x32`, and receive dispatch behind the existing session envelope. Readers only
  update metadata. Confirmed departures remove the corresponding observations.
- The live bridge advertises ONLY presence capability. It does NOT suppress
  follow, open guest lamps, route game packets or transfer enemy authority.

Tests execute the production header rules, actual tick/receiver functions and
actual shared relay dispatcher. They cover malformed/replayed/foreign packets,
load/border visits, room changes, capability gating, ownership selection, dungeon
isolation, atomic altar replacement and preservation of a separate personal view.
They do not demonstrate working native travel, native AI handover or live altars.

## Remaining implementation

1. Native packet boundary hooks and map-owner state/HP/hit/AI hooks adapted to
   direct P2P. Preserve reliable sequencing; never filter raw reliable datagrams.
2. Host-ordered map changes beyond the host's currently loaded map, plus safe
   state transfer when the owner leaves/loads. Test damaged enemy takeover.
3. Guest travel and native insert-task reconstruction, then capability-gated
   replacement of normal follow. Keep initial admission and explicit leave separate.
4. Full host altar catalog including per-slot ritual incarnation, native/random
   FormData and unlocked lamps. Load a chosen host dungeon while the host is
   elsewhere; never rely only on the latest currently mounted host dungeon.
5. World-scoped guest altar UI and command handling, preserving personal altar
   flags/cache/save snapshots. Removing an occupied ritual needs a defined safe path.
6. Presence-aware death, spectating, scaling, encounters, cutscenes, Dream ending
   and NG+. Preserve current personal rewards and catch-up semantics.
7. Native fixtures for real hooks, then two/three-player game confirmation of
   separate fights, reunion, owner handover, chalices and host departure.

The archived personal-Dream patch is not applied. No new gameplay switch is
exposed while the required native mechanisms are incomplete.

## Validation / deployment

First gate: `tools/test_world_presence.py`, `tools/test_world_presence_bridge.py`,
`tools/test_relay_dispatch.py`, `tools/test_session_register.py` PASS.
Build, isolated two-profile startup and gameplay statuses are recorded separately
in the parent run record; no successful fixture closes the feature.

First-gate DLL build and delta preparation exit=0. Started from the isolated
parent `out/stage/Bloodborne Game Launcher` runtime with existing Player 1/2
profiles at16:58:42 MSK. Native PID25140/11776, fresh user/run logs16:59:11/09,
34/34 selected hooks on both. Main installation unchanged; backup
`D:/Games/Bloodborne/coop-dev/backups/independent-world-stage-20261105-165841`.
Connection/presence exchange and the full independent-travel feature remain OPEN.
