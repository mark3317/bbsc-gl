# Устранение блокировок игрового потока — 03.11.2026

Обновление по игровому прогону17:16–17:24: исправления вошли в реальную сборку.
Асинхронные bell grants438/672/422мс не остановили кадр на время запроса;
cleanup/retry позволили подключения. Остаточный gameplay FPS47.6–55.2 и
post-load статтер358мс остаются открытыми. Подробности в parent
`docs/fixes/2026-11-03-pacing-run-1716.md`. Исторические source-only статусы
ниже описывают момент разработки, а не текущую установленную сборку.


По просьбе пользователя после анализа прогона 16:23–16:27 исправлены конкретные
блокирующие пути и повторные проверки памяти. Это изменения исходников с
целевыми исполняемыми проверками. Продуктовые DLL/EXE не собирались и не
устанавливались; игра не запускалась. Стабильные 60 FPS и устранение наблюдённых
статтеров в игре пока не подтверждены.

## Разрешение Зовущего колокола

Ранее native item hook синхронно вызывал WinHTTP `/party/acquire`, допуская
ожидание на игровом потоке; в прогоне callback занял 474.9 мс при кадре 505.6 мс.
Теперь hook только ставит запрос в атомарный mailbox и возвращается до эффектов
и расходования ресурсов. Существующий maintenance worker получает unanimous
подтверждение, после чего игровой tick один раз вызывает проверенный NativeApply.
Это тот же entry, который уже используется для seamless responder resume.

Проверяются actor/global/map, native session state, здоровье, loading/title/quit,
поколение завершённой загрузки и pending native load finish. Повторная загрузка
той же карты с теми же адресами не сохраняет разрешение. Срок отложенного действия
12 секунд; истечение отменяет попытку, не разрешает предмет. После отказа native
применения отмена передаётся party engine. Визуальная анимация и реакция native
item UI на отложенный запуск требуют игрового подтверждения.

Generation/result обновляются одним CAS: ответ старого запроса не может оживить
отменённую попытку. NativeApply и вложенный GoodsExecutor используют одно разрешение
только на текущем стеке вызова; обычные повторные callbacks не создают второе
действие. Контекст pending item защищён try-lock без ожидания; вложенный native
вызов использует thread-local replay guard. Никакого cached can_beckon в качестве
подтверждения роли не используется. Offline/legacy путь не ставит запросов.

## Очистка старых знаков

`ClearStaleRecord` больше не вызывается из `SendCleanSummonCreate`. Он выполняется
только maintenance worker, с отпущенным summon_lifecycle_mutex. In-flight fence
не допускает публикацию поверх незавершённого delete. Игровой wrapper использует
try-lock и существующий HTTP timeout/retry результат, пока cleanup не завершён;
первая публикация может ждать следующего native refresh вместо ожидания сети
в кадре. Native polling/игровое подключение после такой отсрочки ещё нужно проверить.

Версия lifecycle не позволяет старому успешному delete объявить чистым новое
состояние после перехода сессии или запоздалого create response. Ошибка delete
сохраняет двухсекундный backoff. Полный порядок delete-before-create и retirement
знака вошедшего гостя сохранён. Ни таймаут, ни lock contention не разрешают обход
очистки. Сетевое ожидание штатного original_send этим изменением не отменяется.

## Диагностика native порта

В родительском BBGL `p2p_transport` снимает числовые counters, stream state и
ограниченный batch samples под transport mutex. Форматирование полного отчёта
и вывод выполняются после unlock. Бюджет/хэши/порядок samples, cumulative counters
и packet delivery сохраняются.

Pacing report теперь копирует окно в очередь фиксированного размера и форматируется
и печатается фоновым writer. Legacy `Perf window`/`Perf stall` тоже не ждут stdout:
это предотвращает ожидание его CRT lock при одновременной печати pacing report.
При заполнении очереди теряется диагностическая запись, а не кадр; следующие
отчёты содержат report_async=1/reports_dropped. Pacing `previous_report_ms` теперь
измеряет захват/постановку прошлого отчёта, а не фоновую печать. Writer учитывается
в process CPU; его CPU нельзя приписывать PresentThread. При штатном уничтожении
очереди накопленные записи допечатываются. Лимитер, vblank deadlines и gameplay
tick frequency не изменены.

## Постоянная работа с памятью

В DLL `QueryProtection` уже проверяет MEM_COMMIT и возвращает границы и права
региона с учётом GUARD/NOACCESS. `HasMemoryAccess` использует этот результат без
повторного обхода того же региона через IsValidMapping. Overflow, полное вхождение
span и требуемые права проверяются как раньше. В emulator build отдельный
IsValidMapping сохранён: его контракт отличается от Windows shim.

`GetCurrentPackedMap` читает поля двух уже проверенных живых структур без повторной
проверки каждого поля: 4 проверки вместо 8. Значение карты/указатели не кешируются
между вызовами; память и права не становятся долгоживущими разрешениями. Эффект
особенно относится к NpcPass, где карта проверяется сотни раз за кадр. Снижение
числа запросов подтверждено, процент прироста FPS ещё не измерен. Новые ограничения
prep workers/CPU affinity и пропуск игровых tick не вводились.

## Проверки

- `tools/test_party_item_async.py`: production deferred gate/mailbox, once-only
  replay/nested entry, denied/late/cancelled generations, 11 lifetime fences,
  blocked worker, конкурентные native callbacks — PASS.
- `party/test_native_gate.py`: production dispatch + реальный Windows trampoline,
  deny до synthetic effects и allow после grant, unaffected guest bell — PASS.
- Три выбранных `BridgeTests` из `party/test_winhttp_bridge.py`: реальный production
  WinHTTP bridge, process fence, unanimous title wait, заблокированный HTTP и
  отмена с отбрасыванием позднего grant — PASS. Полный inherited suite не запускался.
- `tools/test_summon_cleanup.py`: production lifecycle, retry/backoff/slow join,
  немедленный возврат wrapper при заблокированном delete, unlocked I/O, late
  response/new generation и delete-before-create — PASS.
- `tools/test_memory_hotpath.py`: оба build-контракта, права/границы/overflow,
  семантическое сравнение map reader с замороженной старой реализацией, повторное
  использование адресов и 8→4 lookup — PASS.
- `tools/test_hook_resume.py`, `tools/test_death_hotpaths.py`,
  `tools/test_cainhurst_reveal.py`, `tools/test_join_teleport.py`,
  `tools/test_perf_policy.py` — PASS. Последний учитывает фактическую политику
  installer functional OR essential: StopRequest наблюдается через essential site.
- Parent `tests/test_async_pacing.py`: blocked sink, bounded backpressure, flush,
  независимость snapshot от reset, формат pacing/legacy — PASS;
  четыре `test_pacing_summary.py` — PASS.
- Parent `tests/test_p2p_diagnostic_snapshot.py` компилирует текущий transport.cpp,
  а не старый объект архива: 540 реальных UDP доставок, framing/readiness/peek,
  crossing diagnostic flush — PASS. Worst round trip около 32.5 мс в этом
  harness с обычной системной дискретностью Sleep; это не игровая LAN latency.
  Начальный timeout harness 15s был недостаточен при округлении Sleep; с 30s
  прогон завершён. `test_coop_latency_diagnostics.py` — PASS.
- Full driver.cpp syntax с настроенными native flags — PASS. Полные изменённые
  module TU проверены clang-cl /Zs с MSVC headers. GNU/libc++ проверка нашла
  прежний несовместимый ifstream(wstring), поэтому она не подменяет MSVC проверку.

Сейвы, настройки, game files, VPS и установленная сборка не менялись. Общая
загрузка CPU при трёх играх остаётся отдельным ограничением: для остаточного
недобора нужен matched single-vs-three CPU/GPU benchmark после общей сборки.
