@echo off
REM web.bat: starts the Writer's Workbench web interface from the Windows
REM command window (Command Prompt).
REM
REM Usage:  web.bat
REM Then open http://127.0.0.1:8002/web/ in your browser.
REM To use a different port, run "set PORT=9000" first, then web.bat.
REM Press Ctrl+C to stop the server.

REM setlocal keeps these settings from sticking around in your
REM command window after the server stops.
setlocal

REM Run from the folder this file lives in, so the paths below work.
cd /d "%~dp0"

REM Let Python find our code (the server, projects, and users folders).
set "PYTHONPATH=%CD%;%PYTHONPATH%"

REM Use the simple SQLite database in the database folder.
set "DATABASE=sqlite"
if not defined SQLITE_LOC set "SQLITE_LOC=database"
if not defined OUR_NAME set "OUR_NAME=WritersWorkbench"
if not exist "%SQLITE_LOC%" mkdir "%SQLITE_LOC%"

REM Port 8002 so it doesn't clash with local.sh (8000) or the editor example (8001).
if not defined PORT set "PORT=8002"

REM The login for the web pages (same as the contributor editor).
if not defined WRITERS_EDITOR_USERNAME set "WRITERS_EDITOR_USERNAME=editor"
if not defined WRITERS_EDITOR_PASSWORD set /p "WRITERS_EDITOR_PASSWORD=Choose an editor password: "

REM Use "python" if it's installed, otherwise the Windows "py" launcher.
set "PY=python"
where python >nul 2>nul || set "PY=py"

echo Web interface: http://127.0.0.1:%PORT%/web/
echo Log in as '%WRITERS_EDITOR_USERNAME%' with the password you chose.
%PY% -m flask --app server.endpoints run --host 127.0.0.1 --port %PORT%
endlocal
