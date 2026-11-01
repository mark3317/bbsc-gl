# System menu exit: direct title request — 01.11.2026

Status: source fixed in standalone and bundled BBSC; targeted production-function
fixture PASS. No DLL/package build, commit, installation or gameplay run performed.

## Evidence and correction to the first diagnosis

PC mod log bbsc-mod-20261101-213036-43556.log: guest departure at 21:46:14.574,
session 0 at 21:46:15.622. No native confirmation entry on this PC. The old hook
explicitly ignored state 0, so a subsequent host exit used the native store unchanged.
At 21:46:25.171 the delayed native send-home step was skipped for the own-world host;
SN-stuck-locks was released at 21:46:25.665. These are aftermath of departure, not
proof that send-home caused the later host menu exit's reload.

Laptop bbsc-mod-20261101-213041-2800.log: confirmation 21:46:15.181; successful
save and Stop 21:46:15.237; state 0 and replayed MenuMan+250=1 at 21:46:15.853;
own-world construction/restoration at 21:46:16.652, living own-world tick at 21:46:19.609.
No stranded-guest safety-net entry or failed/cancelled native save in that interval.

The first explanation (clearing pending quit too early lets home recovery race it)
was incomplete: it does not explain the host in state 0, which never had pending
quit. Both routes issue MenuMan+250, rather than the explicit title event command.

## Native code inspected, read-only

Game eboot.bin reconstructed into an analysis-only ELF under bloodborne_pc/out.
Image-relative offsets, not BN addresses:

- 01C0D050 Yes functor: sets native save flags/latch, then final store
  01C0D0C4 MOV [RAX+250],1. Existing hook correctly identifies this callback.
- 01940593 StageFlow reads MenuMan+250; 0194071C/01940827 use its cached value
  to arm the world-stage transition, bypassing normal member readiness when set.
- 01940DC5..01940E0C consumes/clears +250 after native save flags settle, marks
  stage task +153/+150. The acknowledged transition clears event request at
  01941050 and advances stage task at 0194107F. +250 is not itself event request 2.
- 0138BAF0 OnReturnTitle is a distinct native command. Its actual operation at
  0138BB29..0138BB2D is [[SprjEventMan]+10]+8 = 2; it needs no input arguments.
- Native session-error handler 01E572DA explicitly excludes request 2 from its
  ordinary return/recovery processing.

Thus replaying the menu store resumes the world-stage exit route. Direct native
title request selects the destination explicitly, avoiding the intermediate
world-transition trigger. The exact in-game sequence after the replacement is
not claimed verified until a later build and user run.

## Change

Confirmed System menu exit now also handles session 0 (former host/solo), preserving
fresh native-save completion gating. Active sessions retain explicit leave/Stop
and wait for native state 0. On completion, clear deferred menu request/save latch
and call native OnReturnTitle instead of replaying +250. State 0 requires no session
manager and issues no Stop. Validate event request target before departure and
again after asynchronous Stop; cancel rather than calling into an unavailable target.
Own-world journals/recovery, peer departure behavior, timeout policy and unrelated
loading paths are unchanged. No additional blanket suppression of loading.

## Verification

Bundled tools/test_menu_quit.py executes production functions: guest/joining/host,
former host in state 0 without session manager, save completion ordering, duplicate
confirmation, failures/timeouts, missing title target before and after Stop,
unsupported states, one direct title command and no +250 replay. PASS.
The test compiles a temporary fixture, not a production DLL. Source copies match;
git diff --check PASS. Native disassembly is static evidence; no gameplay claim.
