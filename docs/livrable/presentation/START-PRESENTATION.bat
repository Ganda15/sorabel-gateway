@echo off
setlocal
cd /d "%~dp0"

set "SORABEL_PYTHON=%~dp0..\..\..\.venv\Scripts\python.exe"

if exist "%SORABEL_PYTHON%" (
  start "Sorabel presentation server" /min "%SORABEL_PYTHON%" -m http.server 8790 --bind 127.0.0.1
) else (
  start "Sorabel presentation server" /min py -3 -m http.server 8790 --bind 127.0.0.1
)

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8790/"
endlocal
