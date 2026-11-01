# Personal dialogue/progress commit after guest return (source change, 01.11.2026)

Fixes the early-apply/unchecked-retirement gap described in
2026-11-01-window-dialogue-audit.md. No compilation, gameplay, installation or
player-save modification performed for this change, per user instruction.

## Checkpoints

- Guest SetFlag records dialogue deltas immediately when the character context
  is known; periodic and menu-exit flushes remain fallbacks.
- Home load/spawn callback loads pending disk journals early after a process
  restart, before map events/talks can consume triggers. Early replay repairs
  differing bits only; it is provisional and never retires a journal.
- While home recovery is pending, legitimate game ESD/event writes to tracked
  flags update the journal too, including resets to zero after gift consumption.
  Replay suppresses only its own SetFlag callbacks. Host progress is not imported
  into this personal map; no blanket OR or forced-one rule is introduced.
- Late home reconciliation retries after transient table replacement; it waits
  for the item ledger's initial settled-home reconciliation for the same load
  generation, then requests a normal full native save of the own world.
- Existing SaveDataMan completion observer routes results to the requesting
  transaction. Only success + native idle + matching final bits + unchanged
  personal revision/load can retire the talk journal and shared-progress files.
  A consumed gift changed during the save requires a new save of its zero value.
- Slot/user mismatch does not apply one character's journal to another. Save
  errors, unavailable managers, disk-write failure or loading keep recovery
  pending. An early callback cannot acknowledge an old save.

## Items and ordering

Existing AddItem/item-lot receipt tracking, one-time ledger awards and owed-item
logic remain. No fresh blanket item grant on loading or dialogue replay was added.
The ledger now observes the common load generation as well as the loading byte,
so it re-arms even when the ordinary tick missed an entire loading screen.
Guest post-load recounts and repeated home checks remain: native bag replacement
can occur after character creation, as shown by the 05:30 run. Final own-world
save waits for the initial home inventory reconciliation, rather than saving
quest state at 4 seconds and restoring owed items independently at 5 seconds.

## Verification status

Prepared tools/test_personal_progress_commit.py extracting production functions:
late overwrite, consumed trigger retained at zero, revision change during native
save, missing managers/disk failure/save error, wrong character, item barrier,
empty-talk shared-progress save, and replay after restart. It requires a compiler
and has NOT been run. Only source diff/definition-order review, fixture Python
syntax and matching changed sections in both checkouts were checked.

This is not a verified runtime fix yet. Before deployment run this focused
fixture and the directly affected menu-save observer fixture, then build once.
Do not run a broad test suite or edit real saves to validate it. The exact
native overwriter from the reported run is still not identified; this fixes
the reproduced recovery/retirement gap without depending on that instruction.
