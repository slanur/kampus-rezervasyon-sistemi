@echo off
setlocal
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8
set PY=python
if exist "%~dp0.venv\Scripts\python.exe" set PY="%~dp0.venv\Scripts\python.exe"
%PY% -m arayuz %*
