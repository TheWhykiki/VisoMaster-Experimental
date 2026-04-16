@echo off
setlocal EnableDelayedExpansion

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    ".venv\Scripts\python.exe" main_web.py --host 0.0.0.0 --port 8000
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    py -3 --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        echo .venv not found, starting network mode with Windows Python launcher...
        py -3 main_web.py --host 0.0.0.0 --port 8000
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    python --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        echo .venv not found, starting network mode with system Python...
        python main_web.py --host 0.0.0.0 --port 8000
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    where conda >nul 2>&1
    IF ERRORLEVEL 1 (
        echo ERROR: .venv, py and python were not found, and conda is not available either.
        echo Install Python 3 and try again, or use Start_Portable.bat web-network.
        goto :HandleError
    )

    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Install Python 3, create a .venv, or use Start_Portable.bat web-network.
        goto :HandleError
    )
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    python main_web.py --host 0.0.0.0 --port 8000
    set "EXIT_CODE=!ERRORLEVEL!"
) 

:AfterRun
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
