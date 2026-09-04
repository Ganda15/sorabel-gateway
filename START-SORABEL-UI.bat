@echo off
setlocal
cd /d "%~dp0"
start "Sorabel Data Assistant" http://127.0.0.1:8780/
uv run uvicorn web_app.server:app --host 127.0.0.1 --port 8780
endlocal
