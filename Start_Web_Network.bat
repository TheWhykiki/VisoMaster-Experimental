@echo off
setlocal EnableDelayedExpansion

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    ".venv\Scripts\python.exe" main_web.py --host 0.0.0.0 --port 8000
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Follow the README installation steps first.
        goto :HandleError
    )
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    python main_web.py --host 0.0.0.0 --port 8000
    set "EXIT_CODE=!ERRORLEVEL!"
)

IF NOT "!EXIT_CODE!"=="0" goto :HandleError
endlocal
exit /b 0

:HandleError
if not defined EXIT_CODE set "EXIT_CODE=1"
echo.
echo VisoMaster Network Web Console failed to start or exited with error code !EXIT_CODE!.
echo The console will stay open so you can read the error message above.
pause
endlocal
exit /b %EXIT_CODE%
