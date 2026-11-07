# Согласование ИИ и штатной передачи движения NPC

Пользователь подтвердил рассинхронизацию движения рядом с другим игроком.
В run024305 ранний controller у клиента/владельца карты LOCAL, у хоста
REMOTE, но native grants противоположны для 7 из 11 общих NPC. Исходный
sender channel4/018EE829 проверяет именно signed grant word.

## Исправление штатного производителя разрешений

В 01916A82, после исходных active/requested/special gates, заменена развилка
построения native ownership request: роль блока2 не запрашивает NPC.
Роли1/0 сохраняют оригинальный вызов018CD180, его приоритет/нулевой отказ
и исходную упаковку handle/priority. Роль читается из того же event-published
32-byte cache, что ранний EnemyIns. Dream/неизвестный блок остаются native.

Найдена сопутствующая ошибка native request intake018F0780: собственный
список хоста018F0880 и принятый список гостя018F09D1 заменялись только при
count>0. Пустая заявка оставляла старые handles/приоритеты навсегда.
Теперь count==0 вызывает ТОТ ЖЕ оригинальный assignment01A6C590, который
уже умеет очистить список. count<0 по-прежнему отвергается. Без этой части
ограничение новых заявок не отзывает старую конкурирующую заявку.

Native host остаётся арбитром каналов16/17; формат, частота, merge01A6C700,
native grants018ECEB0 и sender/receiver channel4 не заменены. Хост в Сне
может штатно выдать grant клиенту по его заявке. После возвращения хоста
его role2 не создаёт конкурента. Полученные words используются всеми
исходными потребителями, включая движение, вместо отдельного обхода
position gate. Никакой постоянной перезаписи words нет.

Три install-time byte-verified rewrites; без новых runtime C++ callbacks,
ticks, таймеров, циклов, обходов памяти/NPC, очередей, сетевых каналов или
повторов. Проверка роли O(1) выполняется в уже существующей native развилке
на подходящего NPC; follower дополнительно пропускает дорогой расчёт
distance priority. Пустой assignment на уже пустом списке O(1), без alloc;
старые nodes освобождаются штатным assignment при отзыве списка. Число
проходов и запросов прежнее. Реальный FPS требует игрового контроля.

## Проверки

`tools/test_native_npc_authority.py`: ORIGINAL request loop01916965,
active/requested/priority-zero/remote exclusion/unknown/adjacent-map;
actual production Windows emitters; ORIGINAL собственная/принятая заявка,
положительные/пустые/отрицательные counts; ORIGINAL list assignment и
merge; ORIGINAL grant clear/set; ORIGINAL position sender, delta codec,
receiver и восстановление XYZ. Передача transport между процессами в
fixture не выполняется. Negative controls без request fence и без empty
replacement воспроизводят соответствующие assertions.

`test_native_ai_admission.py`: original sparse registration, owner commit
после Loading, binding/update, передача/возврат хоста, специальные пути PASS.
`test_native_npc_sync_mode.py`: installer fail-closed на каждом из трёх новых
участков, режимы native/legacy/default,2000ticks без дополнительных NPC
проходов и direct lamp/bootstrap dependencies PASS. MOD syntax PASS.

SOURCE FIXED / targeted checks PASS. Сборка, установка и игровой результат
дополняются отдельно. До подтверждения игры movement bug остаётся OPEN.
Parent evidence: out/coop-dev/runs/native-npc-authority-20261107.

## Сборка и установка

07.11 DLL build exit0,8 прежних warnings; metadata inputs unchanged0.
Five-file delta exit0 и PC deploy exit0, backup
D:/Games/Bloodborne/coop-dev/backups/native-npc-authority-20261107-20261107-030429.
Игры были закрыты. Запуск П1/П2 запрошен03:04:35МСК.
Gameplay OPEN. HEAD/pin, сейвы/settings не менялись.

Startup confirmed03:04:59MSK: both run_20261107_030458.log,35/35 selected; native authority ready + early AI admission ready; no matching startup fault/install errors. Native PIDs22100/40152. Gameplay still OPEN.

## 07.11.2026 — NPC authority retest: assignment/retention PASS / movement OPEN

Collect native-npc-authority-20261107/retest-pc exit0,3files,warnings0;
2live ChangedDuringCopy, до03:11:37. П1=guest4ec03841, П2=host9fe0730d.
П1 Cathedral03:08:55 owner epoch2/role1; host прибывает03:09:25 role2,
one-shot state applied=true. П1 25combat activations local/applied=true
(14до/11после прихода host); host26remote/FFFF. В текущем read-only snapshot
host14REMOTE/FFFF, client12LOCAL (5word1,7FFFF). Конкуренция host устранена
в этом снимке. Из7FFFF три мертвы, четыре живые stateE4=30 и отсекаются
native01916A55..74 до request rewrite. Это candidate special-state gap,
не доказанный новый movement bug; визуальный результат не подтверждён.

Найден startup failure первого П1 run030458: map10176MiB error1455,
затем write-null00443025/exit3. После restart030657 fatal в интервале нет.
Shared27perf windows: P1 50.9–57.8FPS, host44.5–56.5 при limit60;
max96.3/114.8ms, причинность новой правки не установлена. Relay queue/drop0
не доказывает отсутствие native UDP проблем. Код/сейвы/settings не менялись.
Parent report out/coop-dev/runs/native-npc-authority-20261107/retest-analysis.md.
Gameplay movement OPEN; не закрывать только по activation/snapshot.
