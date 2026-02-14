@echo off
setlocal

set "RS_ROOT=%~dp0"

if not exist "%CAPTURE_PY%" (
    echo [ERR] capture_env not found: %CAPTURE_PY%
    echo Run: capture\setup_capture_env.cmd
    exit /b 1
)

cd /d "%RS_ROOT%"
set "PYTHONPATH=%RS_ROOT%"
"%CAPTURE_PY%" -c "from core.rs_runtime import run_blocking; raise SystemExit(run_blocking())"
