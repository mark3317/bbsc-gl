## Игровое подтверждение пользователя — 06.11.2026

Пользователь подтвердил: «Да, видят друг друга в обоих направлениях».
После сборки/установки и запуска P1/P2 22:46:34 проверено перемещение
к уже находящемуся в локации участнику со сменой порядка прибывающего.
Регрессия видимости при повторной встрече ЗАКРЫТА для этого сценария.
Это не подтверждение исправления вылета П2 или других открытых багов.

Логи обоих участников сохранены в parent
out/coop-dev/runs/player-reunion-regression-20261106/confirmed-pc/;
files=2, warnings=0, ChangedDuringCopy=2.
Это снимки прогона, не доказательство завершения игровых процессов.
Логи содержат однократные recreation/render-hold bypass при встречах,
включая P1 22:48:44.981/22:49:43.458/22:51:35.907 и22:52:27.970.
Видимость подтверждена пользователем, не выведена из наличия actor.

# Повторная встреча игроков в native-NPC режиме — 06.11.2026

Пользователь сообщает повтор невидимости при загрузке к другому игроку.
История чата «Исправить отображение игроков» подтверждает последнее решение:
FirstSync снимает constructor draw bit у phantom types 1/2/12 до завершения
обычного призыва. После независимого перемещения хвост StageFlow уже завершён;
явное пересоздание retained-session игрока однократно пропускает этот AND.
Это scoped native render admission, а не постоянная правка прозрачности.

Собраны пять логов обоих локальных профилей; warnings=0, часть файлов менялась
при копировании. P2 guest входит в Central Yharnam 22:20:16.259, P1 host —
22:20:34.028. Оба startup log явно сообщают player-maintenance hooks OFF.
В коде native-NPC ветка не устанавливала существующий render admission hook
и не вызывала восстановление игроков. Это доказанный пропуск прежнего решения;
точные render bits в момент нового игрового отказа не сняты.

В native-NPC режиме возвращён только прежний player hook FirstSync и
существующий native removal/clear-arrival/recreation путь. NPC packet/HP/
ownership/wake/block hooks остаются выключенными. Перед установкой проверяются
оригинальные восемь байт AND и четыре callable prologue; ошибка оставляет
независимое перемещение неактивным.

По уточнению пользователя восстановление однократное, на загрузке/встрече.
Структурные изменения существующего presence увеличивают atomic revision;
heartbeat и координаты не будят player controller. При неизменном revision
и завершённом допуске — возврат до mutex, копирования membership и чтения
native actor/task/model. До готовности native task сохраняется только текущий
допуск, не более 15 секунд; после одной операции для данной пары visit/load
повторов и model watchdog нет. Новый сетевой пакет, hook или очередь не добавлен.
Первичный призыв остаётся штатным. Штатный FirstSync владеет созданием модели.
Старый периодический self-heal при active independent travel не запускается.

Для соседних map border сохраняется здоровый уже допущенный actor, в том числе
новый адрес, появившийся в результате завершённого native создания. Настоящая
загрузка и same-map reload сохраняют однократное пересоздание. Исторический
расширенный mode0 сохраняет прежние ограниченные проверки готовности.

Проверки PASS:

- test_native_npc_sync_mode.py: production installation (ровно один player site),
  отказ при несовпадении каждого native span/ошибке установки, оба режима,
  отсутствие NPC hooks и block ticks, штатный m29 bootstrap ламп.
- test_player_load_once.py: production controller, local/remote reunion,
  временно отсутствующий/неготовый task, одна операция, восемь border walks,
  bounded pending admission; после завершения 2000 кадров/heartbeat дают
  ноль новых запросов native task/actor и ноль повторных созданий.
- test_world_player_render_admission.py: оригинальный FirstSync и полный
  renderer через production Windows trampoline; старый AND воспроизводит
  скрытие, scoped bypass сохраняет отрисовку, обе роли/types и guards.
- test_world_player_lifecycle.py, test_player_map_borders.py (включая negative
  controls), test_member_binding.py — PASS.

Evidence: parent out/coop-dev/runs/player-reunion-regression-20261106/.
Сборка, установка и пользовательское игровое подтверждение записываются
отдельно в run.md/HANDOFF. Баг не закрывать до подтверждения пользователя.
Сейвы, настройки и игровые assets не менялись; HEAD/pin сохранены.
