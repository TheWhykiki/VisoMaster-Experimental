@echo off
setlocal

REM Prefer the local virtual environment because it is the least error-prone startup path.
IF EXIST ".venv\Scripts\python.exe" (
    echo Found .venv, launching with local Python...
    ".venv\Scripts\python.exe" main.py
) ELSE (
    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Run Start_Portable.bat or follow the README installation steps first.
        exit /b 1
    )
    echo Running VisoMaster...
    python main.py
)
endlocal
