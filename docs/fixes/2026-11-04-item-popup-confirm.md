# Client item notification: native OK registration

Request: boss rewards / key items (Pthumeru Chalice in the latest run) stay
visible on clients for about ten seconds without an OK button. The requirement
is the normal confirmation button, not automatic dismissal or a shorter timer.

## Source change

The original queue updater 016D86E0 checks [[local+58]+38]+41 bit7 before
requesting action11 / ActionButtonParam4400 at016D87CF. If set, it jumps past
the request, so the native OK prompt cannot appear and no confirmation can
release the queue. Read-only inspection of the original executable confirms
the branch, call arguments and accepted-result queue cleanup. Param4400 is
the original confirmation prompt (textId10010110), not a custom button.

BbscItemPopupConfirmHook at016D873C substitutes a thread-local view for that
single read on a living, loaded native guest (state6), with a nonempty exact
item-get queue and the exact local control pointer. Only bit7 is masked.
The displaced MOV/TEST and native conditional branches execute normally.
The character's flags, inventory, queue and session role are never written.
Native action registration, its remaining guards, player input and queue
release remain responsible for confirmation. All award paths using this queue
(bosses, keys, drops, native awards) receive the same rule. Hosts/solo/loading/
dead/empty or mismatched queue retain the original path. Existing
SHADPS4_BBSC_ITEM_POPUP=0 also disables the substitution.

This is a statically verified blocker and targeted source correction. The last
live run did not capture this control bit; its exact live cause and whether any
additional native gate delays OK remain unconfirmed until gameplay testing.

## Validation and status

- tools/test_item_popup_confirm.py PASS: extracts the production callback,
  installs the real Windows trampoline, reproduces the original rejected
  branch, then reaches native registration with bit7 set. Covers repeated
  notifications, other session roles, dead/loading, opt-out, empty/mismatched
  queue and missing control/flags. Verifies character flags/queue unchanged.
- Original ELF byte/branch/argument inspection PASS (read-only).
- Full bloodborne_re.cpp BBSC_MOD clang++ syntax check PASS; diff --check PASS.
- Direct queue producer dependency tools/test_notebook_popup.py FAIL at the
  expected five-item popup list. Both production fragments extracted by that
  test are byte-for-byte unchanged from HEAD; no kit/test changes made here.

SOURCE ONLY. No DLL build, deployment, game restart, commit, pin change or push.
BBSC HEAD and parent gitlink0ddb1d4; existing local changes retained. No real
save/settings/journal/game-data writes.

Gameplay OPEN: on an updated guest receive a new boss reward/key item, confirm
the original OK button appears with ordinary timing and closes the notification
on input; compare the host. Also cover a normal pickup and consecutive items.
