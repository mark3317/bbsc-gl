# 07.11.2026 — лампы чаш: прямые штатные запросы

Исторический статус до сборки и игрового подтверждения: SOURCE READY / целевые проверки PASS / DLL этой правки не собрана
и не установлена / игровой результат OPEN. Пользователь сообщает отказ
зажигания и возврата как в сессии, так и вне неё; затем попросил максимально
вернуть штатный путь, если проверки проходят.

## Изменение

QueueBbscWorldTravel больше не поглощает72900100..72900109: исходный
ESD c1_11 немедленно пишет исходный флаг. Original12907020 самостоятельно
выполняет анимацию101160, ожидания,9020..9026 и выбирает2102954..2102960.
Existing NativeWarpBegin принимает уже начатую штатную поездку только при
реальном stage request. До этого нет очереди BBSC, подмены точки2102950,
запросов destination snapshot и mod input lock для этого маршрута.
Штатные локальные условия и их завершение не переписываются.

Найден подтверждённый code gap: IsTravelCommand не включал запросы зажигания
72300200 и аналоги (включая72900200..209). Поэтому scoped guest command-range
hook не допускал их, а существующие NoteBbscTalkFlag / ReadBbscTripJournal /
ApplyBbscTalkJournal могли учитывать одноразовый запрос как личный quest flag.
Добавлена отдельная классификация IsLampActivationCommand: допускается исходная
команда гостя и исключается из журнала; Queue немедленно возвращает false,
поэтому зажигание никогда не превращается в запрос перемещения. Обычные
и чашные команды проверяются по оригинальным ESD, workbench70000100 исключён.

Сохранены локализация native activation/return events и channel31 isolation,
общее открытие ламп, реальные checkpoints и ritual-scoped initialization.
Отключить всю интеграцию мода означало бы вернуть чужие анимации и потерять
независимые поездки; здесь снято вмешательство в сам запрос и ожидание чаши.

## Доказательства и ограничения

Свежий P1 run_20261107_011256.log содержит solo m29/load7 в01:20:01,
но не содержит историю команды72900xxx/состояние её native event при нажатии.
Это НЕ доказательство конкретного пропущенного условия. Ранее описанная
причина admission в fixes/2026-11-06-chalice-lamp-admission.md остаётся
предварительной; её наличие не доказывает устранение текущего отказа.
Точные live range bounds также не записаны. Подтверждён code gap в допуске
и журналировании, но полная причина solo-отказа ещё НЕ установлена.
Нельзя объявлять игровой баг закрытым по этим fixtures. Реальные сейвы,
их журналы и настройки не менялись; старые флаги в сейве не сбрасывались.

## Проверки

- test_chalice_dream_return:10 ESD lamp variants, solo/host/guest; оба запроса
  остаются native, очередь/ожидание/дополнительная рассылка отсутствуют;
  исходная карта чаши сохраняется до реального warp;7 native Dream points.
  BBSC_TEST_EBOOT=parent out/exit-study.elf: исполнен оригинальный range gate
  0204232E..02042356 и native reject branch в выделенной памяти.
  BBSC_TEST_GAME: оригинальные10 ESD и их номера запросов PASS.
- Два negative control: прежний отказ activation range и прежнее поглощение
  m29 return ожидаемо ломают production regression. Никакой правки live source.
- test_world_travel_native, test_lamp_dream_returns (включая read-only assets),
  test_lamp_activation (53 original activation calls), test_world_lamps PASS.
- test_travel_parallel_preparation и test_travel_departure_lock PASS;
  fixtures очереди теперь проверяют только маршруты, использующие очередь.
  Новый прямой m29 path проверяется отдельно, включая отсутствие dispatch hold.
- Whole bloodborne_re.cpp BBSC_MOD syntax, diff --check PASS.

Новых hooks, ticks, опросов, таймеров, очередей, повторов или сетевых сообщений
нет. Периодические расходы m29 return снижены удалением этапа mod queue.
Классификатор имеет быстрый выход для остальных флагов, один bounded lookup
для реального lamp request. Native idle/actor loops не менялись. Frame cost
в игре не измерялся. Параллельный чат ИИ готовит согласованную DLL;
сборку/установку в этом чате не запускали и процессы не завершали.

## 07.11 final build and deployment

Related lamp task completed; final combined DLL built exit0/8 inherited warnings,
source inputs unchanged, delta/deploy exit0,5files. Backup:
D:/Games/Bloodborne/coop-dev/backups/npc-ai-event-logging-20261107-20261107-013459.
P1/P2 launch requested01:35:00MSK after user-confirmed ordinary shutdown.
No code tests repeated for deployment. Startup pending; gameplay OPEN.
Startup confirmed07.11 01:35:25MSK: P1/P2 run_20261107_013524.log;35/35 selected hooks and NPC AI activation diagnostics ready marker in both. Native PIDs13960/11504. Gameplay subsequently confirmed below.

## Игровое подтверждение07.11 — CLOSED

Пользователь подтвердил: зажигание и возврат в Сон работают. В run013524
П1/host зажёг2902952 в01:48:59.667 и2902953 в01:49:31.044; П2/guest
зажёг2902954 в01:52:48.023, хост принял общий checkpoint в01:52:48.033.
Возвраты обоих: native stage request queued=false с точкой2102955/2102956
и последующим AREA Hunter's Dream. Вне сессии П1 обновил native checkpoint
2902950→2902951 в01:37:08.431 и вернулся в Dream01:37:22.023; П2 также
имеет solo progression ламп01:41–01:45. Точная старая solo-причина отдельно
не доказана; это не отменяет подтверждённого исправления сценария.
Collect exit0,2files,warnings0,оба live ChangedDuringCopy; снимок до01:54:55.
Fault/fatal в собранном интервале не найден. Код/сейвы/settings не менялись.
Evidence parent out/coop-dev/runs/chalice-lamps-confirmed-20261107/pc и run.md;
подробности fixes/2026-11-07-chalice-lamps-native-requests.md. Предыдущие OPEN
и SOURCE READY ниже исторические; повтор только при новой регрессии.
