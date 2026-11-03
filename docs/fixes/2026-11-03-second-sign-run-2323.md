# 23:23 run: second sign not claimed, silence rotation works

Evidence: parent out/coop-dev/runs/blank-silence-2323-review/pc (9 files,
0 warnings, all stable); player-1/2/3-events.jsonl in the same run. All native
processes ended exit0; none running at collection. DLL build23:21:52.

Generation22: P1 host, P2 joins. P3 sign returned to host23:24:42 onward,
but no claim/admission for P3. Overlap readiness logs at23:24:43.737,48.750,
53.754. First guest request completes23:24:56.726 (queue1->0), masks become
ffffffff, but P3 still gets no invitation. Thus this is not just a blocked
in-flight first-guest completion or missing sign delivery.

P2 explicitly confirms title exit23:25:20.078. P1 later confirms Beckoning
silence23:25:39.396; ownership releases23:25:40.267. P3 shows stopped notice
23:25:40.668 and acquires generation23 at23:25:51.940. P2 is at title/loading
at release, so absence of its stop banner does not prove a runtime banner failure.

Generation23: P3 host, P1 guest. P2 sign returned23:26:18 onward, but never
claimed. P1 first request completes23:26:20.290, queue0/readyffffffff; P2
still not selected. P1 leaves, then rejoins (claim222 at23:27:17), while P2
continues publishing and being returned in host search. P1 completes again
23:27:30.693. No simultaneous3 residency. P2 never receives a generation23
admission; transport negotiation is not reached for this attempt.

Conclusion: confirmed silence/release/rotation works in this run. Independent
second-guest admission remains unresolved. Existing overlap hook executes, but
readiness alone is insufficient. Next investigation: native candidate identity,
role filtering and consumption between returned sign list and summon request.
The exact rejecting predicate is not recorded in current logs; do not attribute
this to the relay, host ownership, or a specific mask without more evidence.
Analysis only: no code/build/deploy/launch changes in this review.
