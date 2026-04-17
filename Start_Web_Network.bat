@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "EXIT_CODE=0"
set "CONDA_BAT="

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    ".venv\Scripts\python.exe" main_web.py --host 0.0.0.0 --port 8000
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    call :FindCondaBat
    IF DEFINED CONDA_BAT (
        echo .venv not found, trying conda environment "visomaster"...
        call "%CONDA_BAT%" activate visomaster
        IF NOT ERRORLEVEL 1 (
            echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
            python main_web.py --host 0.0.0.0 --port 8000
            set "EXIT_CODE=!ERRORLEVEL!"
            goto :AfterRun
        )
        echo WARNING: Conda was found, but the environment "visomaster" could not be activated.
    )

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

    echo ERROR: No usable Python runtime was found for the network web console.
    echo Install Python 3, create a .venv, or use Start_Portable.bat web-network.
    set "EXIT_CODE=1"
    goto :HandleError
)

:AfterRun
IF NOT "!EXIT_CODE!"=="0" goto :HandleError
endlocal
exit /b 0

:HandleError
echo.
echo VisoMaster Network Web Console failed to start or exited with error code !EXIT_CODE!.
echo The console will stay open so you can read the error message above.
pause
endlocal
exit /b %EXIT_CODE%

:FindCondaBat
for %%I in (
    "%USERPROFILE%\miniconda3\condabin\conda.bat"
    "%USERPROFILE%\anaconda3\condabin\conda.bat"
    "%ProgramData%\miniconda3\condabin\conda.bat"
    "%ProgramData%\anaconda3\condabin\conda.bat"
    "%ProgramFiles%\Miniconda3\condabin\conda.bat"
    "%ProgramFiles%\Anaconda3\condabin\conda.bat"
) do (
    if exist %%~I (
        set "CONDA_BAT=%%~I"
        goto :eof
    )
)
for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
    set "CONDA_BAT=%%~I"
    goto :eof
)
goto :eof
