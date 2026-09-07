@echo off
REM Lance le serveur MCP Sorabel sur le profil support, pour le client officiel
REM MCP Inspector. %~dp0 = le dossier de ce script : aucune adresse en dur.
cd /d "%~dp0..\.."
set SORABEL_PROFILE=support
".venv\Scripts\python.exe" -m mcp_server.server
