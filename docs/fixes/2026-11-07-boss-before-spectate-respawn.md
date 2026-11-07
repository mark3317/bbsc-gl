# Победа до включения наблюдения — 07.11.2026

Статус: SOURCE FIXED, целевые production-проверки PASS; DLL не собиралась,
не устанавливалась, игровой контроль OPEN. Пользователь разрешил исправление
без новых таймеров/опросов. Исходный live-разбор и копии логов:
../../../../out/coop-dev/runs/p2-boss-respawn-20261107/analysis.md.

П2 умер03:42:42.255; BlockClear2_1 зарегистрирован03:42:50.350;
retained handoff запускается03:42:57.272, уже после победы. Раньше проверка
bbsc_boss_killed_ms>=bbsc_spectate_since_ms отвергала эту победу.

BeginBbscCoopDeath теперь фиксирует отдельную границу текущей смерти из
существующего bbsc_dead_since_ms (при отсутствии наблюдения HP0 — время входа).
Watchdog освобождает исходную метку только ПОСЛЕ передачи в общий controller.
Проверки победы/отсутствия победы в TickBbscSpectate и выбор лампы босса
используют одну границу смерти. Нулевая победа не считается завершённым боем.
Старая победа перед новой смертью остаётся недопустимой. Existing load/session
и encounter map/load fences сохранены. Spectate safety/debounce/settle часы
по-прежнему начинаются при входе в наблюдение; периоды не менялись.

Новых hooks/ticks/таймеров/опросов/сетевых сообщений/сканов нет. Добавлены
8байт snapshot на активную смерть; существующая dead_since метка только
перенесена выше по файлу. Один snapshot при входе в death controller,
стоимость сравнений существующих death branches прежняя (плюс kill!=0).
В простое дополнительных вызовов/работы нет; от числа NPC/игроков не зависит.
Измерения игрового FPS этой ревизии не выполнялись.

Проверки:
- test_independent_death_destination: production Begin+Tick, обе роли и оба
  режима; смерть→победа→late entry, победа после entry, native entry без
  предварительного HP0, старая победа/следующая смерть, settle и load fence PASS.
- BBSC_TEST_BOSS_BEFORE_SPECTATE_OLD=1 возвращает прежнее сравнение только
  в production Tick: ожидаемый FAIL на delayed-death regression (negative PASS).
- test_repeat_death: production lifecycle/rearm, исходная метка существует
  при handoff; first/repeat, partial failures, teardown/session/load fences PASS.
- test_boss_lamp_respawn: победа до spectate допускает правильную лампу,
  19destinations/host/guest, старые победы/map/load/unavailable guards PASS.
- Полная MOD syntax-проверка bloodborne_re.cpp clang++ exit0, без диагностик.

Пользовательские dirty-правки сохранены; pin не менялся. Сейвы/settings/игры
не изменялись. Не считать баг игровым образом закрытым до повторного прогона.
