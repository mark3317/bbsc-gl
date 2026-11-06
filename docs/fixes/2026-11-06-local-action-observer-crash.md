# Вылет обоих клиентов после общей сборки — 06.11.2026

Первый запуск новой DLL: P2 run051406, P1 run051440. Оба exit3, одинаковый
Fault read00000008095f0d52 at guest offset5ee6948, return203f111.
Полные логи в parent out/coop-dev/runs/latest-fixes-2p-20261106/pc (2files,warnings0).
Windows Application/System за интервал сохранены рядом отдельно; найденные
WER blocks.exe от05:07 — ожидаемые негативные fixtures, не игра.

Причина доказана адресами: новый observer принятого ObjAct стоял в01CD97D6
на RIP-relative `mov rcx,[rip+0370A403]`. DLL hook копирует инструкции без
relocation, в отличие от emulator hook, который отклоняет такие инструкции.
В trampoline по5ee6948 получился адрес5ee6948+7+370a403=95f0d52, в точности
из обоих Fault. Исходный адрес —1cd97d6+7+370a403=53e3be0 (stack cookie).
Функция вызывается и вне независимого коопа/дверей, поэтому упали оба во Сне.
Нет оснований относить этот сбой к GPU или новому reset/боевой трассировке.

Observer перенесён на01CD97E6, уже после native stack-cookie проверки,
до восстановления R12: пять полных байтов `add rsp,58; pop rbx`. AL и R12
по-прежнему содержат native результат и ID действия; скопированные инструкции
не зависят от адреса. Требования дверей/локальный accepted-action guard прежние.

Проверка test_guest_transition_doors теперь выполняет реальную native функцию
и epilogue ИМЕННО с установленным production DLL trampoline bbsc_hooks.cpp,
вместо прежнего исполнения только нетронутой функции. Все роли0..8,
пять action IDs, accepted/rejected AL, сохранение R12 и стека PASS.
test_transition_door_authority: обе оригинальные двери/все шаги/local-only/
wrong-exit/stale-load PASS. Старый тест не покрывал установленный observer;
его прежний PASS не подтверждал безопасность этого перехвата.

Исправление пересобрано (exit0,8 warnings), delta установлена exit0, inputs metadata
неизменны. Backup D:/Games/Bloodborne/coop-dev/backups/action-observer-fixed-2p-20261106-20261106-051846.
Player1/Player2 последовательно запущены: native37636/24204, новые логи051904/051926,
35/35 hooks и enemies/travel=true оба. P1 дошёл до Сна без прежнего Fault.
Игровые кейсы последних изменений остаются OPEN.
