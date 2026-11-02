# Порядок кооп-событий — 02.11.2026

## Принятые правила

Выход в меню сразу забирает управление и сохраняет намерение выйти. Гость после
Continue появляется в своём мире на позиции до подключения. Уход хоста возвращает
гостей в собственный мир. Фонарь хоста перемещает всех гостей, включая переходы
в чаши/из чаш. Вне боя с боссом погибший возрождается сразу; в бою с боссом погибшие
наблюдают за живыми до завершения боя или общего поражения. Существующие PvP-правила
сохранены; они не приравниваются к кооперативному наблюдению.

## Изменённый порядок

1. Native spawn-resolution (0x01938F65) регистрирует загрузку мира, включая Continue.
   На первом игровом tick после loading=0 и появления local character сигнал
   потребляется один раз. Старый сигнал перед title очищается, другой global
   отбрасывается. Multiplayer ReloadFinish продолжает работать для summon/reinsert.
2. Новый собственный персонаж снимает committed quit guard до session recovery.
   Восстанавливаются принадлежащие quit блокировки в совпадающем контексте.
   State0 сам по себе не является достаточным подтверждением Continue.
3. Выход: подтверждение -> закрытие меню вне стека команды -> native save completion
   -> журналы и уведомление peers -> Stop -> немедленная native RemoteCleanup
   -> ожидание state0/failed terminal -> OnReturnTitle. Engine cleanup не выполняется
   из save-result callback. По истечении5 s только диагностируется задержка;
   запрос выхода остаётся, 30-секундной отмены после принятого Stop больше нет.
4. Тот же Stop->RemoteCleanup применяется при подтверждённом завершении сессии
   партнёром. Native StageTransition подтверждает пару вызовов
   0x013CDEF6(Stop) ->0x013CDF17(RemoteCleanup). Раньше наша очистка откладывалась
   до state0. Это устранённое несоответствие; сокращение реального Stop до нескольких
   секунд требует следующего прогона, точная timed native подстадия не измерена.
5. Guest state0 в чужом мире без активной загрузки возвращается домой после1 s
   стабильного состояния вместо15 s. При активном quit этот путь запрещён:
   меню и отправка домой больше не конкурируют. Native начавшийся load имеет приоритет.
6. Placement-ready запрашивает открытие cover; guest inventory-ready текущей
   generation разрешает его. Ранний запрос хранится до успешной проверки ledger.
   Сигналы ещё незавершённой загрузки запрещают открытие. Сохраняются bounded
   time-limit и отмена при завершении сессии. Сама выдача предметов остаётся после
   native inventory reset; её не перенесли в ранний map callback.
7. Cleanup-complete и watchdog больше не сообщают об успешном снятии блокировок
   при активном quit, когда release helpers обязаны отказать.
8. Служебный TickBbscItemLedger ограничен10 Hz, смена load generation немедленно
   обходит ограничение. Сохранены интервалы реального пересчёта/записи1–2 s.
   FinishBbscLedgerContext остаётся до ограничителя: завершение award context нельзя
   откладывать. В quit исключены безусловные повторные записи уже установленных locks.

## Матрица порядка (новые и сохранённые пути)

| Сценарий | До загрузки/разрыва | После готовности | Владелец решения |
|---|---|---|---|
| Host создаёт комнату | native create; размещение и описание мира | публикация world/life; native insert guests | Host/native matching |
| Guest обычный join | сохранить origin/свой мир/ключи; placement до stage descriptor | host flags, type/reinsert, ledger readiness, fade | Native join + BBSC placement |
| Cross-map join | connect-first, затем native handoff destination | существующий второй reload для освещения, окончательный reconcile | Один load cover на оба reload |
| Guest подключается в чашу | проверить scope/revision, native mount/injection до stage | тип гостя, мир чаши хоста, inventory/placement readiness | Chalice transition guard |
| Повторный/поздний claim | state4 сохраняет pending; state6 retire sign | поздний create повторно retire; новый session не смешивать | HTTP lifecycle mutex |
| Неуспешное подключение | native failure, отмена устаревшего placement | home cleanup, release cover/locks | Native terminal state |
| Host фонарь | опубликовать destination/revision, сохранить текущие журналы | гости follow, native reinsert, готовность load | Host destination authority |
| Guest идёт вслед в/из чаши | валидировать mount/revision до перехода | одинаковый map-id не подменяет dungeon identity | Chalice scope + follow |
| Гость выходит в меню | own-origin serializer, save, Stop+cleanup | напрямую title; Continue собственный origin | Quit intent приоритетнее home fallback |
| Host выходит в меню | save/notify/Stop+cleanup | host title; гости home | Каждый локальный game thread |
| Выход в меню из чаши | та же save/Stop последовательность, origin принадлежит guest slot | title без лишнего захода в Сон; Continue в своём мире | Общий quit, существующий home serializer |
| Guest Blank | native leave; отмена удержания сессии | свой мир, restore quests/items, unlock | Native leave + guarded fallback |
| Host Blank/kick | native kick; host остаётся в своём мире | гости home; host room timeout и локальная очистка | Native host flow |
| Подтверждённый уход host | остановка сессии, cleanup remotes | guest home, кроме собственного committed quit | SessionExit |
| Уход одного из нескольких гостей | убрать ушедшего, сохранить живую комнату | остальные продолжают играть | Peer life count/native members |
| Смерть вне boss | снимок смерти/однократная потеря echoes | немедленное существующее revive/restock | Общая death state machine |
| Смерть в boss, живые остались | boss-at-death latch, snapshot | spectate; живые продолжают | Общая death state machine |
| Все погибли в boss | host death reload, guest wipe notification; penalty до stage snapshot | revive/restock один раз, release death locks/camera | Host reload + guest follow |
| Boss погиб при мёртвом игроке | учесть rewards отдельно от death snapshot | recovery без повторной потери заработанного после смерти | Boss context + death journal |
| Поздний death callback после revive | живой персонаж + предыдущий death window | не запускать повторный stain/reload | Existing late-death guard |
| Session ended во время death/load | прекратить удержание/reinsert; native load не дублировать | собственный мир, role/death cleanup | PostLoadRecovery + SessionExit |
| Повторное подключение после Continue | сбросить прежний quit только по готовности нового мира | новая сессия работает без старых блокировок | Load observer перед SessionExit |

## Что должно оставаться до/после загрузки

До: origin/слот, снимок собственной истории, проверка назначения и чаши, death
snapshot/penalty, отмена конкурирующего transition, подготовка world flags там,
где последующие map events читают их при инициализации. Нельзя переносить эти шаги
в периодический post-load tick.
После: подтверждение создания персонажа и loading=0; восстановление session role,
reinsert/revive, inventory reconciliation после native reset, release locks и cover.
Own-world quest commit выполняется только после reconciliation и подтверждённого
native save; журнал не удаляется при незавершённом save. Сетевые callbacks не должны
вызывать native stage/cleanup прямо со своего потока; существующая очередь game-thread
работы сохранена. Save-result callback лишь публикует результат.

## Проверки и границы

Production fixtures: menu quit (Stop->cleanup, позднее completion после30 s,
пропуск tick в Continue, другой global, exactly-once generation), inventory barrier
(старое поколение, loading, pending callback, timeout, session end), chalice scope,
follow arrival, home origin serializer, native trampoline и post-load recovery
включая alive/dead wipe и единственного владельца восстановления — PASS.
Устаревший chalice fixture получил отсутствовавшую заглушку существующего
NotifyBbscHostDeathReload; алгоритм чаш ради этого не менялся.

Это аудит перечисленных путей текущего кода, не доказательство всех возможных
межпоточных перестановок. Real-network latency, падение процесса между save/Stop,
повторные native callbacks и3+ игрока требуют игрового контроля. Нет гарантии
измеренного быстрого Stop до прогона. Вторая lighting загрузка сохранена.
HTTP connect timeouts отдельны; транспорт этим изменением не переписывается.

## Установка

02.11.2026 01:43 МСК: DLL build exit=0; mod delta1767a8d установлен
на обе остановленные машины, по5 файлов. Бэкапы lifecycle-order-20261102-014341
(ПК) и lifecycle-order-20261102-014343 (ноут). Игровое подтверждение pending.
Компилятор сообщил о двух оставшихся неиспользуемых старых таймерах
(BbscStrandedMs/bbsc_confirmed_departure_ms); ошибок сборки нет.
