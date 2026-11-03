# Second guest: defer selection until native role cooldown expires — 03.11.2026

## Observed run versus reproduced defect

The 15:56–16:03 local-three run (parent docs/fixes/
2026-11-03-second-guest-run-1603.md) returns the second guest's sign to the host
but never produces a claim while the first guest remains. Inviting the waiting
guest works after the first guest leaves and the room is recreated. Historical
logs do not record each pending node's state or role countdown; the exact live
moment of consumption cannot be asserted from those logs.

Static CUSA03173 1.09 has a definite lost-candidate path:

1. 01873290..018732DD scans pending nodes whose state is0 or2 and whose native
   role selection mask intersects R13D.
2. 018732DD immediately writes pending+10=1 (consumed), before validation.
3. 0187338A calls SummonBuild01874710 with destructive_reject=false.
4. 01874750..01874769 rejects a role with enabled retry counter and positive
   countdown when destructive_reject=false. It returns null, no request built.
5. The caller leaves the pending node at1. Further native scans skip it even
   after the countdown expires. Repeated advertisements with the same native
   generation do not rearm that node (014B7186..014B71AD).

This is especially relevant to queued guests immediately following the first
invitation: all co-op roles share retry backoff policy, currently capped at2s.
The exact contribution of this path to each historical failed invitation is an
inference until the next game run, not a captured live countdown.

## Correction

At existing signature-checked SummonSelection.Scan01873269, before the native
scan consumes any node, ApplyBbscSummonRoleDelayMask removes currently delayed
co-op role masks from R13D for this scan only. The pending node and prepared
summon remain intact. When the native countdown expires, the original scan can
select that same node and the original builder can submit the real request.

Covers co-op roles7/21/22/23/24 under the existing FIVE_HUNTERS feature. Enabled
counter + positive float predicate follows native behavior, including NaN/zero/
negative pass behavior. Unreadable tables/feature off leave native behavior.
An original mask of0 is never expanded. Change-only logging records deferred
role masks, without payloads/identities/secrets. The scan hook is selected as
functional when full research/capture is off, using its existing7-byte MOV
RAX,[RAX+1A8] signature and the production trampoline.

No sign generation invention, artificial claim, pending-state reset, shortened
countdown, forced native state or ACK. Member/role capacity, identity and actual
JoinRoom/readiness checks remain in the original native builder/connection path.

## Regression evidence

`python tools/test_second_guest_cooldown.py` PASS. Temporary C++ regression
harness calls the extracted production function via production bbsc_hooks.cpp
trampoline and executes exact original scan/consume bytes01873269..018732E5
and native cooldown predicate01874740..0187476F in synthetic executable memory.

Baseline: first guest consumed, second guest state0; scan consumes second at
positive cooldown; builder rejects; later countdown0 still cannot select it.
With production hook: second stays0 (or renewed2) during delay, then is selected
once and reaches the native cooldown-pass continuation. All5 co-op roles,
feature-off/invalid table, zero native mask, disabled guard, zero/negative/NaN
countdowns, unrelated role and mixed-role masks are covered. Counter/observation
window/countdown remain untouched; consumed first guest is never selected twice.
Only branch continuations are stubbed; this does not simulate full world entry,
capacity allocation, UDP readiness or a three-player session.

`python tools/test_matchmaking_native.py` PASS for existing interval/backoff
policy and guard preservation. Changed source diff --check PASS.

## Delivery status

Source only, uncommitted. User explicitly requested no build: no production
DLL/port/launcher/package build, deployment or game launch. Only temporary test
executables were compiled/run; removed with their temporary directories.
Existing unrelated working changes retained. Saves/settings/journals/game files
unchanged; parent submodule pin unchanged. Live second-guest validation pending.
