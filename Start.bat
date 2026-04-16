@echo off
setlocal EnableDelayedExpansion

REM Prefer the local virtual environment because it is the least error-prone startup path.
IF EXIST ".venv\Scripts\python.exe" (
    echo Found .venv, launching with local Python...
    ".venv\Scripts\python.exe" main.py
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Run Start_Portable.bat or follow the README installation steps first.
        goto :HandleError
    )
    echo Running VisoMaster...
    python main.py
    set "EXIT_CODE=!ERRORLEVEL!"
)

IF NOT "!EXIT_CODE!"=="0" goto :HandleError
endlocal
exit /b 0

:HandleError
if not defined EXIT_CODE set "EXIT_CODE=1"
echo.
echo VisoMaster failed to start or exited with error code !EXIT_CODE!.
echo The console will stay open so you can read the error message above.
pause
endlocal
exit /b %EXIT_CODE%
