# Remaining guest reload after another guest uses Blank

A guest departure must leave the host and other guests in the current world.
`BbscSendPhantomHomeHook` previously skipped native `OnLeave_Limit` only for
`BbscOwnWorldNonGuest` (and active finale). Thus another guest was unprotected
against the native delayed leave callback, even while state 6 and persistence
remained active. The source already documents misdirected `OnLeavePlayer`
notifications in the multiplayer case; the host-only guard did not cover guests.
This is a source-level defect matching the report; no new live trace was captured.

Added `BbscGuestStayingInSession`: state 6, persistence not suspended, no menu
quit and living local actor. Such a guest skips send-home and releases stale
leave locks on the next tick. The release rechecks residence, so a real departure
that starts in between keeps its native locks. Host/own-world and finale guards
remain. A local Blank suspends persistence before Lua's leave flow; real session
loss/native Stop and death continue through native home recovery.

Validation: `tools/test_resident_guest_leave.py` extracts and executes the actual
hook and deferred release, checking resident guest, local leave, loss, joining,
quit, death, intervening departure, own-world host and finale. PASS.
`tools/test_native_leave_release.py` PASS. Fixtures compile only their isolated
harnesses, no mod/package build, install, game launch or save changes.

Pending live validation: host plus two guests, one guest uses Blank and returns
home; host and remaining guest must stay without loading, retain movement and
fog/menu interaction. Repeat with the other guest, then host departure to verify
that the remaining guests still return home.
