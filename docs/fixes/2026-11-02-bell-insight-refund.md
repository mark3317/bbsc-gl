# Bell Insight refund — 2026-11-02

User requested removal of legacy bell Insight grants; no save edits.
common.emevd event 9183 command 6 is 2004[8](10000, 4680, 0).
SpEffect 4680 has heroPointDamage=-1 at +0x144, granting one Insight.
The bank 2004 handler at 017BA6A0, command 8 branch 017BAB93,
resolves entity/effect from argument offsets 0/4. Its entry prologue is verified.
Suppress only event 9183's local-player effect 4680 command when free bells
are enabled, return success to advance the interpreter. Boss event 9350 and
chalice altar event 9422 remain unchanged. Removed TickBbscFreeBellRefund,
its 10/45-second heuristics and bell-pending file operations. Existing marker
files are inert and left untouched. No currency or save data is rewritten.

Target production-hook fixture (raw/resolved args, unrelated events/effects,
disabled mode) and original bell parameter fixture PASS. Runtime pending.
