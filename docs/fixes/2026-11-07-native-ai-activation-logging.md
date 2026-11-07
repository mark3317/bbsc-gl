# 07.11.2026 — событийное логирование назначения ИИ NPC

Добавлены только записи в существующий BbscWorldNpcActivated. Новых hooks,
циклов, ticks, опросов, очередей, таймеров, повторов и сетевых сообщений нет.
Поведение назначения ownership word сохранено. Реальные сейвы/settings не меняются.

## Строки

`WORLD ... | NPC AI activation ...` — одна строка на штатное successful activation
completion, включая назначение, уже имеющее нужное значение. Поля:
actor/handle, npc_map/local_map/scope_map, world(host/room), ritual, owner, epoch,
local_owner, personal_doll, before/desired/after, applied, visit/load.
`after` — новое непосредственное чтение native word; applied означает
совпадение с desired в этой точке, а не гарантированное состояние во всех
последующих кадрах. Значения1/FFFF — local/remote native authority.

`NPC AI activation skipped reason=...` — безопасный отказ после распознавания
NPC: sync-table, sync-slot, actor-list, actor-binding, block-data, map-info,
map-id, loading, no-owner, ownership-word. Player tables и неготовые/скрытые/
отключённые actor paths по-прежнему исключаются без шумных диагностик.
Запись делается вне presence mutex, включая loading/no-owner.

Для сравнения до/после возвращения хоста нужны activation records в обоих
интервалах: сопоставлять world/scope_map/ritual и owner/epoch, затем реальные
before/desired/after каждого NPC. После возврата активировать ещё новых NPC
или штатно реактивировать прежних. Если активаций после возврата нет, лог
не доказывает непрерывное сохранение words уже активных NPC. Смена роли карты
и присутствие хоста дополнительно видны в прежних PLACE/map AI commit строках.

## Стоимость и проверки

Обычный активный кадр не вызывает callback и не пишет строки. При выключенном
SHADPS4_BBSC_TIMELINE/BB_DIAGNOSTICS остаются прежние26 actor reads/event:
не читаются дополнительные данные NPC и нет формирования/записи строк.
При включённой диагностике — один дополнительный2-byte readback на успешную
активацию, snapshot нескольких scalar lease fields и одна строка порядка
нескольких сотен байт; объём растёт с числом реальных активаций, не кадров.
Записи идут в прежний logger; новая очередь/поток не создаются. Игровая стоимость
включённого диагностического вывода ещё не измерена.

Расширенный tools/test_native_npc_activation_ai.py исполняет original1.09
машину состояний и production Windows trampoline: данные фактической строки,
unchanged assignment, owner/epoch/adjacent map/visit/load, skip binding/loading/
no-owner и отсутствие логирования под presence mutex PASS.2000 stable updates:
0 callback/read/write и0 новых строк. Diagnostic-OFF2000 activation events:
0 строк,26 reads/event PASS. Whole MOD syntax exit0. Сборка DLL отдельно ниже.
Существующий negative control обновлён под новую форму before/write.

## 07.11 final build and deployment

Related lamp task completed; final combined DLL built exit0/8 inherited warnings,
source inputs unchanged, delta/deploy exit0,5files. Backup:
D:/Games/Bloodborne/coop-dev/backups/npc-ai-event-logging-20261107-20261107-013459.
P1/P2 launch requested01:35:00MSK after user-confirmed ordinary shutdown.
No code tests repeated for deployment. Startup pending; gameplay OPEN.
Startup confirmed07.11 01:35:25MSK: P1/P2 run_20261107_013524.log;35/35 selected hooks and NPC AI activation diagnostics ready marker in both. Native PIDs13960/11504. Gameplay OPEN.

## 07.11 run013524 — пользователь подтвердил FAILED для новых врагов без хоста

Сбор failed-pc/: exit0,2files,warnings0,оба ChangedDuringCopy=true. Это живые
снимки, а не завершённые логи. П1=53e832c5/game-7, П2=457f6279/game-14.
Снимок до01:55:55МСК. Fault/fatal не найден; relay продолжает обмен.

Подтверждено:
- П1 ушёл из чаши01:52:58.860 и прибыл в Dream01:53:01.494; до конца снимка
  остаётся там.
- П2 покинул Dream01:53:31.536 и прибыл Cathedral Ward0x18000000 в01:53:38.313;
  owner457f6279/role1 назначен01:53:38.429, visit14. Далее lease не меняется.
- В позднем интервале нет ни одной строки NPC AI activation у П2.
- Во ВСЁМ прогоне successful assignments П2=105, П1=48; все имеют
  npc_map0x15000000 (Dream), все applied=true. Ни одного assignment в чашах
  или обычной боевой карте нет, включая периоды с хостом на карте.
- Skips П2: loading36, no-owner9; П1: loading27. No-owner01:45:47 относится
  к более раннему переходу в Dream, а не к финальному сценарию Cathedral.
- Следовательно нельзя приписывать текущий отказ отсутствию map lease,
  applied=false или доказанной поздней перезаписи word: этих свидетельств нет.

Отрицательное игровое подтверждение пользователя: новые враги не имеют ИИ,
когда хост отсутствует в мире. Диагностика показывает неполноту выбранной
границы018BD488 и/или ранних guards до первой строки: callback пишет assignment
только в Dream. Из имеющихся строк нельзя различить невызов для боевого NPC
и ранний выход до логирования (control/backread/handle/player-table checks).
Писать «успешно назначено, но затем сброшено» было бы недоказанным.

Граница тестов: fixture запускал native dispatch с уже готовой synthetic
actor/list/control привязкой и stub Setup, то есть не проверял полный настоящий
путь гостевого появления/допуска AI без room host ДО successful completion.
Тесты этого уровня не закрывают наблюдаемый live отказ. Следующее исследование
должно локализовать штатный ранний допуск/создание/пробуждение новых боевых NPC,
а не добавлять постоянный ремонт words или повторные обходы.

Статус: AI gameplay FAILED / bug OPEN. При проверке код/бинарники/настройки/
сейвы и процессы не менялись; новых циклов/опросов/диагностики не добавлено.
