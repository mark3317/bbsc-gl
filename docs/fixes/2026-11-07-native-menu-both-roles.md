# 07.11.2026 — штатный System exit для гостя и хоста после ухода гостя

Статус: SOURCE FIXED / targeted checks PASS; NOT BUILT / NOT INSTALLED / gameplay OPEN.
Этот результат дополняет и ограничивает прежнюю host-only правку
2026-11-06-host-menu-reload.md: она сохраняла ручной выход гостя и принудительный
Stop хоста при уходе последнего гостя. Эти два вмешательства теперь удалены.

## Дефекты и доказательства

Снимок текущего прогона и timeline: родительский
out/coop-dev/runs/menu-return-20261107/analysis.md.
П2 run03375104:13:30.858 confirmed return to title -> custom Stop state6;
затем native own-world flags restore04:13:32.034 и Byrgenwerth04:13:35.245.
П1 run03365704:13:30.879 Stop из confirmed partner departure в state3,
ужеsolo System exit04:13:34.094, затем повторное создание world threads/events.
Пользователь подтвердил, что оба вернулись в мир без выбора Continue.

1. Guest System Yes подавлял оригинальное тело01C0D050, обнулял MenuMan+250,
запускал собственное сохранение, затем Stop/cleanup. Только после native idle/
PartyTitleReady вызывал OnReturnTitle, CloseMenus и поздно восстанавливал+250.
Это точно оставляет zero-selector window при отключении гостя. Native
01940DBB..01940E86 на реальных инструкциях воспроизводит в этом окне admission
world-return (+153=1,+150=0). Оригинальный Yes публикует+250/+25C и save latches
+1547/+1548 вместе; тот же native branch сохраняет+150 даже до окончания save.
Нельзя заменять эту транзакцию ручным Stop-before-title.

2. Получение сообщения об уходе последнего гостя заставляло TickBbscSessionExit
на хосте самому снимать persistence, вызывать Stop и bulk remote cleanup.
Сообщение об уходе другого игрока не является собственным System Yes.
Этот путь существовал независимо от уже исправленного host Yes и в данном логе
выполнился раньше него. Поэтому host-only fix не устранял конкурирующий teardown.
Production negative control с возвратом старого last-guest условия вновь нарушает
сценарий «guest leaves -> host System Yes». Точное промежуточное состояние
живого native task в04:13:34 лог не содержит: не выдавать source/native fixture
за запись каждой инструкции этого игрового прогона.

## Изменение

Все состояния0..7 проходят существующий byte-verified System Yes observer и
продолжают оригинальное тело. Observer сохраняет trip journals, отключает
reinsertion и session persistence, фиксирует исходную роль; не вызывает Save,
Stop, Cleanup, OnReturnTitle, CloseMenus и не пишет menu/save/input лatches.
Игре принадлежат ожидания autosave, ошибки сохранения, fade/menu lifetime,
выбор перехода и teardown. Повторный Yes сохраняет уже действующий запрос.

Удалены BbscPendingQuit, CancelBbscPendingQuit, TickBbscPendingQuit и оба его
вызова, ручной quit-save watcher/result, custom save/disconnect/title replay,
30-секундный quit timeout и HTTP PartyTitleReady gate из System flow.
Существующий native Stop observer один раз отменяет Party/уведомляет peers;
он не вызывает повторный Stop. Подтверждение независимо от BBSC save-poll
observer: обе существующие точки проверяют свои native bytes отдельно.

Host при уходе гостя оставляет native membership собственное удаление peer,
не запускает новый world transition и не меняет его persistence. Guest/joiner
при уходе хоста без своего System exit сохраняет прежний home-return путь.
При собственном System exit он не выдаёт конкурирующий Stop по peer notification.
Личный origin гостя остаётся в существующем serializer hook: роль берётся из
bbsc_title_quit.session4/6, slot и карта/координаты собственного мира сохраняются.
Обычные Lua return-to-title и Blank этим запросом не переписывались.

## Проверки

- tools/test_menu_quit.py --negative-controls: production all0..7 native ownership,
  pending autosave/no custom writes, duplicate Yes, one-shot native Stop observer,
  guest departure -> host exit, state7/solo exit, simultaneous host leave,
  ordinary host-leaves -> guest home fallback, invalid contexts. PASS.
  Возврат прежнего forced host Stop и отсутствие native guest confirmation
  ожидаемо проваливают сценарии. Тест не моделирует итоговый title UI.
- tools/test_title_request_native.py ../../out/exit-study.elf: реальные native
  Yes/save flags, save-wait exit-kind retention, old zero-selector world admission,
  отдельные OnReturnTitle/StageTransition commands. PASS. ELF только для чтения;
  serialization заменена isolated stub, настоящих сейвов нет.
- tools/test_hook_resume.py: actual Windows trampoline mid-function resume/skip PASS.
- tools/test_native_leave_release.py: state7 one-shot release/active preservation PASS.
- tools/test_home_return.py: production origin serializer/capture/home return PASS;
  fixture получил недостающие stubs соседнего targeted-kick dispatcher, runtime
  targeted-kick поведение не менялось. Проверяются fake memory, не реальные сейвы.
- tools/test_party_menu_barrier.py: native Stop owns one-shot Party cancellation;
  отдельного HTTP title gate/pending state больше нет. PASS.
- MOD syntax clang-cl /Zs exit0 (унаследованные deprecation/unused warnings).
- git diff --check PASS.

## Стоимость и границы

Новых hooks, ticks, таймеров, опросов, обходов, очередей, сообщений или retries нет.
Убраны два старых quit-tick вызова, их состояние и timeout; в простое нет новой
работы. На Yes постоянный объём существующей работы. На guest departure у хоста
удалён teardown; существующее native peer removal/notification остаётся владельцем.
Игровой FPS и title arrival/staying/Continue ещё не измерены этой DLL.

HEAD46a4ac2, parent index/pin6e7d32f сохранены; shared dirty tree и соседние работы
не сбрасывались. DLL/установка/игры не менялись; сейвы/settings/файлы игры не
записывались. Коммита/pin/push нет. Нужны отдельная согласованная сборка/установка
и игровой контроль обоих порядков выхода, включая одновременный exit и Continue.

## Подтверждение пользователя — 07.11.2026

«Оба вышли в меню, затем я нажал „Продолжить“».
Проверенный порядок: П2guest exit -> П1host exit -> оба в главном меню ->
ручной Continue -> мир и повторное соединение. USER CONFIRMED / CLOSED.
Последующая загрузка в логах — ручное продолжение, а не автоматический возврат.
Одновременный и обратный порядок этим игровым подтверждением не покрыты.
Сбор/установка новой DLL подтверждены run npc-room-members-village-20261107;
логи и разбор: parent out/coop-dev/runs/menu-native-retest-20261107/analysis.md.
Ранние OPEN/FAILED статусы для проверенного сценария исторические.
