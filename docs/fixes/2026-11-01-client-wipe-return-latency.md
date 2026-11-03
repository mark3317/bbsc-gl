# 04:31–04:37 run: client wipe semantics, GPU crash, combat latency

Evidence: bloodborne_pc/out/coop-dev/runs/20261101-0437/{pc,laptop}:
mod logs, complete last_run.log, laptop Application/System/WER event extract.
User reports client keeps echoes, no vial/bullet restock, host sees rejoin text,
client crashes on home return, delayed damage from client attacks.

## Death / respawn

Laptop 04:33:25 PartyGhostDeath records 1073 echoes. After host reload,
04:33:50 wipe warp uses a summon-reload snapshot, phase 3; client rebuilds
as phantom type 1. 04:34:05 post-load recovery releases camera/death locks.
04:34:31 reward adds 48: total 1073 -> 1121. No death-penalty/restock log.
Second death 04:36:14 records 1217 echoes; same wipe reload path follows.

Code inspection: TickBbscSpectate's successful RequestBbscSessionWarp(...,
"wipe") returns before BbscApplyDeathPenalty calls in the later respawn-in-place
branch. BbscRestockFromStorage is called by in-place respawn, not by successful
post-load recovery of an already living phantom. This explains bypassed death
semantics; exact consumable quantities were not logged. Fix needs one-time
death processing before world teardown and correct restocking after rebuild,
without duplicate penalties on retries, normal death, or boss victory rewards.

PC reinsert task restarted at 04:33:49 and 04:36:35. No session teardown during
these wipes. Recreated native character likely produces arrival text despite
same session; existing resolved-text suppression is insufficient per user.
Do not solve by disabling real join notifications globally.

## Client crash on home return

04:36:54 host departure; 04:36:56 client requests home transition with no bar.
04:37:00.955 onward GPU skips draws: unmapped resource table in RunSrtWalker.
04:37:02.155 DeviceLost on submit; device fault WriteInvalid at 0x0;
04:37:02.157 Vulkan assertion, STOP: GPU library assertion failed.
Windows WER records LiveKernelEvent 141 / nvlddmkm.sys / Turing_SCG3D at
04:37:10 and 04:37:22, WATCHDOG-20261101-0437.dmp.
This is current-run evidence on the LAPTOP, separate from the previously
deferred PC crash investigation. GPU reset is confirmed; upstream trigger
(renderer/resource lifetime/driver/hardware) is not established. No completed
home load or Shared Progress merge in the client mod log, so the new merge
filter's execution is not shown as the crash site and cannot be gameplay-verified
for home return in this run. No CPU native fault stack was logged.

## Client attack delay

Transport sample analysis: receive-to-dispatch queue median/p95/max:
PC 50.5/86/2914 us; laptop 62/315/134486 us. Mostly relay traffic, no full
queue/auth/digest errors in final counters. Last PC vport30 tx=13005,
client queued=13005/read=13005. This is not a loss guarantee or full latency
measurement. Cross-machine wall clocks have a large offset; raw timestamp
differences must not be reported as one-way latency. Packet queue timing
alone does not explain seconds of damage delay. Need native hit/authority
timeline, relay delivery/clock alignment and gameplay scheduling correlation.
User report reopens combat-delay investigation despite earlier T22 confirmation.

No code changes, tests, builds, deployment, save modification or rollback during
this investigation. These three issues remain open; no new GPU cause assumed.
