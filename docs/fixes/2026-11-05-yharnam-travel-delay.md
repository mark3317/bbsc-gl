## 06.11.2026 — destination preparation concurrent with departure animation, SOURCE ready

User explicitly requests starting preparation together with native animation.
Ordinary-map trips now send/retry the destination flag request while releasing
original local travel in the SAME tick. Animation and original4s wait proceed.
If flags are late, a byte-verified native update boundary012ECF6B holds ONLY
2003[49] dispatch for7200/12107000; conditions/timers have already updated at
012ECDEF->012EC380. It branches to original stack epilogue012ECFAD BEFORE command
execution and PC advance. No animation replay, frozen timer, direct/synthetic
warp or copied guest arguments. Resume original dispatcher when flags arrive.
Existing chalice preparation (animation before layer request) remains unchanged.
Pending pre-dispatch readiness is not discarded by a90s load timeout, which
would release the original warp without its destination; native leave remains.

Extended the existing hook skip API with an optional verified native resume
address in BOTH DLL/emulator implementations, defaults unchanged. Production
Windows trampoline fixture confirms original stack/epilogue and no command/PC
side effects on hold; existing skip/resume paths PASS. Production travel fixture
confirms request+release together despite missing flags, animation/wait admitted,
warp held, request retry during animation, then one native release/arrival.
Original ELF validates gate/timer-call/dispatcher-call/tail bytes; MOD syntax PASS.
Native event transport isolation from previous entry is included in the source.

A DLL rebuild was started; a newly active related Hunter's Mark chat was found
while it was running. This attempted binary is NOT declared coordinated/latest
and is not installed. Current games continue; no termination/input, live memory,
save or game-asset edits. Finish related work and rebuild before shared deployment.
Gameplay confirmation remains OPEN.

## 05.11.2026 — travel delay survey / native transport isolation, SOURCE ready

User prioritizes recurring delay, also P2 return-to-Dream selection doing nothing.
Installed23:48 build includes prior cache/log fixes; do not blame missing install.
Survey71 completed native stage requests from both profiles05.11,10 destinations.
Abnormal release->stage intervals: Central Yharnam points2412951/2412953
8.081,8.362,8.767,9.942,10.294 seconds (plus earlier5.630); OLD Yharnam
point2302950 at23:58:33.543 takes8.505s. Preflight0-2ms in latest cases.
P2 latest slow request23:56:07.494 -> release07.495 -> condition observation07.511
(flag=true) -> next-instruction animation observation11.047 -> stage15.576.
These observations precede actual dispatch and do NOT timestamp visible animation.
Ordinary headstone sequence is about4s; loading is a separate measured interval.
Latest P2 returns eventually occur23:55:57.266 and23:57:45.192; failed selection
itself has no queued travel/stage request in logs, so it is not proven diagnosed.
Survey data: parent out/coop-dev/runs/travel-delay-survey-20261105/transitions.json.

Found original transport isolation gap: local travel events7200/12107000/12107100/
12107200 set native+78=0, but012EE660 ignores this when sending timed continuation
and012EE420 ignores it when applying foreign condition/progress. This exact path
was fenced only for personal NPC events. Extended the EXISTING send/receive
boundary to those four independently negotiated local travel events, for BOTH
roles and regardless of the NPC quest switch. No map-specific timer, direct warp,
shortened animation/wait, or native shared door/boss event changes. Bounded per-
load TRAVEL records expose suppressed send/receive event IDs and native kinds.

Actual original emitters + Windows receive trampolines: old production source
FAIL on travel continuation send; fixed PASS for all4 events,both kinds,host/guest,
NPC-switch off/on,independent off passthrough,shared doors/malformed/drain. Full
BBSC_MOD syntax exit0. This proves a concrete transport defect, not receipt of
one particular foreign packet during each observed stall. Delay/failed return
remain gameplay OPEN pending new binary and testing. DLL build follows below;
no game termination/input, save/game-asset edits or live-memory writes.

## 05.11.2026 — Yharnam departure delay follow-up, SOURCE fix / gameplay OPEN

Latest both run_20261105_230550. P1 guest23:12:06.247 request ->06.249
release (2ms) -> first pre-update animation observation12.474 (+6.226s)
-> native stage request16.543 (+10.294s) -> arrival23.329. Previous guest
23:10:34.984 release ->39.023 stage request (+4.039s). Host trips +4.048s
and +4.056s. Extra pause is after release, before observed native progress;
the observation is NOT proof of the visible animation or actual dispatch.

Found/reproduced two source defects. Native event lookup can initially return
-1 while the instance's file exists but its instruction is not ready. The cache
retained this failure for the whole load when ref stayed unchanged, preventing
later localization/client admission. Retry failed lookups on the next update.
Also ONE shared previous-step tuple logs interleaved idle travel instances on
EVERY frame: P1 has19212 phase lines, P2 has20180. Track phase bits per instance
and journey, bounded128 instances/four phase types. Add original flag-condition
phase and selected flag readback; label these pre-update OBSERVATIONS honestly.
No native script, animation, four-second delay, condition, event scheduler,
warp coordinates or load speed changes.

Production regression FAIL old lookup / PASS retry; old logger with corrected
lookup FAIL at interleaved-instance count / new logger PASS, repeated phases and
new journey covered. Existing production ESD/native release fixture PASS and
full BBSC_MOD syntax exit0. No build/deploy/restart; both games are running.
No process-memory/game-asset/save writes. The cache defect and log flood are
fixed in source. Neither defect is proven to explain this exact6.226s pause;
that latency remains OPEN pending precise new condition/flag observations.
