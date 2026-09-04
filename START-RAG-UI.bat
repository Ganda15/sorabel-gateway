@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo The local Python environment is missing.
  echo Run: uv sync --extra vector
  pause
  exit /b 1
)

start "Sorabel RAG UI" cmd /k "uv run uvicorn web_app.server:app --host 127.0.0.1 --port 8780"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8780"

popd
endlocal
