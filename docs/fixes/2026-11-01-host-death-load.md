## Подтверждение пользователя — 01.11.2026

- T22: задержка урона в чашах не повторялась; считать решённой.
- T23: зависание при возврате из чаши в Сон решено.
- T24: камера наблюдателя после возрождения решена.
- T25 / ключи и инструменты: в целом решено; не все случаи проверены.
  Остаток — покрытие редких сценариев, а не подтверждённая текущая потеря предметов.
- Нестабильный вылет хоста пользователь относит к GPU-проблемам этого ПК:
  на других устройствах не воспроизводится. По просьбе пользователя расследование
  отложено; не считать текущим блокером мода и не назначать повтор для его диагностики.
  Точная техническая причина не установлена; прежние логи сохранены как история.

Это подтверждение заменяет более ранние pending/открытые статусы ниже.

> **Статус 01.11.2026:** Текущий результат: logging fix bbaae0f уже собран и установлен на ПК/ноут (последний раздел). Сам вылет хоста не локализован и не закрыт. Раннее not yet rebuilt/deployed ниже — промежуточное состояние.

# Host exits during boss-wipe reload — 01.11.2026

Build: bundled BBSC-GL d467c4f, BBGL e962847. User confirms host died during
the boss fight and crashed while respawning. Both logs copied to
`D:/Games/Bloodborne/coop-dev/runs/20261101-post-boss-crash-0149`.
Active runtime profile is `%LOCALAPPDATA%/Bloodborne Game Launcher`, not the
older `%LOCALAPPDATA%/bbgl` still selected by the collection helper.

## Observations

- Host 01:47:37.749: publishes dead. 01:47:46.542: final death step enters spectate.
- Host 01:48:06.057: guest publishes dead. 01:48:07.568: spectator hold releases
  and native death reload returns 1.
- Host 01:48:10.139: publishes alive, then mod log ends without completed-load
  confirmation. This alone does not prove a successful respawn.
- Guest 01:48:12.439: confirmed host departure; cleanup, home reload and
  world/item reconciliation complete. In this run the guest had not yet reached
  its final spectate state before the host disappeared.
- No new matching Application crash/hang report, System GPU reset/WHEA event,
  or Windows crash dump found for this run. Native fatal_exception terminates
  with code 3 after printing to stderr, so lack of a WER entry is not exculpatory.
- Host last_run.log stops at 01:40:26 (launcher closes just after game entry),
  guest last_run.log also stops at startup. No fault address or stack is retained.

## Confirmed regression and correction

The close-after-launch callback kept the process/pipe reader alive only when
hosting local servers. Public-server hosts, guests and offline players closed
the parent and its daemon log reader together with the window. Corrected in
BBGL launcher/bbport_launcher_qml.py: every running game now keeps the event
loop and reader alive without a window, then gameFinished quits the launcher.

A real offscreen Qt event-loop check passes for local hosting and guest/offline:
window closes, a simulated late fatal report is written through production
_read_output into last_run.log, then game exit terminates the event loop.

The native crash cause remains undetermined; do not label it a GPU crash or
a proven camera-hook crash. Code correction is not yet rebuilt or deployed.
Next reproduction must use the corrected launcher to retain the native fault
address/stack and exit code. No saves changed, no gameplay started.

## Logging fix deployed

BBGL `bbaae0f` rebuilt and installed on both PC and laptop (01.11.2026).
Launcher SHA256 on both: `D0DFC857650F1A03026B729A8A91EA626E3EBFBDF92A80BC7FD06E60DE002EBE`.
Mod is unchanged (`d467c4f`, DLL SHA256
`6C09C61B1B56BA779EF99ECD0ABAD66BB51FEAA2A28E0AB605DA058DBF4A32C4`).
Release verification PASS. Actual frozen launcher on each machine passed an
offscreen Qt lifecycle check for local hosting and guest/offline play: window
closes, delayed simulated fatal output reaches production last_run.log, then
gameFinished exits the background process. Fixtures use temporary log folders,
not player logs/saves. Backups on each machine: `coop-dev/backups/before-log-reader-fix`.
No gameplay launched; crash reproduction and exact native fault still pending.
