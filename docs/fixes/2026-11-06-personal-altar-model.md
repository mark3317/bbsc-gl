# Personal chalice model after host ritual removal — 06.11.2026

User: host removes a ritual in the same altar slot occupied at the guest's home.
After returning home, the guest retains the working menu/dungeon but loses the
cup model. This is a visual-state report, not a deleted ritual report.

Original 1.09 m21 events 12105010..12105016 disable nine models in their slot,
then choose the model from 94x05500..507 and cup-kind flags 94x05100..104.
These belong to group 94x05, included in the borrowed Dream service state.
The complete native ritual (six groups per altar) is separately journaled.

Host catalog updates replace those live flags without updating the Dream
delta baseline. RestoreBbscOwnDreamState consequently retains the host's
removal/replacement as a change made meanwhile. NoteBbscOwnDreamRestored then
used to overwrite the first-kept personal 94x05 journal with that result.
RestoreBbscOwnWorld restored the functional record but its visual group was
already contaminated. This path reproduces the reported asymmetry in memory.

Correction: NoteBbscOwnDreamRestored treats 94000..94699 like map groups:
the first-kept personal ritual record remains authoritative. Full home restore
puts back that original group before personal map events. Host view/removal
still applies while visiting. No synthetic model/visibility writes, native
cache mutations, timers, save migration or real save edits.

Validation: tools/test_altar_model_restore.py executes production altar-view,
Dream delta and full home restoration using allocated tables only. Seven slots,
host removal/replacement and native borrowed-view edits preserve all six
personal record groups, cup-kind and model bits. Unrelated Dream edits and
purchase counts remain; local selector group9 unchanged policy. Old policy
independently FAILS. Read-only original EMEVD confirms seven model controllers.
Direct dependencies test_world_altars_native.py and
test_dream_restore_admission.py PASS. Actual in-game model remains OPEN.

Build/deploy/start record: parent out/coop-dev/runs/personal-altar-model-20261106/run.md.
DLL build exit0 (8 existing warnings), source size/mtime unchanged during build.
Five-file delta prepare/deploy exit0 at02:54 MSK; backup
D:/Games/Bloodborne/coop-dev/backups/personal-altar-model-2p-20261106-20261106-025406.
Existing separate-profile Player1/2 CMD launchers requested02:54:13 MSK.
Both bb-probe processes started02:54:39/40 (PIDs1984/34844); fresh profile logs
confirm35/35 hooks and independent enemy/travel hooks. Gameplay still OPEN.
Shared dirty tree preserved; HEAD/pin4989896 unchanged, no mixed commit or push.
