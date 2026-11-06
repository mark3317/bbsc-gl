## 05.11.2026 — guest altar host glyph/layers, SOURCE ready; gameplay OPEN

User reports the installed22:19 native menu omits Remove Chalice but still
shows PERSONAL glyph/layers. Collected both profiles under parent
out/coop-dev/runs/altar-host-content-20261105/pc (2 logs, warnings0).
P1 guest run222014 at22:21:28.145 /39.551 /50.292: slot1=native_slot1,
host_channel0x81fce924a8ab2, personal_state5, current=true, removal omitted.
Thus old branch/Remove hooks worked; menu CONTENT was not switched to host.
The previous menu SOURCE-ready entry does not establish host glyph/layers.

Original1.09: native79 captures selected PERSONAL helper+108 at01B661CF,
and its async payload carries that same helper into01B66330/01B66EF0.
Added a separate native helper per altar with stable process lifetime (7 total),
constructed by the ORIGINAL altar helper constructor01AA3110 (as at01AB457C).
Original01AA6860 decodes it from the atomically installed HOST backing flags:
channel, seed, parts and persisted glyph via native getters. No memcpy of owning
pointers, custom menu, guest personal helper/channel replacement or asset edits.
Native73 establishes the scoped selection before79 without changing its command.
Native79's pointer capture and selected-helper accessor now borrow that helper;
the original promise, rendering, layer results and Remove-only omission remain.
Refresh occurs on first read / changed record, load or world, not timer polling.
Context remains world/load/slot/ritual-bound; stale travel remains rejected.
Native caches/refs are owned by those seven native helpers, kept until process
exit because async menu callbacks retain raw pointers across ESD/map lifetimes.

PASS: new production allocated-memory helper ABI/capture/getter fixture, distinct
host vs personal channel/glyph/layer metadata for all7 slots, native73 ordering,
record refresh, stale world/load/ritual/catalog and host/wrong-slot exclusions;
REAL Windows capture and return-epilogue trampolines (including native RET).
Original1.09 constructor/decoder arguments, helper size and async pointer chain
PASS. Existing production travel and native branch/Remove trampoline fixtures
PASS. Full BBSC_MOD syntax exit0. No real save/live process/game file writes.
Fixture native decoder is a stand-in; original code checks do NOT replace an
in-game appearance/travel check. DLL NOT built/deployed, both games still running.
Gameplay OPEN: guest host glyph/layer list/locks, selection into the host cup,
personal altars on return home; also empty guest personal slot vs occupied host.

## 05.11.2026 — host lamps through general shared progress, SOURCE ready

User clarifies HOST list is incomplete too: guests must receive every host lamp
and retain them through the ordinary shared story merge. Removed the separate
ordinary-lamp mask, read/apply code, catalog comparison and transmission. Altar
wire retains a zero reserved word for layout compatibility; incoming old masks
are ignored. Chalice layer availability remains in the native host ritual view.

General host kind1 block snapshots now also merge eligible progress into the
co-op guest live flag table on the game thread (existing shared-progress tick,
complete host blocks, no writes while loading). The same general exclusions as
the home merge apply. The existing trip journal/home merge collects these same
host blocks, including unvisited areas; there is no destination allowlist here.
Ordinary independent map-state application preserves eligible existing kind1
progress for BOTH roles, so a resident guest's older snapshot cannot erase
already-open host lamps/story. Runtime kinds6/7 and scoped m29 copy are unchanged.

PASS: production shared-progress policy/live byte merge for all44 base/DLC
headstone destinations, older/empty input, encounter/NPC/ritual exclusions;
production altar fixture: ordinary flags untouched by altar application,
older peer state cannot relock host progress; native bootstrap fixture and
full BBSC_MOD syntax exit0 (existing unused-argument warning). Allocated fixture
memory only, no real save/process/game-asset edits. No DLL build/deploy/restart.
Gameplay remains OPEN for both roles: complete headstone menus before/after
independent travel, new lamp activation and persistence through normal play.
Earlier diagnosis below is historical; it did not establish live overwrite order.

## 05.11.2026 — native guest altar menu restricted, SOURCE ready

User requests correction through the original call rather than a custom menu.
Kept zero-argument native command79/promise/ESD layer result; occupied guest
slot0 uses the same normal altar path instead of short-ritual78. Host unchanged.
Read-only1.09 confirms native79's async builder01B75280 chooses a ritual/search
or layer screen using PERSONAL SprjHolygrail slot+364, even after host backing
flags have been installed. Native01B66110 still uses its existing wait/promise.

At01B75353 and its continuation01B74F4B only the CMP operand is redirected to a
constant state4 observation; original CMP/Jcc and all original stack/async code
execute. Selected native branches overwrite RAX before any other dereference.
Personal ritual helper/channel/cache pointers are NOT overwritten or rebuilt.
Thus existing native01B66330/01B66EF0 renders the ESD's original layer list,
localized labels, locks, cancel and selection. The continuation cannot reopen
the host ritual/search UI. No new renderer, custom list, synthetic ESD argument
or incompatible78/79->41 switch. Raw/native altar flags and scoped travel still
supply host ritual/destination; empty/missing host altars remain denied.

The layer screen also unconditionally adds Remove Chalice. Native list::Add
entry01B76150 skips ONLY caller01B67A7F (the removal row); returns original
builder/RDI and leaves caller cleanup intact. Host and all layer/other-menu rows
continue natively. Original rusru confirms200/262005 = "Убрать Чашу".
Permission context is world/load/slot/ritual-specific and separate from unrelated
ESD commands. Host ritual changes cannot restore mutation actions; stale altar
or layer selections are rejected on BOTH halves of the travel request.

Added bounded per-menu logs: requested/native slot, host channel, personal native
state and current-catalog match, layer result and omission of removal row.
PASS: production travel fixture including all7 altars, empty/missing view, host,
world/load/ritual expiry and two-phase stale choice; NEW actual Windows trampoline
fixture executing both CMP paths and exact removal caller against synthetic
memory, native return ABI and untouched personal memory. Original ELF branch
bytes/targets/RAX lifetimes/removal-call/return ABI PASS. Full BBSC_MOD syntax
exit0 (existing warnings). No real save/process memory or game asset edits.
DLL has NOT been rebuilt/deployed in this follow-up; installed21:54 build remains.
Native menu appearance, selection and occupied host-cup travel need gameplay
verification. Previous diagnostic-only entry below is historical for source status.

## 05.11.2026 — native historical enemy admission, SOURCE ONLY

Repeated user report: on entering an occupied map, previously killed enemies
appear alive and inert. Native player FirstSync/CreateWait is not NPC initial
state. Read-only original1.09 ELF establishes the missing separate path:
0178C7EF calls01786360 during summon; native channel11 includes a CHR section
(tag43485220/version15091700). Serializer0190E750 marks HP<=0 characters;
loader0191BF6B invokes0190E8B0, which sets the native historical-removal reason
and calls018C49F0. This differs from ordinary HP5 updates and proxy Kill018BF9A0.
Retained native session travel never re-enters that initial CHR load path.

Added explicit pre-event admission from the current resident map owner. Owner
builds the ORIGINAL native11 packet with01786360 for the actual native member;
visitor reads it from that member's native queue with01789200 and passes only
its native CHR records to0190E8B0. All native block IDs/counts are preflighted
before any application. Native game code owns death/removal and exclusions.
No mod enemy cache, capture, custom NPC payload, HP writes, repeated Kill or
model hiding. No initial-state claim for NPC positions/AI beyond this native
historical-death path; existing native replication remains responsible there.

Control8/9 carry request/correlation metadata ONLY, scoped to world/map/ritual,
owner epoch and local load/request generation. Native packet fingerprint rejects
old/unrelated queued data; no NPC state is retained. An explicit loading request
may name the destination instead of its previous committed map; provider must
actually reside in that destination. Different Playing maps are denied. Native
send failure retries only while admission is pending; apply is once per load.
No resident owner (including a departed stale lease) preserves first-map native
admission. Existing presence simulation/routing permissions are not broadened.
All participants need this source revision for the new request/reply metadata.

PASS: allocated-memory production admission fixture (malformed/truncated data,
all-block preflight, old request/epoch/load, loading destination, wrong-map denial,
native send failure, once-only apply); original ELF serializer/dead-bit/handler
ABI; production native authority/send fingerprint + original hook spans;
pre-event bootstrap wait; world presence/routing; full BBSC_MOD syntax exit0.
No DLL build, deploy/restart, game input, live memory writes or save changes.
Gameplay remains OPEN: kill ordinary enemies before arrival, enter via lamp in
both host/guest directions and repeat the trip; no live inert copies should
remain, living enemies and personal rewards must continue working normally.
Other active chats changed HEAD during this work (now813bfb1); no reset, pin
update or mixed-worktree commit was performed.

## 05.11.2026 — guest personal cups regression, SOURCE ready

Fresh P1/P2 21:29 run shows personal Dream restoration during joining/guest
states because the native loader's own-world byte was used as session identity.
Fixed that decision; no personal Dream restoration while in the host Dream in
state4/6. Native readiness now precedes Dream writes; state4 ->6 reinstalls the
host view within the same load, and joining altar writes are protected.

Native12107100 prepares a cup before the ESD layer request. The native loader
hook now takes the selected host catalog mount immediately, replacing stale
armed/personal loader input before committing channel/layout/parts/type/feature.
Primary summons without an independent selection retain their fresh-claim path.

Production restore/bootstrap/atomic-altars/travel/chalice fixtures PASS, including
three different descriptors (personal decoded cup, old armed cup, selected host
cup). Full MOD syntax exit0. No build/deploy/gameplay or live save/memory changes;
coordinated pending build must include these changes. Gameplay remains OPEN.

## 05.11.2026 — Central Yharnam departure delay, diagnosis / SOURCE logging only

Latest main-install run: Player1/2 run_20261105_212953.log. Roles switched:
P1 host, P2 guest after21:33. P2 request21:34:05.652 -> native event released
21:34:05.703 (51ms) -> stage request21:34:09.731 (4.028s after release).
P1 first request21:34:26.259 -> release21:34:26.261 (2ms) -> stage request
21:34:30.385 (4.124s). P1 second request21:36:00.113 -> release21:36:00.115
(2ms) -> stage request21:36:10.057 (9.942s). Thus the extra delay is AFTER
preflight/release, not a multi-second destination-state wait. Relay samples in
that interval show queue0/dropped0 and continuing exchange, not queue congestion.

Read-only original m21_00 event12107000: EndIfClient, wait on its parameterized
flag, native animation2004[14](player10000,101164), WaitSeconds(4.0), native
warp2003[49]. Previous4s transitions fit that native sequence. Current logs do
NOT timestamp visible animation start or prove which instruction consumed the
extra~6s. Do not call the whole10s original animation or claim a proven root cause.

Added bounded active-trip logs for native interpreter animation-command,
WaitSeconds and warp-command entry with time since release. Idle instances are
excluded; unchanged instruction does not log every frame. These are script
progress, NOT proof of visible animation. No travel behavior/animation/wait edits.
Production native travel fixture verifies observation leaves instructions and
release timing unchanged PASS; full MOD syntax check PASS (exit0).
No rebuild/deploy, process termination, game inputs, real-save/game-asset changes
or live memory writes. Delay remains OPEN pending exact script-phase evidence.
Prior NO BUILD was superseded by the separately requested21:29 build/install;
this diagnosis does not replace binaries in running games.

## 05.11.2026 — host Dream/altar admission, SOURCE ONLY

User reports personal chalices visible/selectable in the host world and explicitly
requires the HOST Dream, with NO one-second corrective polling. User then requests
removal of the personal-Dream mode altogether. Removed DREAM_OWN default, switch,
launcher setting/hint/translations and personal-service/event branches. The own
Dream journal remains ONLY for restoring personal data on leaving the host world.

Host altar records now install atomically (all42 backing groups preflighted)
before Dream native event initialization, including native joining state4.
Missing full host Dream/map/catalog holds initialization, rather than letting
personal cups initialize. Native altar menu refreshes the host view or denies
opening if unavailable. Complete new catalogs apply on game-thread receipt;
replayed revisions do not reapply. Removed visitor timer writes. Host catalog
capture is driven by native flag writes, loaded table/world changes and received
ritual progress; unchanged writes do not advance revision. Existing timed packet
retransmission repeats the retained revision for late join/loss, without rescanning
rituals. Canonical host Dream map and service snapshots are sent even while host
is elsewhere; arrival applies host map/services first, newest ritual records last.
Personal reward/receipt protections and home restoration remain in place.

PASS: production altar getters/atomic42-group replacement/event-driven capture
and unchanged retransmit; actual ESD altar menu/readiness/travel; native pre-event
Dream barrier (state4, missing canonical state, one-time admission); chalice scope;
shared finale runtime; full BBSC_MOD syntax check exit0; generated RU text check.
Fixtures use allocated memory only. No DLL build, deploy/restart, game inputs,
real save changes, game asset changes or live memory writes. Previous NO BUILD
instruction persists. Installed25405ed unchanged; gameplay confirmation OPEN.

## 05.11.2026 — player lamp-reunion recreation, SOURCE ONLY

User reports models missing when a player travels by lamp to other residents.
Installed25405ed run: guest Yharnam21:06:43.246; host21:07:01.674; host binds
peer21:07:02.656; guest requests missing actor insertion21:07:04.194 and binds
21:07:04.474. Both log render repair, which does NOT prove a visible mesh.
Later read-only inspection found both sessions already solo, no remote actors;
it cannot establish the model failure's live fields.

Confirmed lifecycle defects corrected: actor-present/not-ready branch returned
forever before bounded recovery; retained actor across local/peer visit/reunion
was reused solely because its pointer/draw state existed. Retained same-address
actors now receive native per-character removal019186E0(world,PlayerIns), used
by original CSMultiPlayerIns.Delete at01E50C54, then existing native insertion4.
Keep member/session; never bulk cleanup or disconnect. Re-enumerate live native
players per task after removals and continue immediately after invalidating an
actor; never touch removed render storage. Recovery for unfinished actors is
bounded. New actors naturally created by the game are not recycled every tick.

Removed manual draw+0C/opacity/death/animation repair: opaque draw pointer is not
mesh visibility and +0C=0 can be normal on a visible local player. Native creation
owns those fields. Per-peer native hide/enable/member binding remains. Log native
recreation request with old actor and both visit generations, without claiming
visibility. Targeted fixture covers stale/reused addresses, local/remote travel,
unfinished actor recovery, bounds, four peers and NO render/opacity writes.
Original ELF verifies cleanup callsite/RSI ABI and callable prologue. Authority
fixture and full MOD syntax-only check PASS. Gameplay remains OPEN; no DLL build,
deployment/restart, computer-use, save changes or live memory writes. User's
NO BUILD instruction still applies; installed25405ed unchanged.

## 05.11.2026 — USER REQUIREMENT: native enemy initial state, no mod enemy cache

User explicitly rejects mod-maintained enemy state: entering an occupied map
must use native summon-style initial synchronization. Removed BbscWorldEnemy,
all enemy capture/retention/serialization/assembly, historical HP/kill seeding
and cached-position handover. Deleted the obsolete takeover fixture which tested
that removed workaround. Obsolete control kind3 is reserved/ignored, never
published or applied. Existing shared story/boss/lamp flags and host altar
catalog remain separate from native per-enemy replication.

Bootstrap no longer waits for a removed custom enemy snapshot. Native peer
creation readiness is still checked, but FirstSyncWait primarily creates a
remote PlayerIns: it MUST NOT be advertised as proof that native NPC initial
state has been delivered. Native enemy authority/HP packet routing remains;
late arrival full NPC initial synchronization is OPEN, not fixed by deletion.
Potential admission routing issue to investigate: SamePlace rejects loading
presence while retained member tasks may already be atCreateWait6. Do not widen
routing to unrelated maps or fabricate native completion merely to pass a guard.

Targeted native authority/routing fixture, updated bootstrap fixture and full
MOD syntax-only check PASS. No new DLL build/deploy/restart: user's ongoing
NO BUILD instruction remains active. Installed source25405ed still includes
the old enemy cache until a later authorized build; lamp fix91e1337 also pending.
Historical death diagnosticsd0e0e4d removed together with the workaround.
No computer-use, save edits, process termination or live memory writes.

## 05.11.2026 — delayed historical enemy death, diagnosis/logging ONLY

User reports first Yharnam resident killed one enemy; late arrival sees a living,
inert/invulnerable model, which later falls dead WHILE BOTH remain nearby. Thus
20:58:01 owner departure/takeover does not explain that recovery. Run25405ed:
guest P2 arrives20:54:29.870; host P1 arrives20:54:52.034, baseline40 at20:54:53.301.
No per-enemy index/HP/death result was logged in that build, so exact actor and
time of recovery cannot be reconstructed. Do not claim a proven actor-specific
cause or that actor-count batches imply repeated resets of the same enemy.

Confirmed code hazards: TakeEnemy sets HP and calls018BF9A0, then SeedEnemies
unconditionally marks actor seeded. Original native Kill returns at018BFAC6
when [[chr+18]+30]+18 bit0 is set, BEFORE setting death byte1E3 at018BFAD3.
Thus calling Kill does not prove death began on a network proxy. Seeded actor
is never rechecked; later live->dead owner snapshot also cannot revise its
already-seeded status. These defects can produce a frozen HP0 model until a
native update completes death; the current logs cannot prove which path fired.

Added source-only per-historical-dead-actor index/pointer, resulting HP,
before/after death byte and native proxy flags. No behaviour change in this
turn: do not add blind repeated kills, hide models or steal AI authority.
Existing takeover ABI/alignment/dead-path fixture PASS; it stubs Kill and is NOT
proof of the game's proxy death behaviour. Needs exact next-run evidence/native
initial-state investigation. User's NO BUILD instruction remains active; no
DLL build, deployment, restart, game inputs or memory writes. Read-only current
inspection happened after owner moved to Dream, not during the reported ghost.

## 05.11.2026 — chalice lamp access corrected, SOURCE ONLY / build deferred

User still testing25405ed; explicitly requests NO build yet. Do not build/deploy
or restart until user resumes. Both profiles remain running; no game inputs.
Current run confirms guest P2 native altar79 -> selected72100421 -> native warp
013CDF30 -> m29 arrival20:51:45.810; earlier altar/warp entry defects no longer
block this observed transition. Guest dungeon lamp use still failed by report.

Confirmed cause: guessed predicate talk/10000==29 && talk%1000<100 EXCLUDES ALL
original m29 lamps290110..290119, while admitting unrelated NPC talks. Registry
now includes exact ten original lamp ESDs, used consistently by UI and command
interceptor. Removed mod opening-story/scene-ready gates on lamp interaction and
travel requests. Original animations, event commands and shared unlock/state
remain native/existing synchronization. Per-talk/per-load admission log replaces
single process-wide line, making each actual dungeon lamp visible in next run.
Production fixture covers every dungeon lamp's UI/multiplayer/range/return path
with scene_ready=false/opening=false; original m29 ESD scan proves full lamp
coverage with no NPC substitution. Seven altars/original animation checks PASS.
No DLL build, deployment or gameplay check of this new source change yet.

## 05.11.2026 — correct native warp entry and original altar commands

Fixes the two confirmed native-flow defects from20:33 run. Functional travel
entry is013CDF30, actual EMEVD2003[49] target, point argument EDI. FirstSync
reinsertion arms at that native stage request, including original unqueued
returns to Dream; original animation/waits remain untouched. Guest occupied
altars retain original zero-argument78/79 and native asynchronous menu result.
Removed incompatible78/79->41 substitution: native41 requires one argument
and rejected the original command before opening any UI. Empty/unready guest
altars remain denied; host commands unchanged.

Added bounded-by-command logs: native altar selection/ritual, local travel
rejection reason, actual warp point and queued/untracked status. Existing
native event release/arrival/admission logs give the remaining sequence.
Production fixtures, all seven original zero-argument altar ESDs, original
animation order, actual2003[49] jump-table/call target/EDI ABI, native41 argument
check and trampoline PASS. These checks do not establish visible UI/models or
successful gameplay. Build/deploy/start and game results recorded separately.
No computer-use, game asset edits, save rollback or process termination.

# Independent travel — development branch, 05.11.2026

Source420c200 DLL build/delta exit0. Backup independent-native-flow-20261105-
203254. Requested two-profile startup20:32:54 MSK: P1 run_20261105_203320.log /
native10428; P2 run_20261105_203316.log / native13860. Both35/35 functional hooks,
enemy/travel hooks ready and local relay connected. No startup hook failure.
Original transition animation, admission to an existing owner, chalice selection,
actual enemy/model state and absence of intro replay remain gameplay OPEN.
Main installation unchanged; no computer-use, save edits or process termination.
Evidence: parent out/coop-dev/runs/independent-native-flow-20261105.

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
