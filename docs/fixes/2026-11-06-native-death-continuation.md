> SUPERSEDED — повтор23:39 не подтвердил эту гипотезу. Пользователь сообщил,
> что зависание осталось. Обоим native timer15 приходит с foreign=false;
> foreign guard не устраняет случай. Guard и его изолированный тест удалены;
> исходный native dispatch возвращён. Проверка принимавшего foreign callback
> fixture не доказывала причину игрового зависания и не является исправлением.
> Новый разбор: [возврат прежнего handoff](2026-11-06-death-handoff-restore.md).

# Смерть без возрождения: изоляция native продолжений — 06.11.2026

Статус: SOURCE FIX / native regression PASS. Сборка и установка ниже отдельными
статусами. Конкретный чужой пакет в живом прогоне не записан; причинность этого
дефекта именно для зависания23:18 требует игрового повторения. Баг не закрыт.

## Свежий прогон

Логи обоих профилей собраны штатным collect-logs (exit0,4files,warnings0),
parent out/coop-dev/runs/death-respawn-20261106/pc. Актуальные процессы
P2=11164/run231400, P1=21880/run231528; предыдущий224634 сохранён отдельно.
Гость23:18:06.530 входит PartyGhostDeath; хост23:18:54.354 — SoloPlayDeath.
Оба повторяют native-death incomplete каждые15с без финального BBSC death step.
Пользователь: «Вы погибли» появилась, затем лежащий персонаж. Таким образом
показ native текста прошёл; отсутствие последующего _2 — до выбора лампы.
Read-only снимки current Lua managers/списков не нашли активных group4000
продолжений, кроме базового HostDead. Это согласуется с потерей callback,
но не доказывает происхождение удалившего его события.

## Воспроизведённый native дефект и правка

Original CUSA03173 1.09:0139A9D0 принимает локальное и принятое из сети
Lua-событие. Timer15/16 с одинаковыми group4000,delay,clock совпадает с локальной
регистрацией даже при её event+8A=0 (stored template+11=0). Исполняется callback
с foreign-origin context, затем one-shot удаляется. PartyGhostDeath_1 отдельно
отвергает чужой context перед регистрацией следующего шага. Это может лишить
собственный таймер продолжения. Оба peer используют один group4000.

Добавлен один entry guard0139A9D0: только foreign timer15/16,group4000,
coop state3/6 и включённый Spectate возвращает native dispatch count0 до
сопоставления и удаления локальных callbacks. From-network — девятый SysV
аргумент(entry RSP+18), проверен настоящим production trampoline в тесте.
Локальные таймеры исполняются исходным диспетчером. HostDead12, save completion43,
async completion3A, другие группы, solo/disabled неизменны.
Точка вызова/вид события записываются в существующий DEATH timeline.

Не добавлены respawn tick/watchdog/retry, ручной показ текста/очистка эффектов,
обходы акторов, новые сообщения или замена original death functions. Native
таймеры, анимации, финальная очистка и существующий выбор boss/spectate/reload
сохраняются. Штатный local registration mode уже использовался, но receive matcher
его не проверяет; смены одного registration flag недостаточно. Поэтому нужен
узкий entry guard. Стоимость: один O(1) callback на Lua-dispatch; обычный случай
отсеивается по group ID, без обхода списков/чтения сетевой очереди.

## Проверки

- tools/test_native_death_continuation.py: исполняет original0139A9D0 в выделенной
  памяти, библиотеки/VM/allocator подменены изолированными заглушками. Негативный
  контроль: чужой timer забирает локальный callback; после установки НАСТОЯЩЕГО
  emulator/mod/bbsc_hooks.cpp trampoline foreign сохраняет callback, local исполняет
  его ровно один раз. Обе роли, timer15/16, solo, feature off, другие группы,
  HostDead и save/async completions PASS. Игра/сейвы не открываются.
- tools/test_repeat_death.py: rearm three host/guest lives, failures/fences и
  оригинальные native bindings PASS.
- tools/test_hook_resume.py: production trampoline entry skip/mid-resume PASS.

HEAD/pin исходно6e7d32f. Остальные многочисленные dirty-правки сохранены;
в собственный коммит включается только эта правка/её новый тест/этот отчёт.
Сейвы/settings/assets не менялись. Работающие игры не завершались.
