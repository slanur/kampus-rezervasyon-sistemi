@echo off
setlocal
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8
python -m rezervasyon %*
