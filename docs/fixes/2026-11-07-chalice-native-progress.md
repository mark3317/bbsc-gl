> Актуальный статус,07.11.2026: **USER CONFIRMED / CLOSED**.
> Пользователь подтвердил сохранение прогресса первого слоя после повторного
> входа и синхронизацию ламп, включая лампу клиента в меню хоста.
> Полный список ламп выбранной чаши и переходы работают. Ранние FAILED/OPEN
> и промежуточные ограничения ниже — история расследования.
> Логи: parent out/coop-dev/runs/chalice-progress-confirmation-20261107/analysis.md.

> 07.11,05:31: RETEST PASS для полного seed, native host writeback вне карты,
> появления клиентской лампы в менюhost и повторного входа по ней.
> Первый boss clear по одному на участника, новых целевых ошибок нет.
> Визуальное состояние всех дверей/лифтов отдельно не журналируется;
> пользователь сообщает корректную работу. Evidence parent
> out/coop-dev/runs/chalice-progress-confirmation-20261107/analysis.md.

# Сброс первого слоя чаши и отсутствие клиентской лампы у хоста

BUILT / PC INSTALLED / P2 STARTED, run051950; gameplay OPEN.
DLL build/delta/deploy exit0,8прежних warnings, source inputs unchanged.
Current П1/П2 snapshot: D:/Games/Bloodborne/coop-dev/saves/chalice-tests-current-20261107-051618.
П2 no-death отключён; native startup05:19:50.774/35of35hooks.
Первоначальная разработка и границы проверок ниже.
Пользователь уточнил: сбрасываются двери/лифты/босс первого слоя, а точки
перехода к боссу и на второй слой остаются. Затем указал, что клиентская
лампа первого слоя не появляется в меню хоста. Действия всех участников
должны записываться в чашу хоста. Новые цикличные обработки запрещены.

## Причина

Ритуальная metadata94x00..05 и20lamp bits каталога НЕ являются полным
сохранённым прогрессом чаши. Original013B89B0 привязывает виртуальные
m29 группы к собственной постоянной памяти каждого слота через
013BC710(kind,40+slot,0,group). Банки1/6/7, по10групп, содержат прогресс
и событийное состояние. Native slot0 использует специальный native index;
арифметику индексов не заменять собственным stride по слотам.

Прежний BbscWorldCaptureFlags при host в Dream возвращал для чаши
flags_ready=true/present0, если current identity отличалась от destination.
BbscWorldFlagsReady считал такой epoch0 seed пригодным по наличию ритуала.
Это разрешало первому guest запустить m29 на личных/прежних event flags.
Его последующий owner snapshot мог заменить прогресс хоста. Это конкретный
исходниковый дефект, воспроизведённый allocated fixture; направление каждого
сброшенного флага в прежнем игровом логе отдельно не записано.

Второй дефект: World::ShouldApplyFlags исключает host off-map m29, поэтому
полный snapshot от guest owner оставался только в session cache. Лампы
принимались вbbsc_world_lamps, но host native12907 другой/невыбранной чаши
не обновлялась. Checkpoint2902953 уhost за15мс доказывал лишь принятие точки,
а не запись её native menu unlock. При смене native alias/cache данные могли
расходиться с постоянной записью чаши. Simple OR всех групп непригоден:
в них есть временные команды и многобитные значения.

## Исправление штатной привязки

- Общий BbscWorldNativeAltarGroup использует ОРИГИНАЛЬНЫЙ mapper с проверкой
  slot/kind/group/index/capacity/backing. На host capture и применение
  направляются в backing именно указанного world/key/ritual/slot, независимо
  от выбранного алтаря и текущей карты. Виртуальные указатели не перепривязываются.
- Первая preparation чаши читает реальные30групп host даже из Dream. Empty
  epoch0 seed больше не допускает m29 events; нужны все10progress groups.
  Неполный capture не отправляется в существующем snapshot producer.
- На существующей границе приёма полного snapshot от действующего guest
  owner host записывает его в свои native группы этой чаши, включая off-map.
  Существующие sender/owner/epoch/sequence fences сохранены. Other cups,
  personal guest world и metadata ритуала не становятся целью записи.
- На existing Lamps receive записываются lit+unlock в native host slot даже
  из Dream/другой чаши. Каталог помечается dirty только при изменении ламп.
  Исторические host lamps своей чаши не отзываются старым owner snapshot:
  сохраняются только20additive lit/unlock bits, без OR остального прогресса.
- Original menu conditions, door/boss events, waits, анимации, переходы,
  native сохранение, авторитет симуляции не заменялись.

## Стоимость и проверки

Новых hooks/ticks/опросов/таймеров/очередей/повторов/типов сообщений нет.
Wire/число/период существующих пакетов не менялись. Capture заменяет30поисков
virtual group на30native O(1) mapper calls; lookup slot — максимум7записей
каталога. Off-map persistence на complete packet добавляет копирование до
3750байт, т.е.7500байт/с для чаши с owner при существующем500ms producer;
для7одновременно активных чаш до52500байт/с, без actor/memory scans.
Лампа —20bounded bit updates на полученный discovery; переотправку и ack
обслуживает прежний канал. No new idle wakeups. Это оценка пути кода,
а не измерение игрового FPS.

PASS tools/test_chalice_progress_native.py: original013BC710+его реальные
таблицы из ELF,7slots/3banks, native host seed из Dream при пустых personal
aliases guest, production Request/four-part Flags receive, actual owner
writeback host off-map, re-entry с потерей cache, native first-layer boss
12901800 и progress receipt, лампа1слоя и boss lamp, разныечаши,
неполный capture, foreign sender/stale epoch/replaced ritual.
Шесть отдельных negative controls (seed, readiness, writeback, incomplete,
lamp persistence, lamp rollback) FAIL старого пути как ожидается.
PASS test_world_lamps (+historical-data negative), test_world_altars_native,
test_world_travel_native, test_world_native_bootstrap вdiagnosticmode0,
test_native_npc_sync_mode (оба режима/default, native m29 barrier,2000idle).
MOD /Zs PASS, build/chalice-native-progress-syntax.log (прежние CRT warnings).

Реальные сейвы во время разработки не читались/не восстанавливались.
Игровой критерий: guest открывает/проходит слой1 и зажигает лампу, host
видит её вменю; оба уходят вDream и повторно входят; двери/лифты/босс слоя1
сохранили прогресс, переходы к boss lamp/слою2 работают. Смена чаши и rejoin
не должны переносить чужой progress. Этот игровой результат ещё OPEN.
