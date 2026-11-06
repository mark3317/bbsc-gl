# Selected chalice loader and guest native helper lifecycle — 05.11.2026

## 06.11.2026 — same-slot personal cache: native visible panel SOURCE corrected

User refined the case: P1 host, P2 guest; new second-altar cup is visible and
entry succeeds, but the first altar displays the guest's personal cup. Guest's
own cup on the same altar is the distinguishing case. Fresh two-profile live
collection: parent out/coop-dev/runs/chalice-first-altar-20261106/pc, 2 files,
warnings0, ChangedDuringCopy=true. P2 slot2 personal_state1; slot1 at00:10:22.670
personal_state5 despite host/decoded channel0x736fcbc954e1c. Slot2 uses host
0xe32ff5c23b211 (3996722017841681), native selection00:08:25.605 and loader
injection00:08:30.292, repeated00:12:52.797. P1 selects same slot2/ritual11.
Earlier no-entry/unknown-owner observations below concern earlier intervals.

Original ELF reveals a separate panel path:01B7721A loads the altar array,
01B7721E sets RSI=0x108,01B77223 adds PERSONAL altar[RBX]. It calls01C50250 at
01B77231; that function reads helper+E0/type,+D0/channel cache,+E8/seed,+F8/parts,
+140/name,+150/glyph and prepares the panel passed to01C506C0 at01B7725E.
Neither the selected-helper getter nor c79's captured promise intercepts this
inlined lookup. Correct host_channel logs therefore did not establish correct
visible panel data, especially when the personal native cache was occupied.

Correction hooks exact next instruction01B77227 (LEA R15,[RBP-3C0]) and redirects
only RSI to the existing host helper with world/load/slot/ritual/catalog guards.
Original instruction and both native panel calls continue. All7 slots covered;
host/offline/stale/missing catalogue and unrelated slots retain native handling.
No manual glyph strings, layer menu replacement or personal cache pointer writes.

Extended tools/test_world_altar_host_view.py checks seven-slot RSI routing,
negative contexts and executes the ORIGINAL inlined selection bytes through the
real Windows trampoline before consuming the renderer input. Distinct personal
and host caches share the same slot. Disabling only new RSI routing FAILS at
that actual panel boundary; corrected code PASS. Read-only original ELF checks
verify exact hook bytes, render calls and consumed helper offsets. Existing
native menu branches/removal and travel fixtures PASS; full BBSC_MOD syntax
exit0. These checks establish routing, not final in-game text/layer geometry.

DLL not built/deployed: two games remain running. Gameplay OPEN for visible
first-altar host glyph/layers when guest owns a different cup there, repeated
switching first/second altar and entry. HEAD/pin4989896 unchanged; no commit of
shared dirty sources, no live-process/save/game-file writes or restart.

## 06.11.2026 — installed23:48 menu check FAILED

User confirms P1 still displays personal8e... while P2 displays3g.... Both fresh
234844(P1 guest)/234843(P2 host) logs collected in parent
out/coop-dev/runs/chalice-glyph-followup-20261106/pc (2 files, warnings0,
ChangedDuringCopy=true; running-game snapshots). Installed23:48 correction is
present: P1 native host-helper and layer-menu callbacks execute23:50:45 and
again06.11 at00:04:46.061/078. Slot1, current=true, host and decoded channel
BOTH0x81fce924a8ab2=2286771891767986. Personal cached altar state5, removal
omitted. Read-only Party catalogue fields independently identify P1 channel
2030783960534556/glyph8e3bc7fy and P2 channel2286771891767986/glyph3gtfrffz.
Thus a correct channel in the helper does NOT prove correct visible menu
content. Initial helper decode and added native update routing have FAILED
the reported in-game glyph scenario. Do not attribute this run to absent DLL.

Neither profile logged native altar selection or an m29 stage request in this
run. Therefore it tests menu appearance, not the both-role selected-loader fix
or repeat dungeon identity. Exact remaining UI data source is unproven; no new
gameplay code/build/deploy/restart performed in this follow-up. Earlier fixture
passes below remain limited source checks, not menu gameplay confirmation.

User reports personal cups in the guest menu, then host entering that dungeon.
Both230550 logs collected in parent out/coop-dev/runs/chalice-wrong-owner-
20261105/pc (2 files, warnings0). P1 guest selects slot1 at23:33:18.093,
point2902954 at22.219; injection22.869 uses channel2286771891767986,
revision10/layout1D0A5A00; arrival27.037. P2 host selects slot1 at20.620,
point2902953 at24.668; arrival29.343, SAME channel reported29.346.
This channel exists in P2 Party catalogue (fixed first Pthumeru cup). These
logs do NOT prove the host loaded a guest-owned channel. Visible glyph and
complete native runtime stage/progress at the incident were not captured.
The user-observed failure remains OPEN; its full cause is not established.

Two source gaps corrected:

* Native01928987 consumed the selected independent descriptor only for joining/
  guest roles. Host input was simply captured even if it differed from the
  selected catalogue. Apply the selected descriptor to both roles; publish the
  same descriptor as host native mounted identity. No independent selection
  preserves original native host capture.
* The separate guest host-menu helper received a single zero-delta decode on
  backing-record changes. It owns native asynchronous metadata/cache work but
  was excluded from subsequent original helper updates. Redirect01AA6860's
  this argument for the selected guest menu to that same stable helper. Keep
  native frame/delta and full update; exclude host, unrelated slot, stale menu/
  world/load and recursive initial decode. No personal helper pointer/cache
  replacement, manual glyph/layer rendering or timer polling.

Validation: production chalice fixture FAIL old host branch with different
selected/stale/native cups, PASS corrected; existing capture/injection and
ordinary/legacy paths PASS. Guest helper callback and actual Windows entry
trampoline check receiver/frame and personal/host/wrong-slot/recursive paths.
Original1.09 entry bytes and native helper frame dispatch checked read-only
against doors-eboot.elf. Existing native travel fixture PASS. Allocated-memory
checks do not establish visible glyph, layer locks, geometry or progression.
Build/install/run recorded separately in HANDOFF and parent run record.
