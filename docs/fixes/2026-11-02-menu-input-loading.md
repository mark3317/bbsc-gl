## 2026-11-02 — confirmed menu exit blocks input, loading at session closure

Run menu-20261102-0248 collected from both machines. PC confirmations
02:49:44.862 -> native title request 02:49:45.485 (623 ms),
02:52:59.646 -> 02:53:00.4 approx. Save and native Stop already ordered.
Menu brake/load wait are not a pad input filter.

Confirmed exit now neutralizes OrbisPad buttons, sticks and triggers at the
existing PadReadState wrapper (also used by bbport keyboard bindings).
Metadata/system bit retained, failed reads untouched. Atomic ownership begins
on accepted Yes, ends on cancellation or after native title handoff, so title
menu and Continue remain usable. Save failure/timeout restores input.
After observed native session state 0/2/5, open loading once immediately before
OnReturnTitle; never before save completion/Stop completion, no world reload.
Production test_menu_quit, test_quit_input and test_hook_resume PASS.
Build/install/runtime statuses recorded in HANDOFF; game validation pending.
