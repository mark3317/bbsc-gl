# Обычная смерть не ждёт тюрьму — 07.11.2026

Статус: PC INSTALLED, production regression PASS, gameplay PASS. Блокировка
обычной смерти с живым напарником исправлена и подтверждена обоими профилями
и пользователем. Новых опросов нет.

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

## Игровое подтверждение — 07.11.2026

Статус: gameplay PASS, баг блокировки обычной смерти закрыт для проверенного
сценария свободного мира с живым напарником. Пользователь: «все работает как нужно».

Сбор retest-pc exit0,2files,warnings0; оба run_20261107_001041.log:
- Player1/game-7, host: SoloPlayDeath00:11:51.768 -> revived00:11:55.042,
  HP594,type0, возврат к лампе(-193.40,-28.65,68.50). PLACE alive1,
  та же Central Yharnam/map0x18010000/visit1, роль host сохранена.
- Player2/game-14, guest: PartyGhostDeath00:12:31.910 -> revived00:12:36.169,
  HP594,type1, та же лампа; PLACE alive1,map0x18010000/visit2,
  роль guest сохранена. Штраф21779 echoes применён, stain21779, now0.

Оба возрождения явно logged как respawn in place(no boss fight); смены visit,
выхода из комнаты и повторов watchdog/kidnap-wait между смертью и revival нет.
Затемнение без экрана загрузки подтверждено пользователем; лог подтверждает
in-place path. Настоящее похищение/боссы этим игровым прогоном не проверялись
(их прежние целевые production tests PASS).
Сбор снят во время работы игр: ChangedDuringCopy отмечен у двух файлов;
это живой снимок с завершёнными эпизодами смерти, не финальные логи выхода.
Артефакты: parent out/coop-dev/runs/kidnap-death-guard-20261107/retest-pc.
