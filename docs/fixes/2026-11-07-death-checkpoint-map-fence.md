# 07.11.2026 — общая лампа смерти только на карте умершего

SOURCE FIX / targeted tests PASS / DLL NOT BUILT / gameplay OPEN.

Пользователь после разбора вылета П1 уточнил: сохранить ограничение возрождения
своей картой. Прочитаны чаты «Разобрать последний лог падения хоста»,
«Исправить возрождение у последней лампы» и «Исправить выбор лампы возрождения».
Прежнее решение запрещало соседний coordinate warp, но специально допускало
полную загрузку на другую карту. Новое указание отменяет этот cross-map override
общей лампой. Сравнение даты зажигания/личной поездки внутри своей карты сохранено.

## Доказательства и границы

run004519: П1 выбрал native2412951 в Центральном Ярнаме00:52:39.504.
П2 зажёг общую2302950 Старого Ярнама00:53:36.043; смерть П1 —00:53:52.527.
RequestBbscSharedLampReload игнорировал возвращаемый `here=false`:
00:53:55.133 BeginBbscSharedLampLoad вызвал original013CDF30(2302950),
который выбрал другую карту. После arrival00:54:00.348 П1 упал в DLRegularHeap
free0x208599f: next-block pointer0x20 из заголовка блока, чтение0x28.
Это доказанный неправильный выбор карты; первое повреждение блока не снято.

Дополнительный read-only original ELF разбор стека: выше heap wrapper29297ba
деструктор2A4B230 освобождает graphics-resource allocation через11E6B00;
стек черезC77256/C82CD7/C0BDCF/BFE3C2 относится к Yebis GPURenderGlare
UninitializeDevice (строки original game), затем ppfx Initialize.
Это место обнаружения повреждения при пересоздании графических ресурсов,
не доказательство конкретного writer, двойного освобождения или виновности ИИ.
Снятие cross-map death override исключает показанный ошибочный переход,
но не считается доказательством устранения любого heap fault в игре.
Логи и disassembly: parent out/coop-dev/runs/p1-death-loading-crash-20261107/.

## Изменение

- ReadBbscSharedLampCheckpoint отклоняет checkpoint другой текущей map/scope
  до передачи point вызывающему коду. Общая лампа больше не скрывает штатную
  личную точку на своей карте. Для m29 нужны прежние key+ritual.
- BeginBbscSharedLampLoad проверяет scope и текущую карту до snapshot/mount,
  записи checkpoint, уведомления хоста и native point load.
- Уже ожидающая цель в прежнем TickBbscSharedLampCheckpoint перепроверяется
  перед применением: при смене карты/ритуала отменяется и остаётся штатный
  reload без shared override. Новая общая лампа не перенаправляет эту смерть.
- Штатный Snatcher prison transition, обычные поездки и приоритет лампы
  побеждённого босса не менялись. Личный native death fallback не переписан.

Нет новых hooks, ticks, опросов, таймеров, повторов, очередей или пакетов.
На существующих death boundaries — сравнение scope/map; Begin использует
один прежний presence mutex для чтения локального scope. Новых actor/heap
обходов нет. Дополнительных фоновых расходов и per-frame работ в idle нет.

## Проверки

- test_shared_lamp_checkpoint.py PASS: П1 Central2412951 + более поздняя
  P2 Old2302950 для хоста/обоих гостей; личная лампа остаётся доступной,
  нет shared death load/подготовки чужого scope/перезаписи personal checkpoint.
  Frozen target scope change, другая ritual generation, same-map load,
  прежние date/order/replay/ack и scoped readiness проверки PASS.
- BBSC_TEST_DEATH_MAP_OLD=1: удаление scope admission из production reader
  ожидаемо ломает regression. Не подменяет native allocator test.
- BBSC_TEST_EBOOT=../../out/exit-study.elf: original013CDF30 выполняется
  на выделенной памяти для same-map shared destination, PASS.
- test_boss_lamp_respawn.py:19 original boss destinations/guards PASS.
- test_independent_death_destination.py: death controller/abduction PASS.
- Full MOD translation-unit C++ syntax exit0.

Сборку/установку не запускали: параллельный чат «Проверь ИИ противников в логах»
изменяет связанную native AI логику; общий build barrier не пройден. Это не
игровое подтверждение исправления вылета. Реальные сейвы/settings не менялись.
