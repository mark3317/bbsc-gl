# Client item notification: native OK registration

## 08.11.2026 — игровой прогон после установки

Статус задержки окна награды за босса — CLOSED по подтверждению пользователя.

Оба профиля запущены в 01:49 МСК на общей DLL с правкой награды и
выходов из Лекционного корпуса. История сборки и установки в parent
`out/coop-dev/runs/lecture-group-pc-20261108-014709/run.md`.

После Церковного чудовища штатный лот `50000010` («Значок охотника с мечом»)
зафиксирован у гостя П1 в 01:55:18.131, у хоста П2 — в 01:55:18.160.
Гость зажёг лампу `2412952` в 01:55:19.035, через 0,904 с. Хост
применил общий чекпоинт. Оба прошли `BlockClear2_1` около 01:55:23 и
сохранили сессию. Хост отправил гостя домой адресной командой в 01:55:39.597.
Гость получил её в 01:55:39.906 и перешёл в одиночный режим в 01:55:40.120.
В обоих журналах нет ошибки установки перехватов блокировок возврата.

Пользователь сообщил, что в этом прогоне всё выглядело нормально.
Логи подтверждают выдачу, доступное взаимодействие и сохранение сессии.
Отдельной метки нажатия «ОК» нет. Снимки обоих живых журналов в parent
`out/coop-dev/runs/boss-reward-confirm-live-20261108-015620`.

## 08.11.2026 — пропуск подготовки принудительного возврата

Подтверждена прямая блокировка «ОК». Штатное обновление `0133A114–0133A11B`
копирует `Lua+0x8D` в `[05540048]+0x52`, менеджер действий. При запросе
действия 11 из `016D87CF` регистр `R9D` равен 1. Регистрация в `01CD91F0`
читает `+0x52` на `01CD926E` и при ненулевом значении возвращает 0 через
`01CD93A7`. Очередь наград остаётся открытой. Этот отказ расположен после
проверки бита `0x80`, которую уже обходила 1.3.2.

Для гостя типа 1 в активной сессии пропускаются три штатные записи
`BlockClear2`. `01384D03` пропускает только `Lua+0x8D`. `01384D48`
после исходной проверки HP переходит на `01384D75`, минуя три
вызова `SetEventFlag` (4047, 4000, 4092). `013853E7` пропускает
`MenuMan+0x2F0`. Ранее поставленные ограничения другого события не
сбрасываются. Соседняя запись Lua, условие здоровья, «Паразит»,
выдача и подтверждение награды, баннер и таймеры завершения идут
штатно. Прежняя защита от ухода и возврата остаётся в поздних этапах.
Проверка пропуска учитывает активный выход на титры. Все три правки
включаются вместе. Если установить их не удалось, имеющиеся процедуры
очистки вызываются один раз из `BlockClear2_3` у живого загруженного гостя.

Удалён `TickBbscBossUnlock` с окном 20 с и интервалом в 1 с. Общий
перехват кнопки предметного окна сохранён. Сверены оригинальные байты и
продолжения всех трёх мест 1.09, прошли `test_boss_quit.py`,
`test_hook_resume.py` и `test_native_chalice_rewards.py`. Первая DLL собрана
с кодом выхода 0. Общая сборка и игровой прогон описаны выше.

## 08.11.2026 — тайминг завершения боя у гостя

В оригинале 1.09 `BlockClear2` ставит состояние завершения боя
`MenuMan+0x2F0` (`013853E7`) и `Lua+0x8D` (`01384D03`, ожидание загрузки
в ветке гостя).
По адресам `01385400`, `013855E7`, `01385832` и `01385859` игра
планирует `BlockClear2_1` через 5 с, затем `BlockClear2_2` через 2 с,
а от него параллельно `BlockClear2_3Leave` через 5 с и `BlockClear2_3`
через 8 с. У гостя BBSC пропускает выход и возврат домой. Очистка
состояния меню и ожидания загрузки в `TickBbscBossUnlock` разрешается
только на последнем этапе, через 2 + 8 с после `BlockClear2_1`.
20 с в `BbscBossUnlockMs` задают срок уже разрешённой очистки.

В прогоне чаш от 04.11 два гостя получили награду в 14:58:11.931 и
14:58:11.933. Стадия `BlockClear2_1` наступила в 14:58:17.010 и
14:58:17.123, очистка прошла в 14:58:27.118 и 14:58:27.485. От стадии
победы до очистки прошло 10,108 и 10,362 с, от выдачи 15,187 и 15,552 с.
Источник — `out/coop-dev/runs/chalice-dream-crash-20261104` в родительском
дереве (`player-7-filtered.log` и `player-21-filtered.log`). Два боя
07.11 дали 5,001 и 5,040 с от выдачи до `BlockClear2_1` на П2
(`run_20261107_205346.log`). Этот журнал не фиксирует очистку или нажатие.

`016D86E0` закрывает окно по принятому действию 11. У исходной строки
`ActionButtonParam 4400` текст «ОК», флаги запрета `-1`, а `execInvalidTime`
равен 3 с и записывается после принятия действия (`01CD97C3`). В BBSC-GL
1.3.2 есть коррекция проверки бита `0x80` перед вызовом `01CD91F0`.
Целевой тест ветки с актуальным на тот момент перехватом прошёл. Архивные
логи подтверждают таймер послебоевой блокировки. Появление и срабатывание
«ОК» в этом прогоне отдельно не записаны.

## 04.11.2026 — исходный разбор

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
