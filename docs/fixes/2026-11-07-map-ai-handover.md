# Map owner и управление ИИ — 07.11.2026

Статус: SOURCE FIXED / targeted tests PASS / NOT BUILT / NOT INSTALLED / gameplay OPEN.

## Изменение

В существующем TickBbscIndependentWorld точка публикации owner/role теперь вызывает
BbscWorldPublishOwner. Эта функция в том же игровом потоке публикует карту/роль и,
только при изменении owner/role либо native visit, однократно применяет существующий
BbscWorldOwnership к текущему загруженному миру. Сетевой Coordinate/OwnerBook по-прежнему
работает только с метаданными; native pointers на сетевом потоке не используются.

Применение использует прежние штатные ownership words NPC:1 для локального управления,
FFFF для удалённого. Оригинальный predicate0191AAE0 читает signed word из той же таблицы
и возвращает локальное право симуляции. Сохранены прежние проверки requested unload,
backread-off/disable, исключение игроков и личное поведение куклы. HP, позиции, флаги
смерти, анимации и visibility не переписываются. Никакие ownership/wake/HP hooks
не включены, обычные native packets и load-only state transport не менялись.

Повторный owner с тем же значением/ролью/visit не касается actor memory. Возвращающийся
хост не отбирает lease у оставшегося участника согласно существующему ChooseOwner.
Новая загрузка инвалидирует прежнее применение. При отсутствии загруженного world
пишется предупреждение, нет ожидания/повтора: следующий отдельный load — новая граница.

## Стоимость и ограничения

Нет нового таймера, опроса, очереди, сетевого сообщения или hook. В прежнем месте записи
двух atomic полей добавлено сравнение прежних значений; при неизменном owner нет
чтений NPC и аллокаций. На смену — один существующий обход загруженных NPC/players,
O(число загруженных NPC + players), запись word только при отличии. Вне этой границы
периодического восстановления ownership нет. Это не снятие нагрузочных ограничений:
реальная длительность прохода/влияние на кадр и игровой native handover ещё не измерены.

## Проверки

- tools/test_map_ai_handover.py: production ChooseOwner + OwnerBook + publish + реальный
  walker/table/word application; уход хоста, оставшийся при возврате, gain/loss,
  новый visit, stale/duplicate lease, сохранение player/unload/actor/controller data PASS.
- 2000 одинаковых публикаций после takeover: 0 actor reads/writes/traversals PASS.
- BBSC_TEST_EBOOT=parent/out/exit-study.elf: оригинальный0191AAE0 исполняется на fixture
  и видит смену native local simulation false/true PASS. ELF только читался.
- Negative control BBSC_MAP_AI_NEGATIVE=1 убирает применение, оставляя metadata:
  ожидаемый FAIL на первой проверке authority; контроль принят.
- test_native_npc_sync_mode.py: native/default и прежний режим, installation/travel,
  2000 ticks, cup admission PASS (fixture обновлён для новой точки публикации).
- test_npc_ownership.py, test_world_presence.py PASS.
- test_independent_native.py + original1.09 hook/callable spans PASS.
- Полный bloodborne_re.cpp BBSC_MOD -fsyntax-only clang++ C++23 PASS, exit0.

DLL не собиралась, delta/установка/запуск не выполнялись. Игровой эпизод и поздняя native
передача/перезапись authority после ухода хоста требуют проверки в игре; predicate fixture
не доказывает исправность всей native packet/HP/animation цепочки. Сейвы/settings и
работающие процессы не менялись. Исходные незакоммиченные чужие правки сохранены,
HEAD46a4ac2 / parent pin6e7d32f не менялись.

Deployment07.11: DLL build exit0/8 inherited warnings, stable inputs; delta/deploy exit0, PC5files. Backup map-ai-handover-20261107-20261107-004456. P1/P2 launch requested00:44:56MSK. Gameplay OPEN; parent run map-ai-handover-deploy-20261107.

Startup confirmed07.11 00:45:20MSK: P1/P2 run_20261107_004519.log,35/35 selected hooks each, new AI authority at map owner commit banner present in both. Profiles distinct3658/3659. Gameplay OPEN.

## Проверка живого прогона 07.11, снимок до00:48:17МСК

collect exit0,2files,warnings0,оба ChangedDuringCopy=true. Источник retest-pc/,
P1 game-7 / P2 game-14, оба run_20261107_004519.log.

- П1bb36a89f в Соборном округе00:46:14.821 получил role1; П2f9db4ebf
  прибыл00:46:32.811, role2 и initial state applied=true.
- П1 запросил Сон00:47:05.751; loading00:47:09.884.
- П2 в00:47:09.905 выполнил map AI authority committed:
  owner=f9db4ebf role1 previous=bb36a89f/2 new_visit=false. Задержка21ms.
  П2 остался в той же карте/visit3, без загрузки.
- PERF подтверждает1 вызов measure NPC ownership в этом окне:8278us.
  Прежний follower admission был56us; это разные состояния/нагрузка, не
  контролируемое сравнение и не доказательство отсутствия регрессии. Есть
  единичный пик >8ms; общий FPS после ухода порядка56–59, сравнимого A/B нет.
- П1 прибыл в Сон00:47:12.454 и получил отдельную role1 для Dream.
- У П2 в00:47:28.430 зафиксирована native enemy loot eligible=true. Это
  событие добычи, НЕ доказательство корректного агро/движения/ИИ.
- Повторных map AI authority commits у П2 после takeover в снимке нет.
  Relay00:48:15.252 очередь0/dropped0, процесс продолжает кадры.
- Возвращения П1 из Dream в Соборный округ в этом снимке НЕТ. Поэтому
  сохранение управления у П2 при возвращении хоста ещё не подтверждено.

Статус: execution of departure handover подтверждён логом/счётчиком;
фактическое поведение ИИ и сценарий returning host остаются OPEN.
Никаких правок кода, сборки/установки, завершения процессов или изменений
сейвов/settings при проверке не выполнялось.

## 07.11 — пользовательский результат: FAILED, streaming regression OPEN

Пользователь: после ухода хоста П2 далеко отбежал, у новых мобов не было ИИ;
после возвращения П1 все начали реагировать на П2. Это отрицательное игровое
подтверждение однократной правки. Прежний LOG CONFIRMED означает лишь вызов,
а не исправление игровой ошибки.

Новый сбор return-streaming-pc/: collect exit0,2files,warnings0, снимки живого прогона.
П1 loading из Dream00:48:27.213, arrival00:48:32.070 в Central Yharnam0x18010000,
owner=bb36a89f role1. П2 остаётся Cathedral Ward0x18000000/visit3 с owner=f9db4ebf
после takeover00:47:09.905. У П2 нет нового map AI commit в момент возврата;
в00:48:32.088 только native peer recreation. Эти карты смежные, поэтому это не
повторное вступление в одну metadata scope. П1 снова уходит00:48:56.726 и
прибывает в Dream00:48:59.307. Реакция NPC — наблюдение пользователя, не замер
ownership words из лога.

Причина неполноты установлена в коде: BbscWorldPublishOwner обрабатывает только
текущий actor table, не нативный алгоритм назначения будущих/заново активированных
NPC. Оригинальный0191AAE0 тестировал лишь чтение уже назначенного signed word,
не streaming. В original1.09 routine018ECEB0 native branch018ED006 сравнивает
MatchingState+124 с3; далее host path018ED0D0 сбрасывает native ownership arrays
и018ED146 назначает1 элементам. Штатные ownership handout018F0780/018F080C тоже
зависят от роли3; это отдельный native path, metadata map owner не используется.
Это объясняет ограничение реализации; конкретная live последовательность
инициализации/перезаписи words новых NPC не трассировалась.

Изучены native table lifecycle:018EB900 инициализирует одну таблицу,
018ECCCF/018ECCD4 создают/публикуют таблицу,0191550A и018ECE9A вызывают initializer
в собственных native проходах. Эти точки НЕ объявлены готовым исправлением:
инициализация таблицы и последующая активация на расстоянии различаются.
Возвращать повторный ownership/wake проход или добавлять к existing tick новый
ремонт нельзя по требованиям пользователя. Нужна штатная связь с map owner в
назначении/активации NPC, с проверкой позднего streaming и соседних карт.
В этой проверке новых hooks/циклов/опросов и изменений поведения не добавлено.
