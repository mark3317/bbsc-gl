# PvP only on the host / missing Blood Dregs — 04.11.2026

Status: SOURCE FIXED with the shared new-world relay correction from
[the parallel placement investigation](2026-11-04-new-join-teleport.md).
Targeted checks PASS. No product build, installation or gameplay confirmation
in this task. Keep gameplay OPEN.

## Last run and limits

Primary PC/laptop profiles twin/test, PC startup16:59, laptop17:03MSK.
PC complete stopped-run rotation copied to parent
`out/coop-dev/runs/pvp-20261104/pc/last_run.2.log` (2,144,307,214 bytes).
Filtered PvP/session records retained beside it. Host enables PvP17:31:35,
disables17:32:21, enables17:32:26, disables17:32:56. Guest request arrives
17:33:07.587 and the host enables at17:33:07.593. Host changes guest team20→21.
No lethal-kill claim or Blood Dreg award is logged there.

The sibling investigation retained a partial laptop raw prefix through17:30
and a separate completed filtered extraction including guest death17:31:53 and
session end17:35:47. That filter did not include PvP. The raw prefix records
only the initial17:06:12 host PvP-off receipt; it cannot establish the full set
of later PvP callbacks. The later laptop log was truncated/restarted during this
investigation; do not label its small replacement or old17:03 rotation as the
PvP run. No live protocol watermarks were captured. The source defect below is
reproduced, but log evidence alone does not prove the transport counter at every
reported hit/death.

## Cause and correction

DynamicEngine previously kept outgoing relay stream/sequence across local
acquire generations when native TCP stayed connected. Receiver receipt keys
include the world generation, so a fresh world expects seq1 while its host
starts above1. Ordered delivery waits for the missing prefix. The guest's fresh
outgoing stream can still reach the host. This reproduces the observed direction:
guest asks for PvP, host enables locally, guest never receives confirmation.

The shared correction in `party/dynamic.py:DynamicEngine.apply` calls
`reset_relay()` when a transition changes generation. No membership/authority
checks are bypassed. Native TCP remains connected. No separate change to damage
teams or unconditional item awards is necessary.

Blood Dreg claims originate on the victim's machine, and the production lethal
callback requires local `bbsc_pvp_on`. Missing host confirmation therefore blocks
claims even when the host can inflict damage. Claim/receipt packets also use the
same relay. Both dependencies are covered below; live inventory confirmation is
still required. Existing missing rewards are not retroactively fabricated.

## Targeted validation

- `python -B -m unittest test_pvp_relay -v` from `party`:2 PASS. Real loopback
  Compatibility/native TCP bridges and DynamicEngine peers, three successive
  worlds on unchanged sockets. Guest requests, host on/off confirmations,
  RegisterKill claims and acknowledgments in both directions remain byte-exact.
- Negative reproduction suppresses only the new acquire-generation reset:
  guest request reaches host, host PvP-on buffers behind missingseq1. Restoring
  reset unblocks the same payload. This is a source regression test, not a claim
  that logs recorded those exact watermarks.
- `tools/test_relay_dispatch.py` PASS: production dispatcher, relay and P2P,
  host state/guest request, foreign-host/session rejection and short frames;
  existing mount/register/kill separation preserved.
- `tools/test_pvp_dregs.py` PASS: production lethal callbacks, finisher selection,
  PvP/NPC/self/environment/replay guards, inventory/storage add and native bytes.
- `tools/test_session_register.py` PASS: production award service, last-hit
  targeting, duplicate claims, delayed grant/retry, ACK and session checks.
  Fixture now includes the real protocol header; its initial compile failed
  because it stripped all production includes after the protocol extraction.

Delivery includes the shared DLL admission changes plus Party compat.py and
dynamic.py; coordinate with the placement task for a single build. HEAD/gitlink
remain0ddb1d4. No commit/pin/push, save/settings/game-data writes or process stop.
