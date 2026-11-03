# Overlapping cooperative admissions — 2026-11-03

Requested: guest B must be able to start connecting while guest A is still
connecting/loading, rather than waiting for A's resident actor.

Native selection01873110..0187322D conflates insertion readiness with command
ownership: any unfinished insertion or nonempty SosStatus request list leaves
R13ready mask0. Yet the native request list already stores a separate request
ID/user/character per guest and builder01874B96..01874C92 accounts reservations.
Dispatcher+78/+90 and result+88, plus broker+138/+1D0, represent actual command
ownership. Removing/resetting those would mix responses; they stay native.

AllowBbscOverlappingAdmissions runs at the existing exact scan hook01873269,
before the original candidate is consumed and before ApplyBbscSummonRoleDelayMask.
It reopens only cooperator bits allowed by native R15slot mask when:
- host is alive, loaded in own world and not leaving/title;
- 1..3 well-formed cooperative reservations exist;
- dispatcher queue, active ID, result and broker command/pending task are idle;
- post-completion cooldown expired;
- native live+reserved role and total capacity can accept another guest.

It doesn't test whether existing guest actors have arrived, mutate reservations,
advance task states, alter identities or invent acceptance. The original scan
marks each selected candidate once; native builder/dispatcher still run. The
existing per-role delay mask avoids consuming a candidate during backoff.
Resident completion remains identity-specific and drains only the matching
finished request. A stalled insertion keeps its own reservation, but with a
free second slot it doesn't prevent B being selected.

This pipelines independent guest insertion/loading, not concurrent reuse of a
single native command buffer. Short control submissions remain serialized by
native ownership; shared capacity/host teardown still affects every guest.
Actual timing/overlap in gameplay remains to be established in the new run.

Validation:
- test_overlapping_admission.py PASS, production policy via real trampoline and
exact01873269 native candidate scan: baseline ready0 blocks B; new hook selects
B with A still reserved/unarrived; A unchanged, B not selected twice.23negative
cases cover command/result ownership, broker busy, capacity, host/load/quit,
wrong roles and malformed lists. Slot mask/PvP readiness preserved.
- test_second_guest_cooldown.py PASS, exact native scan/consume/builder.
- test_resident_summon_completion.py PASS, exact identity-bound completion,
other pending request retained and current-login identity regression.

DLL-only; no protocol/VPS/profile/save changes. Build/deploy/startup recorded
in parent out/coop-dev/runs/overlapping-admission-20261103/run.md.
