## 06.11.2026 — local travel admission / parallel preparation SOURCE corrected; gameplay OPEN

Latest installed01:00 run010053 includes failures for BOTH roles. Fresh live
collections in parent out/coop-dev/runs/chalice-guest-return-followup-20261106/
{pc,pc-host-followup,pc-old-yharnam,pc-return-latest};2 files each,warnings0.
P2 Old Yharnam return72300101 at01:09:33.273 stages44.577 (+11.304s).
Second72300100 released01:10:52.911,90s timeout01:12:22.919. Crucially NPC
initial-state/world admission completes ONLY01:12:54.647; local7200 resumes
54.677, native stage58.798, Dream arrival01:13:01.564. This establishes the
local travel being held behind world/NPC bootstrap, independent of the earlier
m29 requested-Dream scope error. The exact reason native CHR admission itself
arrived late is outside this fix; world-event synchronization is not bypassed.

Fixes in shared source:
- Five exact ORIGINAL local travel events7200/12107000/12107100/12107200/
  12907020 bypass the world/NPC bootstrap for established roles3/6. They only
  drive personal requests/animation/loading. Joining role4 and every shared
  world/NPC event retain original bootstrap/owner admission. Native warp
  dispatch still checks DESTINATION readiness.
- Central World::ScopeForMap used by bootstrap, snapshot availability and
  arrival application. Pending Dream cannot replace current cup scope;
  ordinary queries cannot inherit a dungeon key; other-world requests ignored.
- Keep current cup's visiting-altar identity until native warp begins, so
  presence/bootstrap cannot lose the departing ritual during its animation.
- Start cup destination seed/request on the FIRST native altar selection,
  together with12107100 animation, without treating it as a warp request.
- Release original travel flag without waiting for cup flags or mount prepare.
  The verified pre-dispatch boundary holds ONLY2003[49] for all FOUR warp
  templates (including12107200/12907020); animation and native timers continue.
  At this boundary cup flags AND native PrepareBbscChaliceLoad are required.
  Destination wait cannot be released by90s timeout while native warp is unarmed.
No shortened native animation/wait, synthetic warp or NPC-cache workaround.
Important environment state continues through the owner's existing shared
snapshot/epoch/native authority pipeline; this is personal travel admission.

Validation: production bootstrap fixture PASS both roles/five local events
with unavailable world/NPC data; shared events/joining still BLOCK. Source
scope/actual Dream arrival/ritual entry regressions PASS. Restoring the old
world admission independently FAILS the new local-travel regression. New
production parallel fixture PASS ordinary/chalice return/headstone/cup entry,
both roles, early request, same-tick original release despite missing data,
animation/wait passthrough, warp-only hold, late mount and no timeout/replay.
Restoring old pre-release cup wait independently FAILS this regression.
Existing travel/original ESDs, ten-cup return, unqueued Dream loader,
46 ordinary/DLC+10 dungeon return/snapshot and native altar fixtures PASS.
Real Windows hook trampoline PASS (first attempt missing runtime DLL path;
rerun with compiler runtime in PATH PASS). Full MOD syntax exit0, existing CRT
warnings, build/travel-admission-parallel-syntax.log. No unrelated full suite.

HEAD/pin4989896 unchanged; shared dirty tree preserved, no mixed commit.
No DLL build/deploy: current games41272/41860 still running. No termination,
live-memory, settings/save/game-asset writes or push. Installed01:00 build
DOES NOT contain these new fixes. Gameplay OPEN after coordinated rebuild:
both roles return from cup/Old Yharnam while other player stays elsewhere;
animation must start without waiting for owner/NPC world admission, destination
preparation overlaps it, shared NPC/world events still wait for correct state.

## 06.11.2026 — chalice departure bootstrap deadlock SOURCE corrected; gameplay OPEN

Installed01:00 run010053, P1 GUEST/P2 HOST. Logs collected live in parent
out/coop-dev/runs/chalice-guest-return-followup-20261106/{pc,pc-host-followup},
2 files each,warnings0,ChangedDuringCopy=true. P1 enters host channel
2286771891767986/ritual26, requests72900101 at01:05:03.154; original flag
released03.156, repeated selections rejected busy,90s timeout01:06:33.160.
Second request01:06:34.908; while STILL in cup/load2 bootstrap certifies Dream
at42.889; native stage01:06:47.098, Dream arrival49.805. P2 enters cup at
01:06:47.413, return72900101 released01:07:11.012; repeat01:07:28.120 busy,
no return stage in this snapshot. User confirms P1 recovered after P2 moved;
then reports P2 unable to return. Not an absent DLL/old ordinary-return bug.

Exact production gap: GuardBbscWorldBootstrap unconditionally replaces CURRENT
m29 event scope with requested destination, even when destination is Dream.
BbscNpcPassHook calls this BEFORE native event update. Thus the running cup's
exit event waits for destination owner/FirstSync/Dream data, or consumes Dream
snapshot before actual departure. Require matching CURRENT event map before
borrowing requested ritual scope. Cup remains admitted during departure; actual
Dream arrival still receives full original bootstrap/owner/catalog checks.
Works both roles; no readiness bypass, native warp/animation/timing replacement
or owner-state sharing change.

Extended actual production bootstrap fixture FAIL old condition / PASS fixed
for host+guest with requested Dream and unavailable destination owner/NPC/Dream/
altar readiness, no source flags reapplied. Existing m29 ritual entry, real
Dream joining/state4->6 and native owner admission checks PASS. Chalice return,
unqueued Dream loader, ordinary/dungeon routing/snapshot tests PASS. Full MOD
syntax exit0 (existing CRT warnings), log build/chalice-departure-bootstrap-
syntax.log. HEAD/pin4989896 unchanged; shared dirty source preserved. No DLL
build/deploy, game termination, live-memory/save/settings/game-asset writes or
push. Gameplay OPEN for both-role independent return while peer stays elsewhere.
