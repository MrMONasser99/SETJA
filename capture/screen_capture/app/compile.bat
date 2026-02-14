@echo off
setlocal

cl /std:c++17 /EHsc ^
  /Fo"obj\\" ^
  app\sc_main.cpp ^
  core\capture\sc_capture.cpp ^
  core\region\sc_region.cpp ^
  core\shm\sc_shm.cpp ^
  user32.lib d3d11.lib dxgi.lib ^
  /Fe:"app\screen_capture.exe"

IF ERRORLEVEL 1 (
  echo.
  echo Build FAILED.
  pause
  exit /b 1
)

echo.
echo Build SUCCESS.
pause
