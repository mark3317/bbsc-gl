# Djura guest talk diagnosis — 05.11.2026

User: host can talk to Djura, guest cannot. No runtime writes or save/settings
changes were made for this diagnosis. Source/game data read only.

Current P1 guest/native bb-probe5144, P2 host/native bb-probe29432; root launcher
PIDs10236/27712 are not the processes containing the eboot. Native read-only
flag snapshot: P1 state1322=1,1320/1321/1323/1324/1325=0; P2 state1325=1,
1320..1324=0. P1 72300300=1,72300314=1,12300751=1; P2 72300300=1,
72300304=1,72300305=1,72300314=1,72300315=1,12300751=0.

Original m23_00 talk t230323 (Djura): main group2147483635 sends1321/1322/1323
to group2147483634. That group first checks72300314 and immediately terminates
its normal talk branch when set. Its1322/72300300 branch is labelled combat
start. The1320/1325 main route instead uses group2147483633; host1325 has the
friendly dialogue/reward history. Thus a shared friendly-looking actor can be
shown while the guest's own ESD follows its hostile/closed-talk personal stage.
Generic world-NPC talk policy allows t230323 (NPC suffix>=100).

P1 fresh run_20261105_054236.log at05:44:00.830 already records NPC1320 restored
to own0 and1322 restored to own1 during admission. This confirms that the mismatch
predates the attempted conversation in this run. The exact earlier action/event
that originally set the guest's1322/72300314/12300751 is not established. Do not
claim that the player personally attacked Djura or killed beasts from this log.
No production change: copying host friendship would change personal quest policy.
