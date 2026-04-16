@echo off
setlocal

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting VisoMaster Web Console on 127.0.0.1:8000...
    ".venv\Scripts\python.exe" main_web.py
) ELSE (
    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Follow the README installation steps first.
        exit /b 1
    )
    echo Starting VisoMaster Web Console on 127.0.0.1:8000...
    python main_web.py
)

endlocal
