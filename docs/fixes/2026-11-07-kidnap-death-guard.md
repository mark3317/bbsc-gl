# Обычная смерть не ждёт тюрьму — 07.11.2026

Статус: SOURCE FIX, production regression PASS. Build/deploy/start и gameplay
фиксируются отдельно в HANDOFF и parent run.md. Новых опросов нет.

## Доказательство

Предыдущий run235555/235553, read-only restored-live-flags.json:
оба HP0/loading0,9420=0,9421=1,9422=1,9423=0. Точки2412951/2102961,
не prison2802959. BeginBbscCoopDeath считал это pending и выставлял reload;
TickBbscSpectate ждал Ready=false. Повторы handoff не могли снять эту блокировку.
Источники: parent out/coop-dev/runs/death-respawn-20261106/restored-retest-pc-later
и restored-live-flags.json. Причина происхождения исторических completion bits
в этом прогоне не объявляется установленной.

9421 — флаг завершения native common event, а не сам по себе текущий запрос
похищения. Native lethal-hit detectors12400780/12700500 ставят9420;
common9421 выбирает2802959, сбрасывает9420 и завершается(9421=true).
Поэтому pending теперь: independent travel разрешён, !9423 и
(реальный9420 ИЛИ existing Ready:9421+point2802959). Один9421 вне тюрьмы
больше не останавливает обычное возрождение. Точка без9421 тоже не запрос.

Использованы существующие флаги/проверка готовности/native events. Нет нового
состояния, hook/tick/таймера/повтора, обработки врагов или сетевого сообщения.
Никакие игровые флаги вручную не сбрасываются. При реальном9420 исходное
ожидание подготовки тюрьмы сохраняется; после выбора2802959 его продолжает
existing Ready. Завершённое9423 и feature-off не перехватывают смерть.
Idle path не меняется: TickSpectate вызывает guard только для уже активной смерти;
внутри старого predicate добавлено лишь чтение checkpoint при историческом9421.

## Проверки

- test_snatcher_abduction: production predicate, точная live комбинация9421/9422
  с ordinary/Dream checkpoints2412951/2102961/2702951, настоящий9420, переход
  к9421+2802959, completed9423, feature-off и существующие guest-event guards PASS.
- BBSC_TEST_KIDNAP_PENDING_OLD=1 возвращает только прежний predicate в fixture:
  negative control ожидаемо FAIL на точной обычной смерти из live снимка.
- test_independent_death_destination теперь использует реальные production
  KidnapDeathPending/Ready вместе с Begin/TickSpectate, а не boolean-заглушки.
  Исторические9421/9422 включены по умолчанию. Host/guest ordinary death идут
  в existing curtain, без reload/warp; boss death остаётся spectate; настоящий
  delayed prison request ждёт подготовки, затем делает одну native load. PASS.

Остальные dirty-правки сохранены. Код в коммитах ограничен этим predicate,
связанными тестами и новым отчётом; HEAD исходноf3d37e1, parent pin6e7d32f.
Игры не завершались; реальные сейвы/settings/assets вручную не менялись.
