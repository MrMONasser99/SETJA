@echo off
setlocal
set "ROOT=%~dp0"
set "PYEXE=D:\Downloads\env_Setja\setja_stable\Scripts\python.exe"
set "CAPTURE_PY=D:\Downloads\env_Setja\setja_stable\Scripts\python.exe"
start /B "" cmd /c "cd /d "%ROOT%capture\region_selector" && run_selector.cmd"
start /B "" "%ROOT%capture\screen_capture\app\screen_capture.exe"
start /B "" "%PYEXE%" -u "%ROOT%ocr\app\ocr_main.py" 2> "%TEMP%\ocr_error.log"
start /B "" cmd /c "cd /d "%ROOT%translator" && "%PYEXE%" -u -m app.t_main"
start /B "" cmd /c "set PYTHONPATH=%ROOT% && cd /d "%ROOT%txt_viewer" && "%PYEXE%" -u txt_viewer.py"
start /B "" cmd /c "set PYTHONPATH=%ROOT% && cd /d "%ROOT%txt_viewer" && "%PYEXE%" -u instant_overlay.py"
echo [SETJA] Started.
pause >nul
endlocal
