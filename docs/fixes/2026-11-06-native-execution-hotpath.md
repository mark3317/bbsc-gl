# BBSC: сокращение вмешательства в штатное исполнение — 06.11.2026

Обновление16:42 МСК: DLL собрана exit0/8 warnings и установлена delta на ПК
и ноутбук exit0. Сейв before-rom-20261106-064652 восстановлен на обоих после
полного резервирования текущих данных. Native37684/17868 запущены16:42:36/52;
BBSC PERF и кадровой PERF/PACING подтверждены. Timeline/combat/research/net/Party
diagnostics OFF. Игровой эффект ещё не оценён; исходный статус ниже исторический
для сборки/установки. Подробности: parent
`out/coop-dev/runs/native-execution-pc-laptop-20261106/run.md`.

Статус: изменения исходников и целевые production-fixtures проверены;
MOD C++ syntax exit0. Новая DLL не собиралась, не устанавливалась и не
запускалась. Игрового замера этой правки нет; рост FPS не установлен.
Задача снижения общего расхода мода остаётся открытой в перечисленных ниже местах.

## Состав и исходная стоимость

- До работы HEAD и parent gitlink совпадали: `6e7d32f71199d17bae124aa768bc5e3ea46278bd`.
  Был изменён HANDOFF; в parent был новый отчёт сравнения. Эти материалы сохранены.
- Установленный `coop/SOURCE.json`: `bbsc_commit=4989896fd19fb9b9dd908d52c345a62b3b82b6c6`,
  `source_dirty=true`, `version=1.2.0`. DLL имеет время 06.11 06:30:58,
  bbsc-launch — 06:31:00. Состав общей dirty-сборки описан в parent
  `out/coop-dev/runs/rom-pc-laptop-20261106/run.md`; позднее отдельно менялся Party compat.py.
  Этот metadata commit не доказывает тождество установленной DLL чистому HEAD.
- Релизный BBSC `v1.2.0` — `bdd59b7`; он отличается и от установленной DLL,
  и от нынешних исходников. Связанный чат «Подготовь прогон на двух профилях»
  завершил анализ и подготовку задания; активной конкурирующей сборки при проверке не было.
- Основания: parent `2026-11-06-v120-load-comparison.md`,
  `2026-11-06-bbsc-hotpath-results.md`, BBSC `2026-11-06-bbsc-hotpath-optimization.md`.
  Общий pre-event callback: около 655–657 вызовов/тик и 2.115–2.116 мс/тик
  в ПК-прогоне; ноутбучный неполный отрывок — 3.783 мс/тик.
  Это elapsed, не exclusive CPU. Родительские и вложенные scopes не складываются.

## Внесённые изменения

1. При построении проверяемого EMEVD range index вычисляется immutable маска
   обработчиков. Обычный шаг после bootstrap не вызывает обработчики поездок,
   Ром, похищения, дверей, финала, предметов и kit gift, если его descriptor
   к ним не относится. Квестовые/чашные личные события остаются консервативным
   множеством для pickup-проверки; это не кеш динамических условий.
2. Общий resolver по-прежнему проверяет live instance/ref/file/header/row/PC,
   адреса, длины, epoch и пересечения. Замена строки по прежнему адресу заново
   классифицирует событие. Неопределённая идентичность сохраняет прежний guarded
   dispatch. Native reset sync byte не кешируется: следующий личный шаг снова
   локализуется. Role/map/flags/инструкции и guards остаются динамическими.
3. Удалён отдельный кеш идентичности из EnableBbscNativeTravelEvent.
   Он дублировал общий индекс, а пара instance/ref сама по себе не доказывала
   неизменность event row. Неизменённый network-sync byte больше не записывается.
4. Успешный допуск native блоков получает revision certificate под block mutex.
   Capture инвалидирует его ДО чтения native inventory; принятая lease и смена
   world также повышают revision. Перед быстрым возвратом проверяются active,
   scope, inventory-ready и native load. Ошибки/ожидание не кешируются.
   При разблокировке mutex вокруг native apply изменение revision не позволяет
   сертифицировать устаревший проход. Межкадровых разрешений на память нет.
5. TickWorldBlocks проверяет capabilities по ссылке под presence mutex без копии
   membership map. Публикация читает local/withdrawn records по ссылкам, сохраняя
   прежний приоритет local при совпадении ключей; временная объединённая map
   и копии native vectors удалены. Heartbeat, частота и последовательности сохранены.
6. Ownership вычисляет scene-ready и режим блоков один раз в текущем callback,
   не на каждого NPC. Значение ownership word записывается только при отличии.
   Native backread-off, requested!=4 и disable по-прежнему снимают владение;
   прежнее состояние current4 не может повторно включить выгружаемого NPC.
7. Четыре входа NPC lifecycle diagnostics при выключенном timeline возвращаются
   до mutex, чтения session/map/load и поиска акторов. Функциональные ownership,
   WakeBegin/End и HP hooks сохранены. Переключатель timeline фиксируется при
   старте процесса; это не runtime-переключение функциональности.

Штатный интерпретатор продолжает ожидания, проверку условий, анимации, завершение
событий и warp. Штатные native history apply/HP/death/revival/loot не заменялись.
Удалены повторная классификация специализированными путями, повторный обход
уже допущенных блоков, временные копии и записи прежнего ownership, а не возможности коопа.

## Карточки обработчиков

### Общий BbscNpcPassHook и локализация

- Кооп: личные события без удалённого stage, границы допуска и локальных команд.
  Native: один интерпретатор EMEVD исполняет текущую команду/условия/reset.
- Вызов: перед каждым шагом любого события, не только NPC. Данные: descriptor,
  instance sync byte, текущие условия guards; второй проход личных флагов.
- Повтор: прежний набор specialized guards для каждого события и повторный lookup.
  Общий resolver и бывший travel cache выполняли одинаковую идентификацию.
- Триггер: новое/перестроенное описание, load epoch, native sync reset, новая PC
  или текущие role/map/flags. Классификация теперь привязана к descriptor;
  динамические условия не перенесены в долгоживущий кеш.
- Удалить весь callback нельзя: вернутся чужие квесты/переходы и исполнение до
  готовности мира. Стоимость подтверждена прежними PERF и новыми счётчиками dispatch.

### GuardBbscWorldBootstrap / BbscWorldAdmitBlocks

- Кооп: история общего мира должна предшествовать NPC/event initialization.
  Native FirstSync привязан к единому миру хоста, недостаточен для разных карт.
- Вызов: каждый EMEVD шаг и block tick. Чтение: session, map/load, world scope,
  requested scope, flags readiness, lease, inventory, applied epoch. Изменение:
  bootstrap marker и native history при первом допуске нового epoch.
- Повтор: обход того же admitted inventory; тик уже делает такой допуск.
  Certificate убирает именно этот обход, не начальную live проверку контекста.
- Инвалидация: inventory capture, world, lease revision, load, scope. В каждом
  capture revision повышается даже при прежнем результате: полного доказанного
  native streaming dirty signal ещё нет. Это сознательная граница оптимизации.
- Полное удаление нарушит bootstrap; local travel bypass и Dream state4→6 fence
  сохранены. Средний прежний capture — 0.073/0.084 мс/тик; полный вклад bootstrap
  отдельно не измерен. В fixture 2000 готовых допусков дают 0 новых обходов/serialize/apply.

### TickBbscWorldPresence / membership / TickBbscIndependentWorld

- Кооп: разные локации, комнаты, посещения, роли и доступность участников.
  Native room membership не равнозначен присутствию на конкретной карте.
- Вызов: каждый tick; presence публикация при изменении или heartbeat раз в 1 с.
  Читает room/session/player transform/HP/load/map/ritual; пишет presence/place/role.
- Повтор: discovery текущего контекста и копирование membership в дочерних задачах.
  В block tick копия убрана; coordinator сохраняет свой согласованный snapshot
  после освобождения presence mutex, поэтому его копию нельзя просто заменить ссылкой.
- Триггер: room/map/load/visit/phase/alive/ritual/capability, состав группы и liveness.
  Часть данных native меняет без mod-события; heartbeat не заменяет детектор изменений.
- Полное удаление восстановит follow/authority единого host world. Полный расход
  independent tick не выделен из общего около 2.8 мс/тик; отдельного нового CPU замера нет.

### Capture / block publication / coordinator

- Кооп: передача native истории блока и одного владельца между независимыми картами.
  Native Serialize0190E750 и Apply0190E8B0 остаются источником/потребителем истории.
- Capture: каждый допустимый tick; читает block/CHR lists, group masks, handles,
  сериализует native death bits. Публикация — прежние 100 мс; leases имеют heartbeat.
- Повтор: сбор прежнего inventory, временная merged reports map, повторное encode.
  Временная map удалена; native capture/encode полностью не устранены.
- Триггер: streaming membership/actor generation/death history/group masks,
  visit/load/scope, lease epoch и retirement ack. Один mod event не покрывает все
  native writers; перенос capture за таймер или кеш по одному указателю небезопасен.
- Без capture/handover появятся пустые блоки, двойная симуляция или потеря истории.
  Native fixture покрывает streaming/reload/visit/epoch/count mismatch и vacancy;
  live редкие пики сериализации отдельно не объяснены.

### BbscWorldOwnership

- Кооп: local simulation соответствует block lease, не native host role целой карты.
  Native activation/backread/disable определяют, может ли NPC вообще симулироваться.
- Вызов: native ownership pass, обход неигровых акторов. Чтение: live ownership
  word/control/request/backread, players, Doll и responsibility; запись только word.
- Повтор: прежнее word и scene-ready/map mode на каждого NPC. Общий контекст вынесен
  в текущий проход; неизменённые слова не пишутся.
- Триггер: native активация/выгрузка/disable, lease, роль, scene и состав акторов.
  Межкадровое пропускание всего обхода требует полноты этих native сигналов; её нет.
- Удалить весь hook нельзя: симулятор будет выбран по роли всей карты.
  В fixture обе responsibility роли: 2000 неизменённых проходов дают 0 записей;
  новая requested0 снимает владение сразу, requested4 возвращает допустимое владение.

### WakeBegin / WakeEnd

- Кооп: штатный wake учитывает группы других присутствующих охотников.
  Native использует локального охотника; мод временно дополняет group masks,
  а original wake выполняет собственные activation/unload решения.
- Вызов: начало/конец native wake; читает текущих игроков, HP/place и 3×8 group words,
  временно пишет маски блоков и восстанавливает их в конце.
- Повтор: одинаковые masks и restore. С ownership это разные данные/границы;
  отключение ownership не заменяет wake. На этот проход новая оптимизация не внесена.
- Триггер: group streaming, движение/смерть/выгрузка игроков, запросы native wake.
  Без полного сигнала native изменения нельзя кешировать маски по map/load.
- Полное удаление может усыплять NPC рядом с другим игроком. Отдельного live native
  времени нет. Оригинальная backread-off ветвь и read-only diagnostics проверены fixture.

### HP / hit / animation / packet filters

- Кооп: текущий владелец конкретного блока производит состояние и принимает урон.
  Native роль привязана к host/guest целой карты, HP receive имеет single-source ABI.
- Вызов: native send/receive rounds, пачка и record/handle. Чтение: channel/size,
  sender/recipient, current scope и block owner; фильтруется рабочая копия пакета
  либо native receive buffer, временно выбирается native role/source.
- Повтор: owner lookups по record, provider set и дополнительные native receive
  после send. Это не параллельная модовая HP-симуляция и не удалено этой правкой.
- Триггер: новый пакет, смена lease/scope/member/HP dirty. Здесь нельзя кешировать
  приемлемость отправителя между пакетами или выключать dirty producer/receive.
- Без этих границ вернутся чужие NPC, потеря попаданий и задержки native смерти.
  Сетевые фильтры/target ownership покрыты block fixture, native HP код не менялся.
  Полная цена оригинальных дополнительных rounds и вклад каждого канала НЕ измерены;
  время callback не выдаётся за их стоимость. Kill/HP0/model-hide/timer обходов не добавлено.

### Личные флаги и native receipts

- Кооп: чужой world snapshot не завершает личные квесты/получение предметов.
  Native SetFlag и completion/receipt writers остаются источником личного результата.
- Вызов: tick и ещё раз перед event/talk; группы читаются пачками, 826 бит сверяются
  с собственной копией, чужие значения восстанавливаются; native receipts сохраняются.
- Повтор возможен при отсутствии записи между проходами, но такая запись реально
  возможна через сеть/native между tick и EMEVD. Два прохода не эквивалентны одному.
- Триггер для будущего skip: доказанные ревизии ВСЕХ writers и backing table.
  Текущий SetFlag hook не покрывает весь набор; грязность одного журнала недостаточна.
- Удаление второго прохода может потерять подарок/дублировать receipt. Прежние
  0.441/0.306 мс/тик включают mutex/lookup/native receipt; сохранены групповые чтения.
  test_native_pickup_state подтверждает личную изоляцию без реальных сейвов.

### Тексты / TickMessages

- Кооп: сообщения и подписи группы; native FMG управляет загрузкой/языком/заменой слотов.
  Вызов: dirty work и лёгкая 2-секундная проверка native replacement.
- Чтение/запись: live repo/category/table/row/slot с проверкой поколений; неизменённые
  tick уже не делают memory queries. Resolver/category/slot reuse ранее оптимизированы.
- Повтор native slot check нужен, потому что игра может заменить указатель без
  смены repo. Полного сигнала всех replacements не доказано; новый skip не добавлен.
- Без обработки — устаревшие подписи/пропавшие замены. Предыдущие пики >16 мс
  снизились 129→9 и 396→19; оставшиеся 32–42 мс не объясняются одним полным поиском.

### Scaling / PARAM lookup

- Кооп: масштабирование числа охотников; native PARAM задаёт HP/damage/stagger.
  Tick выбирает scale key; неизменённый idle уже пропускается с проверкой owners в 1 Гц.
- Данные: repo/type slot, table identity/count, строки effects/NPC; armor пишется
  ограниченными batches и только при изменении key или перестройке таблицы.
- Кеш slot offset существует: cache hit проверяет текущий repo slot/table/type;
  miss перебирает offset 0x08..0x1000. Это не полный поиск при каждом вызове.
- Триггер: новый scale key, load generation, table/count/repo/slot change и retry
  после недоступной таблицы. Права на row проверяются до текущего batch записи.
- Удаление owners validation опасно при reload/address reuse. Прежний пик
  `scaling table owners` 69 мс ещё не разложен на hit/miss/validation/OS preemption;
  functional trace/cache fixture PASS, новые частоты/кеши не добавлены.

### Диагностика

- Кооп-функции нет: lifecycle/combat/PERF/timeline только наблюдают.
  Native продолжает исполняться при выключенной диагностике.
- Вызов: event/wake/history/packet/tick. Данные: actor lookup, current/requested,
  scope и counters; engine bytes lifecycle не пишет.
- Повтор вне диагностики: четыре lifecycle входа раньше брали mutex и читали
  контекст до проверки enabled. Теперь они заканчиваются до этих действий.
- Триггер: явный запуск процесса с timeline; sample interval/budget/dedup остаются.
  Combat trace уже имеет отдельное включение, диагностические hooks отделены от functional.
- Отключение наблюдения уменьшает доказательность логов, не семантику коопа.
  Fixture: 2000 пар WakeBegin/End при OFF — 0 actor lookups и 0 session/map reads;
  trace policy сохраняет 35/168 выбранных sites, functional dispatch coverage PASS.

## Проверки и пределы результата

Исполнялись только затронутые fixtures и прямые зависимости, в исходном подмодуле.
Игровые EMEVD/analysis ELF использовались только для чтения; память сценариев синтетическая.

- test_event_identity_hotpath: equivalence старому linear resolver для 512 событий,
  18000→8000 queries на 2000 тёплых запросов (это прежняя оптимизация resolver,
  не новая заявленная экономия); новые 9 классов ×2000 шагов настоящего NpcPass,
  неизвестная identity fallback, native reset, in-place reclassification, reload/overlap/thread epoch PASS.
- test_world_blocks: новые counters admission/ownership; scope/lease/load/visit,
  malformed/streaming/vacancy/обе роли/native packet filtering PASS.
- test_transition_door_authority, test_native_transition_access, test_lamp_activation,
  test_world_travel_native: original door/travel chains, action/role/load gates,
  ordinary/chalice activation и native restart PASS.
- test_personal_npc_dispatch: 19 native контроллеров + оригинальный sender channel31 PASS.
- test_scripted_pickups, test_native_kit_gift, test_native_pickup_state:
  12 pickup/reward gates, оригинальный подарок/другие gifts и native receipts PASS.
- test_rom_native_transition: original EMEVD/iterator/Remo wait и штатный warp tail PASS.
- test_npc_lifecycle: original backread-off, read-only observations, budgets,
  roles/maps/load/recreation и diagnostic-OFF counters PASS.
- test_npc_ownership: native unload/disable/request имеет приоритет для обеих
  map/block ролей; игроки, Doll, offline и null-вход сохранены PASS.
- test_runtime_perf --npc-only, test_perf_policy: range reuse/reload/overlap,
  functional hook retention и PARAM slot validation PASS.
- MOD syntax `/Zs`: exit0, 28 предупреждений (в том числе getenv deprecation
  без suppress-флага этого syntax helper). Это не DLL build/link.

Не измерены: новая длительность callback в игре, native HP rounds, стоимость
streaming discovery, scaling miss/validation и оставшиеся редкие stalls.
Не заявляется процент ускорения относительно 1.2.0; сопоставимого парного прогона нет.
Сейвы/settings/game assets не менялись, backup прогресса сохранён,
коммиты/pin/push и установки не выполнялись.
