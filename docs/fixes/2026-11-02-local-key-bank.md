# Local key bank across guest loads — 2026-11-02

Native disassembly identifies the mechanism previously left unknown in K2-snapshot-plan.md.
Inventory +0x10 is the bank manager. Persistent key slots are at inventory+0x28,
temporary key slots at +0x38; selected slots/count pointer are +0x58/+0x60.
0x01AC5600(manager, mode) with nonzero mode selects the temporary bank and clears
every slot, then rebuilds the lookup. Mode zero selects the persistent bank.
Guest actor setup at 0x01937A8B passes player_data+0x338 and mode 1 (call 0x01937A97).
This explains repeated key loss at native guest initialization without item-removal hooks.

The production entry hook changes nonzero mode to zero only for the local carried
inventory's bank manager. It runs independently of research logging and does not
depend on a session-state sample during actor initialization. Native save/load,
ordinary item removal, NG+ key deletion, storage and remote inventories are unchanged.
Both source checkouts contain the fix. Existing recovery remains for old receipts,
including keys already in the temporary bank before updating/restarting the game.

Validation: tools/test_local_key_bank.py <read-only eboot.elf> extracts the production
hook, validates guest call/prologue bytes and executes the actual native bank-switch
machine code in an isolated process. Native cleanup helper calls and lookup rebuild
are stubbed; bank selection and slot clearing instructions are original. Baseline
clears the key; fixed path survives repeated initialization/home selection; consumed
keys remain absent; other inventories and null input pass through. PASS.
No real save or game file modified. Live guest death/follow/home/menu/rejoin and
saved inventory still need confirmation; this is not a gameplay closure.
