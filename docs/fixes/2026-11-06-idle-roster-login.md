# Вход в сеть на ПК: отсутствующий участник старого idle roster

06.11.2026: исправлено и установлено на ПК; повторный запуск и live NP login подтверждены.
Первый LAN прогон после forest-host: run_20261106_063240.log06:33:10
Login rejected32 / ConnectUser authentication failed. Дополнительный запуск
run_20261106_063936.log06:39:45 воспроизвёл отказ. Существующая Party diagnostics
показала np_reject command0 с KeyError идентификатора бывшего участника.
Пароли/токены не выводились.

Dynamic journal основного профиля хранит home.owner=None и roster из local+
исторического peer. Discovery штатно удаляет отсутствующего idle peer из
members/native_names, однако durable roster остаётся. Compatibility.np_command0
безусловно индексировал native_names[p] для каждого roster item: исключение
отклоняло корректную локальную авторизацию с wire status0x20 (32).
Это ошибка списка друзей в ответе входа, а не повреждение сейва/неверный пароль.

Исправление: login friends включает только roster peers с доступной native
identity. Локальный account, проверка NP имени/пароля, остальная авторизация,
члены мира и durable journal не меняются. Отсутствующему peer не придумывается
имя, вход не переписывает membership. Обычные известные друзья сохраняются.

Проверки из party:

- python -B -m unittest test_dynamic.DynamicTests.test_native_login_with_expired_idle_roster_peer test_compat.CompatibilityTests.test_delayed_login_cannot_replace_newer_authenticated_socket:2PASS.
- Новый тест создаёт production DynamicEngine A/B/C в изолированных каталогах,
  истекает B при idle roster A/B/C, посылает реальный protobuf LoginRequest
  через сокет Compatibility и проверяет success/accountA/friendC/неизменную
  membership. Старый unguarded login в отдельном negative control отклоняет
  тот же запрос: ожидаемый FAIL подтверждён.

После сообщения пользователя «закрыд» отсутствие игровых процессов проверено.
На ПК заменён только coop/party/compat.py; сборка DLL не нужна.
Backup D:/Games/Bloodborne/coop-dev/backups/rom-login-roster-20261106-064202.
Повторный запуск primary profile06:42:02, helper14988, diagnostics включена
transient для подтверждения успешного NP входа. Сейвы/settings/identity/journal
не сбрасывались, forest-host повторно не накатывался, one-hit ON сохранён.
Ноутбук не перезапускался, эта Python-правка на него в этом запросе не ставилась.
Evidence parent out/coop-dev/runs/rom-pc-laptop-20261106: pc-login-fixed logs,
login-fix.json и основной профиль Party events. Gameplay Rom остаётся OPEN.

Live результат: native1456 старт06:42:23, run_20261106_064223.log35/35hooks;
06:42:31 успешные NP replies0(login),39(token),12(features), затем100(context)
и111(world list). Reject/auth failure в этом запуске нет.06:42:47 загружен
Forbidden Woods; подключение к ноутбуку и кейсы Ром этим ещё не подтверждены.
