@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ---- Find ROOT by walking up until we find "\capture\" ----
set "ROOT=%~dp0"
:UP
if exist "%ROOT%capture\" goto FOUND
if "%ROOT%"=="%ROOT:~0,3%" goto NOTFOUND
for %%I in ("%ROOT%..") do set "ROOT=%%~fI\"
goto UP

:NOTFOUND
echo [ERR] Could not locate project ROOT (folder 'capture' not found upward from: %~dp0)
pause
exit /b 1

:FOUND
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "REGION_CMD=%ROOT%\capture\region_selector\run_selector.cmd"
set "SCREEN_EXE=%ROOT%\capture\screen_capture\app\screen_capture.exe"

if not exist "%REGION_CMD%" (
  echo [ERR] region selector not found: "%REGION_CMD%"
  pause
  exit /b 1
)
if not exist "%SCREEN_EXE%" (
  echo [ERR] screen_capture not found: "%SCREEN_EXE%"
  pause
  exit /b 1
)

REM ---- Run BOTH in background (no extra console windows) ----
pushd "%ROOT%\capture\region_selector"
start "" /b cmd /c run_selector.cmd
popd

pushd "%ROOT%\capture\screen_capture\app"
start "" /b "%SCREEN_EXE%"
popd

exit /b 0
