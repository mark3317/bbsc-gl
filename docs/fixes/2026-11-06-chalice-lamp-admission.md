# Chalice lamps: preserve ritual admission in native NPC mode

User report: only chalice lamps fail; pressing Light Lamp hides the prompt,
but no animation follows. Ordinary-world lamps are outside this regression.

Code regression found: native NPC mode bypassed GuardBbscWorldBootstrap both
at the event-update callsite and at the guard entry. That guard also installs
the current ritual's runtime flag view before m29 native initialization.
Native replication of enemies does not replace this part of independent cup
mounting. The original12907010 starts with EndIfFlag(request), then waits for
the local ESD request before the native animation101170. Running initialization
against a previous/mismatched ritual can end a one-shot event prematurely.
This is a candidate cause; the live report alone does not establish that exact
instruction history. Do not mark the gameplay bug closed without a new run.

Change: reuse the existing pre-event guard in native mode for chalice maps.
It admits the mounted ritual's flag snapshot once per native load/scope.
NPC block/FirstSync admission remains bypassed in that mode; ordinary maps
return immediately. Running ritual state is not reapplied every event step.
Original ESD/EMEVD, native lighting animation and return commands are unchanged.
No lamp polling, forced animation, retry or new interaction handler was added.

Validation PASS:
- test_native_npc_sync_mode.py: modes0/1/unset, production installation/ticks;
  missing cup state holds initialization, both host/guest admit once, 2000
  further steps do not replay flags, unavailable NPC admission does not block.
- test_world_native_bootstrap.py with BBSC_NATIVE_NPC_SYNC_TEST=0: existing
  full-mode admission, source-cup departure and mount namespace preserved.
- test_lamp_activation.py against original dvdroot_ps4: native53 activation
  request parameters, both roles and restart localization, no warp substitution.
- git diff --check.

Status: SOURCE READY; source/tests only; build/deploy/gameplay pending. A separate active
chat investigates P2's22:10:38 Dream-join heap crash, so shared build must wait.
Current games are never terminated for installation. Source HEAD/pin6e7d32f
unchanged; no save restore or settings edits. Only mods-src/BBSC is mod source.

Repeat launch requested while investigating:21:57:03 runner38388/26164,
native21:57:28 P1=35024/P2=30716. P2 crashed at22:10:38 (separate investigation).
P2 restarted22:13:47 with runner35744/native9548 using the unchanged installed DLL,
165FPS process-local overrides. No claim this restart includes the source fix.
Run artifacts: parent out/coop-dev/runs/lamp-native-repro-20261106-215703/.
