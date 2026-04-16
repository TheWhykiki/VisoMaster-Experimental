@echo off
call scripts\setenv.bat
echo INFO: Legacy updater name detected. This repository now maintains requirements_cu129.txt.
"%GIT_EXECUTABLE%" pull --ff-only
"%PYTHON_EXECUTABLE%" -m pip install -r requirements_cu129.txt --default-timeout 100
"%PYTHON_EXECUTABLE%" download_models.py
