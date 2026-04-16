@echo off
setlocal

IF EXIST ".venv\Scripts\python.exe" (
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    ".venv\Scripts\python.exe" main_web.py --host 0.0.0.0 --port 8000
) ELSE (
    echo .venv not found, trying conda environment "visomaster"...
    call conda activate visomaster
    IF ERRORLEVEL 1 (
        echo ERROR: Could not activate the conda environment "visomaster".
        echo Follow the README installation steps first.
        exit /b 1
    )
    echo Starting VisoMaster Network Web Console on 0.0.0.0:8000...
    python main_web.py --host 0.0.0.0 --port 8000
)

endlocal
