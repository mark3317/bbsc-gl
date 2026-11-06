# Игроки на границах соседних локаций — 06.11.2026

## Повтор после установки: SOURCE исправлен; игровой контроль OPEN

Предыдущая правка вошла в общую DLL05:18 и запуски P1/P2 051904/051926.
Пользователь подтверждает FAIL: по разные стороны перехода исчезают модель
и ник. Два живых лога собраны в parent
out/coop-dev/runs/player-map-borders-repeat-20261106/pc (2files,warnings0,
ChangedDuringCopy=true). Роли P1 HOST23f27193 / P2 GUEST89b6f05b.
Первоначальные SOURCE ONLY статусы ниже исторические для предыдущей версии.

В05:25:45.156 P2 пешком меняет Forest→Cathedral, visit8→9, native load7
не меняется. Мод немедленно удаляет remote actor и запускает FirstSync;
P1 повторяет удаление своей копии гостя05:25:45.170. Повторные переходы
05:26:16.661/21.213/23.078/28.844/39.156 дают visit10..14 и такое же
пересоздание на обоих клиентах. Копии снова bind через~0.15..0.24с;
draw_admitted=true не доказывает отображение/прозрачность в живом кадре.
На этих границах НЕ записан вызов mod Disable: прежнее точное ограничение
здесь уже обойдено. Утверждать, что повтор вызван тем же Disable, неверно.

Подтверждены два оставшихся механизма:

- PlayerVisualLife считал каждый border visit настоящей загрузкой и удалял
  исправно созданный actor вместе с его именем. Теперь соседняя смена map
  сохраняет тот же actor при неизменном local native-load generation,
  живом/готовом персонаже и непрерывном here. Настоящие загрузки, same-map
  reload, revival и повторная встреча сохраняют native recreation.
- Native send всё ещё использовал строгий SamePlace. Block packet send
  отбрасывал ВСЕ записи animation3D/status41/HP5/position4 соседнему peer,
  включая собственный PlayerIns. Сейчас смешанный пакет пропускает только
  собственный player handle; NPC handles не получают нового разрешения.
  Native channel34 (018BE2CA..018BE404) передаёт handle и три набора
  draw/display/backread groups; его100байт разрешены соседнему peer только
  для local PlayerIns. Размеры/остальные handles/другая комната/loading/
  несоседние карты продолжают проверяться. Никаких изменений opaque payload.

Это исправления измеренного удаления и доказанного send filter; длительность
пользовательского полного исчезновения не измерена по рендеру. Поздний read-only
live-render.jsonl снят вне точного момента перехода: non-atomic, активация4/4,
disabled0, разные alpha; он не устанавливает причину исходного инцидента.
Новых opacity/draw/death writes нет. Добавлен однократный MODEL лог
`native peer kept across map border` с картами, visit и native load.

PASS:

- test_player_map_borders.py: повторные переходы обоих peers сохраняют actor
  и не удаляют модель/имя; настоящий native load пересоздаёт; отдельные old
  exact-map и old border-recreation negative controls FAIL. Original1.09
  FirstSync+renderer через Windows trampoline обе роли/guards PASS.
- test_player_border_packets.py: реальные production send callbacks/filters,
  обе роли, смешанные player/NPC записи4/5/3D/41, полный channel34, размеры,
  loading/Dream/non-transitive карты; old send policy независимо FAIL.
- test_world_player_lifecycle.py, test_world_blocks.py,
  test_independent_native.py, test_world_presence.py PASS.
- test_native_enemy_states.py с original1.09 ELF: hit target, native state
  receivers через production Windows hooks,27sites/7prologues PASS.
- Полный MOD bloodborne_re.cpp -fsyntax-only exit0;
  build/player-map-borders-repeat-syntax.log.

Новая DLL не собрана/не установлена: игры37636/24204 продолжают работать.
Сейвы/настройки/assets/HEAD/pin не менялись, commit/push не выполнялись.
Нужен повтор игрового сценария после согласованной сборки и установки.

## Первая правка (установлена05:18, пользовательский FAIL выше)

Статус: исходники исправлены, целевые проверки и MOD syntax PASS.
DLL не собрана и не установлена; игровой контроль OPEN. Два клиента
bb-probe (17376/30784, запуск 04:37:14) оставлены работать.

Пользователь сообщает, что охотники по разные стороны перехода между
Соборным округом и Запретным лесом не видят друг друга. Подтверждённый
механизм в исходниках: TickBbscWorldPlayers использовал SamePlace с точным
номером карты и явно вызывал native Disable(1) для другого номера карты.
Та же проверка блокировала допуск рендера при пересоздании и допуск member
task. Это достаточно для скрытия исправно созданного персонажа. Снимка
рендера непосредственно во время пользовательского случая нет; наличие
дополнительного штатного ограничения в живом прогоне не исключено.

Добавлен отдельный SamePlayerSpace: одинаковое место либо непосредственная
пара соседних карт из оригинальных MSB 1.09 ConnectCollision. Все 14 пар
сверены с оригинальными файлами только чтением. Учитываются area/block
target bytes; FF block у m23/m28 разрешается в обычный block 00. Связь
симметрична и не транзитивна. Обычный Сон m21_00 не соединяется с картами
через неиспользуемый m21_01. Загрузки, другая комната и разные/неизвестные
ритуалы чаш остаются разделены.

Новая проверка применяется только к скрытию/включению игроков, жизненному
циклу, native FirstSync render admission и member-task admission. SamePlace,
владение врагами/событиями, маршрутизация каналов и лампы не изменены.
Не добавлены записи opacity, draw-node или death; существующий штатный
рендер продолжает обрабатывать геометрию и дистанцию. Смена visit по-прежнему
вызывает однократное native удаление/FirstSync, включая переход пешком.

Проверки:

- tools/test_player_map_borders.py: сверка 14 пар с MSB; production controller
  держит/включает/прикрепляет игрока Cathedral/Forest, не повторяет создание
  каждый кадр, пересоздаёт один раз при новой visit; скрывает Dream/loading.
  Все пары симметричны; NPC channel31 не получает новое разрешение.
  Старое правило точной карты независимо проваливает новый сценарий.
- Тот же тест выполняет оригинальные 1.09 FirstSync и полный native renderer
  через production Windows trampoline между Cathedral/Forest: обе роли,
  types1/2/12, одноразовость, timeout/visit/world/loading/dead/self/leave guards.
- test_world_player_lifecycle.py, test_world_presence.py,
  test_independent_native.py PASS; прежние сценарии респавна и изоляции сохранены.
- Полный bloodborne_re.cpp, BBSC_MOD, clang++ -fsyntax-only exit0;
  build/player-map-borders-syntax.log. Это не сборка DLL.

Игровой сценарий после согласованной сборки/установки: оба направления
Cathedral/Forest, один охотник с каждой стороны у двери; затем оба проходят
границу туда/обратно. Проверить модель, движение/анимации, имена и отсутствие
дубликатов. Затем один уходит в Сон/чашу — его копия должна исчезнуть.
Сетевые пакеты/реальный результат этого сценария ещё не измерены.

HEAD и pin 4989896 без изменений. Чужие локальные изменения сохранены;
коммит, push, правки сейвов/настроек/игровых файлов не выполнялись.
