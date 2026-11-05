# Guest crash must not stop healthy peers — 04.11.2026

Status: SOURCE ONLY. Targeted regressions PASS; no build/deployment/gameplay
confirmation. Running PC games were left intact. GPU crash itself is not fixed.

## Evidence

Latest three-profile run started about12:33 MSK. Host LocalPlayer3, guests
LocalPlayer1/2. Logs collected in parent
`out/coop-dev/runs/guest-crash-isolation-20261104/pc`;6 files, warnings0.
Player1/3 logs changed during copying: these are live snapshots, not final logs.
Release BBSC diagnostics were off; no current mod/Party event log was available.

Player2 `last_run.log`:12:50:52.078 Vulkan DeviceLost, WriteInvalid0x0,
STOP GPU assertion; runner pid31712 exit23 at12:50:54.800.
Current Windows WER events12:51:07/12:51:31 report LiveKernelEvent141,
nvlddmkm.sys, WATCHDOG-20261104-1250.dmp. These support a current GPU reset;
they do not establish the underlying GPU fault or a mod cause.
Player1 signaling declares LocalPlayer2 DEAD/no answer12:52:14.102;
Player3 does so12:52:15.231. Read-only Party state revision253 retains owner
LocalPlayer3 and joined LocalPlayer2; LocalPlayer1 has left the room.
The user reports Player1 was sent out when Player2 crashed.

## Deterministic defect and correction

Static Engine sets global relay_error when one recipient exceeds its16-frame
window+128 backlog or10s ACK expiry. Compatibility.relay_loop then shuts down
the shared DLL socket, affecting every healthy recipient. DynamicEngine has the
same shared-error path for its per-peer workers. A per-peer socket queue overflow
also used the static global network_error callback.

These recipient failures now fence only that recipient's outgoing stream and
clear its bounded backlog. Scheduling continues for every other recipient,
including those later in the roster. The native socket stays open. Global local
failures (storage/shared ingress) retain their existing behavior. Snapshot output
exposes relay_peer_errors independently from relay_error.

The failed stream stays fenced until reset_relay (new native transport/world
scope). It must not resume with skipped multipart sequences. No timeout changes
ownership, admission, native membership, durable receipts or real save state.
Automatic recovery of the failed guest within the same stream is not implemented.

Old static source reproduced loss of the healthy peer's chunk144 in an isolated
three-process run. Fixed source delivers all180 chunks and reverse traffic.
This proves the relay cascade defect. Release logs do not prove whether that
exact branch, native non-host DEAD handling, or both caused this game's ejection;
the reported gameplay scenario remains OPEN pending a new game run.

## Checks (temporary profiles only)

- Static crash/bounded-backlog test:180 ordered frames, healthy reverse path,
  unchanged authority/membership. Old HEAD engine FAIL at chunk144; fix PASS.
- Static actual10s expiry: remaining peer continues, reset clears fence. PASS.
- Dynamic crash via production native relay socket:180 exact frames reach the
  healthy peer; reverse response uses the same socket; reset starts a fresh
  ordered stream. PASS.
- Dynamic worker expiry: failed recipient fenced; healthy worker continues. PASS.
- Direct dependencies: static recipient gaps/new stream, latency/loss/duplicates,
  dynamic ACK loss/order/new native stream, independent slow socket worker. PASS.

No game launch, real save/settings edits, commit/pin/push. No installation while
Player1/3 remain running. Only Party Python source changed; native DLL/port do
not need rebuilding for this correction.
