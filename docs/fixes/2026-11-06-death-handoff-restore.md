# Возвращён прежний retained-death handoff — 06.11.2026

Статус: исходники исправлены, целевые проверки PASS. Сборка/деплой/игровой
результат — отдельные статусы в HANDOFF и parent run.md.

## Повтор и история

Повтор обоих профилей после36a91be: run233908(P1)/233909(P2), штатный collect
exit0/2files/warnings0, parent out/coop-dev/runs/death-respawn-20261106/retest-pc.
Гость23:40:49.338 PartyGhostDeath, local timer23:40:52.838; хост23:41:11.944
SoloPlayDeath, local timers23:41:12.965/23:41:14.467. Все foreign=false.
Далее native-death incomplete повторяется каждые15с. Пользователь подтвердил,
что ошибка осталась;36a91be её не устранил. Эта гипотеза снята, hook0139A9D0
и его fixture удалены. Не представлять приём foreign в toy VM как причину live.

`git show fb4d600^:emulator/src/core/bloodborne_re.cpp` и diff fb4d600:
до fb4d600 (зафиксирован05.11.2026 06:40) существующий TickBbscDeathLifecycle
после15с передавал затянувшуюся смерть в BeginBbscCoopDeath("watchdog",state).
В fb4d600 этот вызов удалён вместе с repeat-text substitute: осталась только
диагностика и сброс её15-секундного интервала. Поэтому native callback stall,
который старый алгоритм доводил до возрождения, теперь удерживается бесконечно.
Сам native-only переход описывался04.11; commit date не равна дате реализации.
В12984a9 watchdog уже был направлен в ОБЩИЕ правила boss/wipe, а не direct revive.
Это поведение сохраняется; отката всего большого fb4d600 не делается.

## Восстановление прежнего алгоритма

Восстановлен удалённый handoff в уже существующем tick и с прежним лимитом15с.
Он передаёт смерть в тот же BeginBbscCoopDeath, который вызывает native final.
Не добавлены tick/thread/hook, сетевые пакеты, второй контроллер или новая UI-цепочка.
Сумма отголосков фиксируется при первом HP0, до native drop/наград за время смерти.
Loading/quit/title/solo/unknown HP и уже идущие spectate/curtain исключены.

Сохранён исправленный native rearm повторных смертей: прежняя искусственная
выдача YOU DIED не возвращается; оригинальный handler и очистка статусов действуют.
При живом напарнике и обычной смерти Begin выбирает RespawnNow; TickBbscSpectate
идёт в существующий StartBbscDeathCurtain, затем retained respawn без StageTransition.
При смерти в boss fight выбирается Spectate,15с не разрешают немедленное оживление.
Без живого напарника, при wipe/invasion/prison остаются существующие отдельные правила.
Невозможность coordinate-respawn в незагруженной карте остаётся прежней границей:
для другой карты нужна native загрузка; добавлять туда перенос координат нельзя.

## Проверки

- test_repeat_death: обе роли, first/repeat rearm, частичные отказы; native delay
  до14999мс не вмешивается,15000мс передаётся в общий controller ровно один раз;
  echo snapshot; loading/quit/title/unknown HP/solo/curtain/active fences PASS.
- Negative control BBSC_TEST_NO_DEATH_HANDOFF=1 (историческое удаление вызова)
  ожидаемо FAIL на проверке handoff. Native-only диагностика не проходит regression.
- test_independent_death_destination теперь исполняет production Begin и Tick:
  обычная смерть с живым партнёром у хоста/гостя вызывает curtain без reload/warp;
  boss death сохраняет spectate без curtain/revive; wipe/arrival/load guards PASS.
- test_death_accounting: два penalty/restock, отказы, отсутствие duplicate charge PASS.
- test_death_status_reset: три жизни host/guest, native death-category policy,
  все пять status gauges, persistent effects/guards/malformed lists PASS.

Файлы игры/settings/живые сейвы вручную не менялись, работающие игры не завершались.
Игровое подтверждение restored handoff ещё необходимо. Причина внутренней задержки
native VM не объявляется доказанной; восстановлена именно убранная прежняя страховка.
