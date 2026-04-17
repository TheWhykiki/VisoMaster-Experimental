@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "EXIT_CODE=0"
set "CONDA_BAT="
set "ENV_PYTHON="

REM Prefer the local virtual environment because it is the least error-prone startup path.
IF EXIST ".venv\Scripts\python.exe" (
    echo Found .venv, launching with local Python...
    ".venv\Scripts\python.exe" main.py
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    call :FindEnvPython
    IF DEFINED ENV_PYTHON (
        echo .venv not found, launching with detected visomaster environment...
        "%ENV_PYTHON%" main.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    call :FindCondaBat
    IF DEFINED CONDA_BAT (
        echo .venv not found, trying conda environment "visomaster"...
        call "%CONDA_BAT%" activate visomaster
        IF NOT ERRORLEVEL 1 (
            echo Running VisoMaster...
            python main.py
            set "EXIT_CODE=!ERRORLEVEL!"
            goto :AfterRun
        )
        echo WARNING: Conda was found, but the environment "visomaster" could not be activated.
    )

    py -3 -c "import PySide6" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        echo .venv not found, running with Windows Python launcher...
        py -3 main.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    python -c "import PySide6" >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        echo .venv not found, running with system Python...
        python main.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    echo ERROR: No usable Python runtime with PySide6 was found.
    echo The desktop GUI needs one of these:
    echo   1. .venv\Scripts\python.exe
    echo   2. conda environment "visomaster"
    echo   3. system Python with the project requirements installed
    echo Use Start_Portable.bat or install the requirements first.
    set "EXIT_CODE=1"
    goto :HandleError
)

:AfterRun
IF NOT "!EXIT_CODE!"=="0" goto :HandleError
endlocal
exit /b 0

:HandleError
echo.
echo VisoMaster failed to start or exited with error code !EXIT_CODE!.
echo The console will stay open so you can read the error message above.
pause
endlocal
exit /b %EXIT_CODE%

:FindEnvPython
for %%I in (
    "%USERPROFILE%\miniconda3\envs\visomaster\python.exe"
    "%USERPROFILE%\anaconda3\envs\visomaster\python.exe"
    "%ProgramData%\miniconda3\envs\visomaster\python.exe"
    "%ProgramData%\anaconda3\envs\visomaster\python.exe"
    "%ProgramFiles%\Miniconda3\envs\visomaster\python.exe"
    "%ProgramFiles%\Anaconda3\envs\visomaster\python.exe"
    "%LOCALAPPDATA%\miniconda3\envs\visomaster\python.exe"
    "%LOCALAPPDATA%\anaconda3\envs\visomaster\python.exe"
    "C:\tools\miniconda3\envs\visomaster\python.exe"
    "C:\tools\anaconda3\envs\visomaster\python.exe"
) do (
    if exist %%~I (
        set "ENV_PYTHON=%%~I"
        goto :eof
    )
)
goto :eof

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
