@echo off
rem Builds the BBSC mod (bbsc.dll + bbsc-launch.exe) on a PC with Visual Studio 2022/2026 (or
rem its Build Tools) - the same compile as build-mod.cmd, without its fixed paths:
rem   - the MSVC environment from vswhere (any edition, any version with the C++ tools)
rem   - clang-cl from Visual Studio's "C++ Clang tools", else from MSYS2 (C:\msys64\clang64\bin)
rem   - output in <repo>\build\mod\, log in <repo>\build\mod-build.log (ends with exit=N)
rem fmt and xbyak come from the emulator's submodules:
rem   git submodule update --init emulator/externals/fmt emulator/externals/xbyak
setlocal
set "SRC=%~dp0"
for %%I in ("%SRC%..\..") do set "REPO=%%~fI"
set "OUT=%REPO%\build\mod"
set "OBJ=%OUT%\obj"
set "LOG=%REPO%\build\mod-build.log"
if not exist "%OBJ%" mkdir "%OBJ%"
echo building > "%LOG%"

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (echo vswhere.exe not found - install Visual Studio Build Tools>> "%LOG%" & goto fail)
for /f "usebackq delims=" %%P in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS=%%P"
if not defined VS (echo no Visual Studio with the C++ tools>> "%LOG%" & goto fail)
call "%VS%\VC\Auxiliary\Build\vcvars64.bat" >nul || (echo vcvars64 failed>> "%LOG%" & goto fail)

set "CLANGCL="
if exist "%VS%\VC\Tools\Llvm\x64\bin\clang-cl.exe" set "CLANGCL=%VS%\VC\Tools\Llvm\x64\bin\clang-cl.exe"
if not defined CLANGCL if exist "C:\msys64\clang64\bin\clang-cl.exe" set "CLANGCL=C:\msys64\clang64\bin\clang-cl.exe"
rem MSYS2's clang.exe in clang-cl mode, for the MSVC target (MSVC's headers, libraries and link.exe)
set "CLMODE="
if not defined CLANGCL if exist "C:\msys64\clang64\bin\clang.exe" (set "CLANGCL=C:\msys64\clang64\bin\clang.exe" & set "CLMODE=--driver-mode=cl --target=x86_64-pc-windows-msvc /clang:--rtlib=platform")
if not defined CLANGCL (echo clang-cl not found: add "C++ Clang tools" to Visual Studio, or install MSYS2 clang64>> "%LOG%" & goto fail)
echo clang-cl: %CLANGCL%>> "%LOG%"

set EXT=%SRC%..\externals
if not exist "%EXT%\fmt\include\fmt\format.h" (echo fmt submodule missing: git submodule update --init emulator/externals/fmt emulator/externals/xbyak>> "%LOG%" & goto fail)
set FLAGS=%CLMODE% /nologo /std:c++latest /O2 /MT /EHsc /W3 /DNOMINMAX /DWIN32_LEAN_AND_MEAN /D_CRT_SECURE_NO_WARNINGS /DBBSC_MOD /DFMT_HEADER_ONLY /I "%SRC%shim" /I "%SRC%..\src" /I "%EXT%\fmt\include" /I "%EXT%\xbyak"
"%CLANGCL%" %FLAGS% /LD "%SRC%bbsc_mod.cpp" "%SRC%bbsc_hooks.cpp" "%SRC%bbsc_relay.cpp" "%SRC%bbsc_channel.cpp" "%SRC%bbsc_register.cpp" "%SRC%bbsc_http.cpp" "%SRC%..\src\core\bbsc_memscan.cpp" "%SRC%..\src\core\bloodborne_re.cpp" /Fo"%OBJ%\\" /Fe"%OUT%\bbsc.dll" /link ws2_32.lib winhttp.lib user32.lib >> "%LOG%" 2>&1 || goto fail
"%CLANGCL%" %FLAGS% "%SRC%bbsc_launch.cpp" /Fo"%OBJ%\\" /Fe"%OUT%\bbsc-launch.exe" /link user32.lib comdlg32.lib /SUBSYSTEM:WINDOWS /ENTRY:wmainCRTStartup >> "%LOG%" 2>&1 || goto fail
copy /y "%SRC%mod.json" "%OUT%\mod.json" >nul
echo exit=0 >> "%LOG%"
echo Built %OUT%\bbsc.dll
exit /b 0
:fail
echo exit=1 >> "%LOG%"
echo Build failed - see %LOG%
exit /b 1
