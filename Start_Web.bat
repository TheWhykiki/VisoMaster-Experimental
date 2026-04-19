@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "EXIT_CODE=0"
set "CONDA_BAT="
set "ENV_PYTHON="
set "ENV_NAME=visomaster"
set "REQUIREMENTS_FILE=requirements_cu129.txt"

if not exist "%REQUIREMENTS_FILE%" (
    echo ERROR: Requirements file "%REQUIREMENTS_FILE%" was not found.
    set "EXIT_CODE=1"
    goto :HandleError
)

IF EXIST ".venv\Scripts\python.exe" (
    call :EnsurePythonPackages ".venv\Scripts\python.exe" ".venv" path
    IF NOT "!EXIT_CODE!"=="0" goto :HandleError
    echo Starting VisoMaster Web Console on 127.0.0.1:8000...
    ".venv\Scripts\python.exe" main_web.py
    set "EXIT_CODE=!ERRORLEVEL!"
) ELSE (
    call :FindCondaBat
    IF DEFINED CONDA_BAT (
        call :EnsureCondaEnv
        IF NOT "!EXIT_CODE!"=="0" goto :HandleError
        call :EnsureCondaPackages
        IF NOT "!EXIT_CODE!"=="0" goto :HandleError
        echo Starting VisoMaster Web Console on 127.0.0.1:8000...
        call "%CONDA_BAT%" run -n "%ENV_NAME%" python main_web.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    call :FindEnvPython
    IF DEFINED ENV_PYTHON (
        call :EnsurePythonPackages "%ENV_PYTHON%" "visomaster" path
        IF NOT "!EXIT_CODE!"=="0" goto :HandleError
        echo Conda launcher not found, launching web console with detected visomaster environment...
        "%ENV_PYTHON%" main_web.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    py -3 --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        call :EnsurePythonPackages "py -3" "Windows Python launcher" cmd
        IF NOT "!EXIT_CODE!"=="0" goto :HandleError
        echo .venv not found, starting with Windows Python launcher...
        py -3 main_web.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    python --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        call :EnsurePythonPackages "python" "system Python" cmd
        IF NOT "!EXIT_CODE!"=="0" goto :HandleError
        echo .venv not found, starting with system Python...
        python main_web.py
        set "EXIT_CODE=!ERRORLEVEL!"
        goto :AfterRun
    )

    echo ERROR: No usable Python runtime was found for the web console.
    echo Install Python 3, create a .venv, or use Start_Portable.bat web.
    set "EXIT_CODE=1"
    goto :HandleError
)

:AfterRun
IF NOT "!EXIT_CODE!"=="0" goto :HandleError
endlocal
exit /b 0

:HandleError
echo.
echo VisoMaster Web Console failed to start or exited with error code !EXIT_CODE!.
echo The console will stay open so you can read the error message above.
pause
endlocal
exit /b %EXIT_CODE%

:EnsureCondaEnv
call "%CONDA_BAT%" run -n "%ENV_NAME%" python --version >nul 2>&1
IF NOT ERRORLEVEL 1 (
    set "EXIT_CODE=0"
    goto :eof
)

echo Conda environment "%ENV_NAME%" not found. Creating it now...
call "%CONDA_BAT%" create -n "%ENV_NAME%" python=3.11 -y
IF ERRORLEVEL 1 (
    echo ERROR: Failed to create conda environment "%ENV_NAME%".
    set "EXIT_CODE=1"
    goto :eof
)

set "EXIT_CODE=0"
goto :eof

:EnsureCondaPackages
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -c "import PySide6, torch, cv2, onnxruntime, numpy, PIL" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    set "EXIT_CODE=0"
    goto :eof
)

echo Installing or updating packages in conda environment "%ENV_NAME%"...
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m ensurepip --upgrade >nul 2>&1
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install uv
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install uv into conda environment "%ENV_NAME%".
    set "EXIT_CODE=1"
    goto :eof
)

call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m uv pip install -r "%REQUIREMENTS_FILE%"
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install project requirements into conda environment "%ENV_NAME%".
    set "EXIT_CODE=1"
    goto :eof
)

set "EXIT_CODE=0"
goto :eof

:EnsurePythonPackages
set "TARGET_PY=%~1"
set "TARGET_NAME=%~2"
set "TARGET_KIND=%~3"

IF /I "%TARGET_KIND%"=="path" goto :EnsurePythonPackagesPath

%TARGET_PY% -c "import PySide6, torch, cv2, onnxruntime, numpy, PIL" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    set "EXIT_CODE=0"
    goto :eof
)

echo Installing or updating packages in %TARGET_NAME%...
%TARGET_PY% -m ensurepip --upgrade >nul 2>&1
%TARGET_PY% -m pip install uv
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install uv into %TARGET_NAME%.
    set "EXIT_CODE=1"
    goto :eof
)

%TARGET_PY% -m uv pip install -r "%REQUIREMENTS_FILE%"
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install project requirements into %TARGET_NAME%.
    set "EXIT_CODE=1"
    goto :eof
)

set "EXIT_CODE=0"
goto :eof

:EnsurePythonPackagesPath
"%TARGET_PY%" -c "import PySide6, torch, cv2, onnxruntime, numpy, PIL" >nul 2>&1
IF NOT ERRORLEVEL 1 (
    set "EXIT_CODE=0"
    goto :eof
)

echo Installing or updating packages in %TARGET_NAME%...
"%TARGET_PY%" -m ensurepip --upgrade >nul 2>&1
"%TARGET_PY%" -m pip install uv
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install uv into %TARGET_NAME%.
    set "EXIT_CODE=1"
    goto :eof
)

"%TARGET_PY%" -m uv pip install -r "%REQUIREMENTS_FILE%"
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install project requirements into %TARGET_NAME%.
    set "EXIT_CODE=1"
    goto :eof
)

set "EXIT_CODE=0"
goto :eof

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
