# 22:52 run — simultaneous host plus two guests confirmed

All three load DLL built22:51:30. Local identity refresh observed:
P1 3912->704347513 at22:54:18.096, P2 4215->520383427 at22:54:12.805,
P3 1704->830650577 at22:54:07.186.

P3 hosts. P2 arrives22:54:42.173; host completes native request queued1->0
at22:54:42.200 and immediately selects the next guest without P2 leaving.
P1 arrives22:54:59.203; second host request completes22:54:59.242.
All participants report3 actors: P1 at22:54:59.203, P2 at22:54:59.343,
P3 at22:54:59.776. Simultaneous residency persists until P1's explicit native
menu confirmation22:55:15.560, about16 seconds. P2 remains at the host after
P1 departure, then confirms menu exit22:55:33.006; P3 later22:55:47.562.
All three runners exit0. No native negotiation failures.

The interim identity mismatch while P1 was still joining compares resident P2
against pending P1; that rejection is expected and protects the unrelated
request. It ends when the correct P1 actor arrives and the request completes.

Confirmed scope: second guest can join while first remains, on this local3
run, with both native requests drained. This does not establish long-session,
rejoin/host-rotation, remote-network or combat stability.

Collected parent out/coop-dev/runs/login-identity-2252-review/final-pc:
9files,0warnings,all stable; supersedes initial pc snapshot with a file still
changing during collection. No code/build/deploy/relaunch/save changes.
